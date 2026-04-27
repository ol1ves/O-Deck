# Cyberdeck Debug & Refine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the punch list of bugs and rough edges Oliver hit when running the cyberdeck on his actual 800×480 Pi kiosk: keyring prompt at boot, hardcoded status-bar text, footer not aligned, can't start pomodoro, no way to exit subviews, fake git heartbeat, and missing diagnostics for the integrations that aren't loading data.

**Architecture:** Split into six phases. Phase 1 adds backend diagnostics (`last_error`, LAN IP, uptime, callsign) so the UI can surface real device info and we can see why integrations are failing. Phase 2 ships the kiosk keyring fix. Phase 3 fixes layout and pomo viewport. Phase 4 makes the brand title clickable from every view (gives subviews a home button). Phase 5 wires the dynamic status bar and the tap-to-override behaviors for theme + weather window. Phase 6 makes the git heartbeat data-driven and distinguishes empty from loading across all widgets.

**Tech Stack:** Python 3.11 / FastAPI / pytest / respx (backend), Svelte 5 / SvelteKit (frontend), bash + systemd + chromium (kiosk).

**Out of scope (deferred):**
- Per-integration root cause fixes (transit MTA URL, Spotify auth, GitHub username, RSS feed URLs). After Phase 1 ships, run `curl localhost:8080/api/status | jq` on the Pi to see each integration's `last_error` — those go into a follow-up plan.
- Map widget redesign (real GTFS-shapes geometry).
- Showcase route content.

---

## Design decisions confirmed with Oliver

- **Theme override:** Tap the `◌ {mode}` indicator → cycles through calm/music/rain/thunder. Override decays back to auto after 60s. Each tap resets the decay timer.
- **Weather window:** Default is "today" (next 24h). Tap the sparkline → toggles to next 6h. Decays back to 24h after 30s. Shows "TODAY" or "6H" label + a "now" marker.
- **Map:** Leave placeholder — Oliver's complaint is the obviously fake motion, not the geometry. No change this plan.
- **Showcase:** Leave placeholder.
- **Bottom bar:** Per Oliver's screenshot the footer floats under the hero widgets instead of sticking to the bottom of the 800×480 viewport. Fix is full-height layout, not a redesign.

---

## File Map

```
backend/
├── cyberdeck/
│   ├── device.py                  # NEW — get_lan_ip(), uptime, BOOT_TIME
│   ├── integrations/base.py       # MODIFY — add _last_error field + populate in run()
│   ├── config.py                  # MODIFY — add DeviceConfig.callsign
│   └── main.py                    # MODIFY — extend /api/status with device + last_error
└── tests/
    ├── test_device.py             # NEW
    ├── test_main.py               # MODIFY — assert new status fields
    ├── test_config.py             # MODIFY — assert callsign default
    └── test_scheduler_and_base.py # MODIFY — assert last_error populated on failure

frontend/src/
├── lib/
│   ├── types.ts                   # MODIFY — Device, IntegrationStatus, AppState fields
│   ├── api.ts                     # MODIFY — fetchStatus(); periodic poll
│   ├── ws.ts                      # MODIFY — themeOverride + weatherWindow with decay
│   └── components/
│       ├── ODScreen.svelte        # MODIFY — height:100vh + flex column
│       ├── ODStatusBar.svelte     # MODIFY — read from store, brand clickable
│       ├── Sparkline.svelte       # MODIFY — now marker + window label
│       └── CommitHeartbeat.svelte # MODIFY — data-driven from github.commits
├── routes/
│   ├── +layout.svelte             # MODIFY — kick off status poll
│   ├── +page.svelte               # MODIFY — clickable brand, theme tap, weather tap, dynamic bar, loading-vs-empty
│   └── pomodoro/+page.svelte      # MODIFY — compact layout for 800×480

scripts/kiosk-launch.sh            # MODIFY — add --password-store=basic
systemd/cyberdeck-kiosk.service    # MODIFY — add --password-store=basic
config.example.yaml                # MODIFY — document device.callsign
```

---

## Phase 1 — Backend diagnostics & device info

### Task 1: Surface `last_error` on integration status

**Files:**
- Modify: `backend/cyberdeck/integrations/base.py`
- Modify: `backend/tests/test_scheduler_and_base.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_scheduler_and_base.py` (find the section that exercises `Integration.run()` on failure; if there isn't one, add this complete test):

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from cyberdeck.integrations.base import Integration


class _BoomIntegration(Integration):
    name = "boom"

    def event_name(self) -> str:
        return "boom.update"

    async def fetch(self) -> dict:
        raise RuntimeError("kaboom: 401 unauthorized")


@pytest.mark.asyncio
async def test_integration_status_includes_last_error_after_failure():
    integration = _BoomIntegration(cache=MagicMock(), ws_manager=MagicMock(), config=MagicMock())

    await integration.run()

    status = integration.status
    assert status["error_count"] == 1
    assert status["last_error"] is not None
    assert "kaboom" in status["last_error"]
    assert "401" in status["last_error"]


@pytest.mark.asyncio
async def test_integration_status_clears_last_error_after_success():
    cache = MagicMock()
    cache.set = MagicMock(return_value=False)
    ws = MagicMock()
    ws.broadcast = AsyncMock()

    class _FlipFlop(Integration):
        name = "flipflop"
        calls = 0

        def event_name(self) -> str:
            return "flipflop.update"

        async def fetch(self) -> dict:
            _FlipFlop.calls += 1
            if _FlipFlop.calls == 1:
                raise RuntimeError("first call fails")
            return {"ok": True}

    integration = _FlipFlop(cache=cache, ws_manager=ws, config=MagicMock())

    await integration.run()
    assert integration.status["last_error"] is not None

    await integration.run()
    assert integration.status["last_error"] is None
    assert integration.status["error_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_scheduler_and_base.py -v -k last_error`
Expected: FAIL — `KeyError: 'last_error'` or `AssertionError`.

- [ ] **Step 3: Implement `last_error`**

Edit `backend/cyberdeck/integrations/base.py`. The `_last_error` attribute already exists (added in a partial earlier edit). Make sure the file reads exactly:

```python
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cyberdeck.cache import Cache
    from cyberdeck.config import Settings
    from cyberdeck.ws import WSManager

logger = logging.getLogger(__name__)


class Integration(ABC):
    name: str

    def __init__(self, cache: Cache, ws_manager: WSManager, config: Settings) -> None:
        self.cache = cache
        self.ws = ws_manager
        self.config = config
        self._error_count = 0
        self._last_success: float | None = None
        self._last_error: str | None = None

    @abstractmethod
    async def fetch(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def event_name(self) -> str:
        raise NotImplementedError

    async def run(self) -> None:
        try:
            data = await self.fetch()
            changed = self.cache.set(self.name, data)
            if changed:
                await self.ws.broadcast(self.event_name(), data)
            self._error_count = 0
            self._last_error = None
            self._last_success = time.time()
        except Exception as exc:
            self._error_count += 1
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.error(
                "integration %s failed (error #%d): %s",
                self.name,
                self._error_count,
                exc,
                exc_info=True,
            )

    @property
    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "error_count": self._error_count,
            "last_success": self._last_success,
            "last_error": self._last_error,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_scheduler_and_base.py -v -k last_error`
Expected: 2 passed.

- [ ] **Step 5: Run full backend test suite**

Run: `uv run pytest backend/tests -q`
Expected: all green (no regressions in pre-existing tests that hit `.status`).

- [ ] **Step 6: Commit**

```bash
git add backend/cyberdeck/integrations/base.py backend/tests/test_scheduler_and_base.py
git commit -m "Surface last_error on integration status for diagnostics"
```

---

### Task 2: Device helpers (LAN IP, uptime, boot time)

**Files:**
- Create: `backend/cyberdeck/device.py`
- Create: `backend/tests/test_device.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_device.py`:

```python
import time
from unittest.mock import patch

from cyberdeck import device


def test_boot_time_is_set_at_module_load():
    assert isinstance(device.BOOT_TIME, float)
    assert device.BOOT_TIME <= time.time()


def test_uptime_seconds_grows():
    first = device.uptime_seconds()
    time.sleep(0.05)
    second = device.uptime_seconds()
    assert second >= first


def test_get_lan_ip_returns_string():
    ip = device.get_lan_ip()
    assert isinstance(ip, str)
    assert ip  # non-empty


def test_get_lan_ip_falls_back_to_loopback_on_socket_error():
    with patch("cyberdeck.device.socket.socket", side_effect=OSError("no network")):
        assert device.get_lan_ip() == "127.0.0.1"


def test_format_uptime_short():
    assert device.format_uptime(0) == "0m"
    assert device.format_uptime(60) == "1m"
    assert device.format_uptime(3600) == "1h 0m"
    assert device.format_uptime(3600 * 26 + 60 * 5) == "1d 2h"
    assert device.format_uptime(3600 * 24 * 4 + 3600 * 11) == "4d 11h"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_device.py -v`
Expected: FAIL — `ModuleNotFoundError: cyberdeck.device`.

- [ ] **Step 3: Create `backend/cyberdeck/device.py`**

```python
from __future__ import annotations

import socket
import time

BOOT_TIME: float = time.time()


def uptime_seconds() -> float:
    return time.time() - BOOT_TIME


def get_lan_ip() -> str:
    """Best-effort local LAN address. Uses the trick of opening a UDP socket
    to a routable address (no packets sent) and reading the chosen source IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
        finally:
            sock.close()
    except OSError:
        return "127.0.0.1"


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_device.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/device.py backend/tests/test_device.py
git commit -m "Add device helpers: LAN IP, uptime, boot time"
```

---

### Task 3: Add `device.callsign` to config schema

**Files:**
- Modify: `backend/cyberdeck/config.py` (the `DeviceConfig` class)
- Modify: `backend/tests/test_config.py`
- Modify: `config.example.yaml`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_config.py`:

```python
def test_device_config_default_callsign():
    from cyberdeck.config import DeviceConfig

    cfg = DeviceConfig()
    assert cfg.callsign == "od-01"


def test_device_config_loads_callsign_from_yaml(tmp_path, monkeypatch):
    from cyberdeck.config import load_config

    yaml = tmp_path / "config.yaml"
    yaml.write_text("device:\n  callsign: od-04\n")
    env = tmp_path / ".env"
    env.write_text("")

    monkeypatch.setenv("CYBERDECK_CONFIG_PATH", str(yaml))
    monkeypatch.setenv("CYBERDECK_ENV_PATH", str(env))

    settings = load_config()
    assert settings.app.device.callsign == "od-04"
```

(If `load_config` already supports a path override, use that instead of the env-var pattern. Read `config.py` first to confirm — if not, fall back to: write the yaml at the location `load_config` already reads from via tmp `HOME`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_config.py -v -k callsign`
Expected: FAIL — `AttributeError` or `ValidationError`.

- [ ] **Step 3: Add the field**

Edit `backend/cyberdeck/config.py`. In the `DeviceConfig` class, add `callsign`:

```python
class DeviceConfig(BaseModel):
    name: str = "O-Deck"
    callsign: str = "od-01"
    resolution: Resolution = Field(default_factory=Resolution)
    timezone: str = "America/New_York"
    location: Location = Field(default_factory=Location)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_config.py -v -k callsign`
Expected: 2 passed.

- [ ] **Step 5: Document in `config.example.yaml`**

Find the `device:` block in `config.example.yaml` and add a `callsign` line under `name`:

```yaml
device:
  name: "O-Deck"
  callsign: "od-04"   # short device handle shown in the status bar
  resolution: { width: 800, height: 480 }
  timezone: "America/New_York"
  location: { lat: 40.7128, lon: -74.0060 }
```

(Match the existing indentation and style of that block.)

- [ ] **Step 6: Commit**

```bash
git add backend/cyberdeck/config.py backend/tests/test_config.py config.example.yaml
git commit -m "Add device.callsign config field for status bar"
```

---

### Task 4: Extend `/api/status` with device info + integration `last_error`

**Files:**
- Modify: `backend/cyberdeck/main.py`
- Modify: `backend/tests/test_main.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_main.py`:

```python
def test_api_status_includes_device_info_and_last_error():
    from cyberdeck import main as m
    from fastapi.testclient import TestClient

    resp = TestClient(m.app).get("/api/status")

    assert resp.status_code == 200
    body = resp.json()

    # Device block
    assert "device" in body
    device = body["device"]
    assert device["callsign"] == m.settings.app.device.callsign
    assert device["hostname"]
    assert device["lan_ip"]
    assert isinstance(device["uptime_seconds"], (int, float))
    assert device["uptime_seconds"] >= 0

    # Integrations now expose last_error
    assert isinstance(body["integrations"], list)
    for entry in body["integrations"]:
        assert "last_error" in entry
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_main.py -v -k status_includes_device`
Expected: FAIL.

- [ ] **Step 3: Modify `main.py`**

Add an import and rewrite `api_status`. In `backend/cyberdeck/main.py`:

Add to imports (with the other `cyberdeck.*` imports):

```python
import socket as _socket
from cyberdeck import device as _device
```

Replace the `api_status` handler:

```python
@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    """Diagnostics: device info, WS client count, integration statuses (with last_error)."""
    return {
        "device": {
            "callsign": settings.app.device.callsign,
            "name": settings.app.device.name,
            "hostname": _socket.gethostname(),
            "lan_ip": _device.get_lan_ip(),
            "uptime_seconds": _device.uptime_seconds(),
        },
        "ws_clients": ws_manager.client_count,
        "integrations": [i.status for i in scheduler._integrations],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_main.py -v -k status_includes_device`
Expected: PASS.

- [ ] **Step 5: Run full backend test suite**

Run: `uv run pytest backend/tests -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/cyberdeck/main.py backend/tests/test_main.py
git commit -m "Expose device info and integration last_error on /api/status"
```

---

## Phase 2 — Kiosk keyring fix

### Task 5: Add `--password-store=basic` to chromium

**Files:**
- Modify: `scripts/kiosk-launch.sh`
- Modify: `systemd/cyberdeck-kiosk.service`

Both files invoke chromium and need the same flag. The flag tells chromium to use a plaintext local store instead of trying to unlock gnome-keyring (which requires interactive auth on first boot — that's the prompt Oliver hits).

- [ ] **Step 1: Edit `scripts/kiosk-launch.sh`**

Insert the new flag before the URL on the `exec /usr/bin/chromium` invocation. The block becomes:

```bash
exec /usr/bin/chromium \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --password-store=basic \
  --touch-events=enabled \
  --ozone-platform=wayland \
  --window-size=800,480 \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  http://localhost:8080
```

- [ ] **Step 2: Edit `systemd/cyberdeck-kiosk.service`**

Same change to the `ExecStart=` block:

```
ExecStart=/usr/bin/chromium \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --enable-features=OverlayScrollbar \
  --password-store=basic \
  --touch-events=enabled \
  --ozone-platform=wayland \
  --window-size=800,480 \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  http://localhost:8080
```

- [ ] **Step 3: Verify no other chromium invocation got missed**

Run: `grep -RIn "chromium" scripts/ systemd/ install.sh`
Expected: every match either has `--password-store=basic` or is a comment / unrelated reference.

- [ ] **Step 4: Commit**

```bash
git add scripts/kiosk-launch.sh systemd/cyberdeck-kiosk.service
git commit -m "Fix keyring prompt at boot: chromium --password-store=basic"
```

- [ ] **Step 5: Manual verification on Pi**

After `git pull` on the Pi:
1. `sudo systemctl daemon-reload` (only needed if systemd unit changed)
2. `sudo reboot`
3. After reboot, the kiosk should land on the dashboard with no keyring prompt.

If the prompt still appears: check `journalctl --user -u cyberdeck-kiosk -e` — there may be a second chromium spawn (e.g. from `~/.config/wayfire.ini`) that also needs the flag.

---

## Phase 3 — Layout & pomodoro viewport

### Task 6: ODScreen full-height, footer sticks to bottom

**Files:**
- Modify: `frontend/src/lib/components/ODScreen.svelte`
- Modify: `frontend/src/routes/+page.svelte` (just the global `:global(.odeck-screen)` rule)

The bug: `.odeck-screen` uses `min-height: 100vh` and `.odeck-screen__inner` uses `height: 100%`. On 800×480 with a tall content tree, percentage-of-min-height resolves to auto, the inner flex column doesn't stretch, and the footer sits wherever the content ends instead of pinning to the viewport bottom.

- [ ] **Step 1: Edit `ODScreen.svelte` styles**

Replace the `<style>` block (keep the existing rules, change the two heights and add a `padding`):

```svelte
<style>
  .odeck-screen {
    position: relative;
    overflow: hidden;
    height: 100vh;
    background: var(--od-bg);
    color: var(--od-ink);
    font-family: var(--font-mono);
  }

  .odeck-screen__inner {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
    height: 100%;
    padding: 10px 16px;
    box-sizing: border-box;
  }
</style>
```

- [ ] **Step 2: Remove the now-redundant `min-height: 100vh` override on the home page**

In `frontend/src/routes/+page.svelte`, find the `:global(.odeck-screen)` rule inside the `<style>` block:

```css
:global(.odeck-screen) {
  min-height: 100vh;
  background: var(--bg);
}
```

Replace with:

```css
:global(.odeck-screen) {
  background: var(--bg);
}
```

- [ ] **Step 3: Make the footer pin to the bottom**

Still in `frontend/src/routes/+page.svelte`, find the `.home-footer` rule and add `margin-top: auto` so it pushes to the bottom of the flex column:

```css
.home-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
```

Note: `display: flex` and `align-items: center` are already declared via the shared selector at the top of the style block — keep both forms working. If the existing rule already covers display/align, add only the `margin-top: auto` line:

```css
.home-footer {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
```

- [ ] **Step 4: Build + manual verification**

```bash
cd frontend && npm run build
```

On the Pi (or via `npm run dev` resized to 800×480):
- The footer (git strip + dock + ticker) should sit flush against the bottom edge of the viewport.
- No vertical scrollbar should be needed at 800×480.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/ODScreen.svelte frontend/src/routes/+page.svelte
git commit -m "Pin home footer to viewport bottom on 800x480"
```

---

### Task 7: Pomodoro screen fits 800×480, Start button reachable

**Files:**
- Modify: `frontend/src/routes/pomodoro/+page.svelte`

The pomo screen stacks: status bar (~30) + 340px ring + cycle dots + presets + controls + dock (~36). That's ~510px before any padding — Start button gets pushed below the visible area at 480.

- [ ] **Step 1: Shrink the ring and tighten spacing**

In `frontend/src/routes/pomodoro/+page.svelte`, change the SVG ring from 340 to 240, the radius from 160 to 110, and the tickmark math accordingly. Replace the `<svg>` block (lines ~90-114) with:

```svelte
<svg width="240" height="240" viewBox="0 0 240 240">
  <circle cx="120" cy="120" r="110" fill="none" stroke="rgba(240,232,214,0.06)" stroke-width="2" />
  <circle
    cx="120"
    cy="120"
    r="110"
    fill="none"
    stroke="var(--rose)"
    stroke-width="3"
    stroke-dasharray={dashArray}
    stroke-linecap="round"
    transform="rotate(-90 120 120)"
  />
  {#each tickmarks as i}
    {@const a = -Math.PI / 2 + ((i + 1) / 5) * Math.PI * 2}
    <line
      x1={120 + Math.cos(a) * 102}
      y1={120 + Math.sin(a) * 102}
      x2={120 + Math.cos(a) * 116}
      y2={120 + Math.sin(a) * 116}
      stroke="var(--ink-sub)"
      stroke-width="1"
    />
  {/each}
</svg>
```

Update the `circum` constant near line 33 to match the new radius:

```ts
const circum = 2 * Math.PI * 110;
```

- [ ] **Step 2: Update the ring wrapper size and countdown font**

In the same file, in the `<style>` block:

```css
.pomo-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 14px;
  position: relative;
}
.ring-wrap {
  position: relative;
  width: 240px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.countdown-time {
  font-weight: 200;
  font-size: 78px;
  letter-spacing: -3px;
  line-height: 0.95;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
```

- [ ] **Step 3: Build + manual verification**

```bash
cd frontend && npm run build
```

On the Pi, navigate to `/pomodoro`:
- The full ring + cycle dots + preset buttons + Start button + dock should all be visible without scrolling.
- Tap Start → it should call `POST /api/pomodoro/start` and the ring should begin animating.
- Verify with `curl -s localhost:8080/api/pomodoro/status | jq` while running — `running: true` and `remaining_seconds` decreasing.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/pomodoro/+page.svelte
git commit -m "Compact pomodoro layout for 800x480 — Start button reachable"
```

---

## Phase 4 — Brand-as-home navigation

### Task 8: Make `O-DECK` clickable from the home page status bar

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Wrap the brand span in a button**

Find lines ~104-110 (the `.status-left` block). Replace:

```svelte
<div class="status-left">
  <span class="brand">O-DECK</span>
  <span class="callsign">/od-04</span>
  <span><span class="live-dot">●</span> odeck.local</span>
  <span class="dim">up 4d 11h</span>
</div>
```

with:

```svelte
<div class="status-left">
  <button type="button" class="brand brand-button" onclick={() => goto('/')} aria-label="home">O-DECK</button>
  <span class="callsign">/od-04</span>
  <span><span class="live-dot">●</span> odeck.local</span>
  <span class="dim">up 4d 11h</span>
</div>
```

(Note: `/od-04`, `odeck.local`, and `up 4d 11h` get replaced with real data in Phase 5 — leave them alone for this task.)

- [ ] **Step 2: Style the button to match the existing brand text**

Add to the `<style>` block (near the existing `.brand` rule):

```css
.brand-button {
  padding: 0;
  border: 0;
  background: none;
  color: var(--ink);
  font: inherit;
  font-weight: 500;
  letter-spacing: inherit;
  cursor: pointer;
}
```

- [ ] **Step 3: Manual verification**

`npm run build` then load on Pi. Brand text should look identical, but tapping it on the home page is a no-op-but-no-error (already on `/`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/+page.svelte
git commit -m "Make O-DECK brand a home navigation button"
```

---

### Task 9: Make `O-DECK` clickable on every subpage via ODStatusBar

**Files:**
- Modify: `frontend/src/lib/components/ODStatusBar.svelte`

This single change gives every subpage (pomodoro, github, subway, transit, calendar, doomscroll, photos, showcase, diagnostics) a way back to home — fixes Oliver's "no way to exit pomo" complaint without adding per-page back buttons.

- [ ] **Step 1: Add the import and wrap the brand**

Replace the entire `<script>` block:

```svelte
<script lang="ts">
  import { goto } from '$app/navigation';

  let {
    app = '',
    accent = 'var(--sand)',
  }: {
    app?: string;
    accent?: string;
  } = $props();
</script>
```

In the `<header>` block, replace the brand span (line 13):

```svelte
<span class="od-status-bar__brand">O-DECK</span>
```

with:

```svelte
<button type="button" class="od-status-bar__brand od-status-bar__brand-button" onclick={() => goto('/')} aria-label="home">O-DECK</button>
```

- [ ] **Step 2: Add a button-reset style rule**

Append to the `<style>` block:

```css
.od-status-bar__brand-button {
  padding: 0;
  border: 0;
  background: none;
  color: var(--ink);
  font: inherit;
  font-weight: 500;
  letter-spacing: inherit;
  text-transform: inherit;
  cursor: pointer;
}
```

- [ ] **Step 3: Manual verification**

On the Pi, go to `/pomodoro`, tap O-DECK at the top-left → land on `/`. Same for `/github`, `/subway`, `/calendar`, `/doomscroll`, `/photos`, `/showcase`, `/diagnostics`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/components/ODStatusBar.svelte
git commit -m "Make subpage O-DECK title a home button"
```

---

## Phase 5 — Dynamic status bar + tap-to-override behaviors

### Task 10: Wire device info into the frontend store

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/ws.ts`
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: Extend types**

In `frontend/src/lib/types.ts`, add new interfaces and extend `AppState`:

```ts
export interface DeviceInfo {
  callsign: string;
  name: string;
  hostname: string;
  lan_ip: string;
  uptime_seconds: number;
}

export interface IntegrationStatus {
  name: string;
  error_count: number;
  last_success: number | null;
  last_error: string | null;
}
```

In the `AppState` interface, add:

```ts
  device: DeviceInfo | null;
  integrationStatus: IntegrationStatus[];
  uptimeOriginSeconds: number; // device.uptime at the moment we polled (for live-ticking)
  uptimePolledAt: number;      // Date.now() when we polled
  themeOverride: MotionMode | null;
  weatherWindow: '24h' | '6h';
```

- [ ] **Step 2: Add fetchStatus + initial values**

In `frontend/src/lib/ws.ts`, expand `initialState`:

```ts
const initialState: AppState = {
  weather: null,
  transit: null,
  spotify: null,
  calendar: null,
  github: null,
  rss: null,
  photos: null,
  pomodoro: null,
  device: null,
  integrationStatus: [],
  uptimeOriginSeconds: 0,
  uptimePolledAt: Date.now(),
  themeOverride: null,
  weatherWindow: '24h',
  connected: false,
  motionMode: 'calm'
};
```

In `frontend/src/lib/api.ts`, append a `fetchStatus` helper:

```ts
import type { DeviceInfo, IntegrationStatus } from './types';

export async function fetchStatus(): Promise<void> {
  try {
    const r = await fetch(`${BASE}/api/status`);
    if (!r.ok) return;
    const body = (await r.json()) as {
      device: DeviceInfo;
      integrations: IntegrationStatus[];
    };
    appStore.update((current) => ({
      ...current,
      device: body.device,
      integrationStatus: body.integrations,
      uptimeOriginSeconds: body.device.uptime_seconds,
      uptimePolledAt: Date.now()
    }));
  } catch {
    // status is best-effort; failures are silent
  }
}
```

- [ ] **Step 3: Poll status on mount + every 30s**

In `frontend/src/routes/+layout.svelte`, find the `onMount` that calls `fetchInitialState()` and `connectWebSocket()`. Add:

```ts
import { fetchStatus, fetchInitialState } from '$lib/api';

onMount(() => {
  void fetchInitialState();
  void fetchStatus();
  connectWebSocket();
  const id = setInterval(() => void fetchStatus(), 30_000);
  return () => clearInterval(id);
});
```

(Match the existing import style — only add what isn't already imported.)

- [ ] **Step 4: Build, no functional change yet**

```bash
cd frontend && npm run build
```

Expected: builds clean. No visible change — Task 11 wires the values into the UI.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/ws.ts frontend/src/routes/+layout.svelte
git commit -m "Plumb device info + integration status into the frontend store"
```

---

### Task 11: Drive the home status bar from real data

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

Replace the hardcoded `/od-04`, `odeck.local`, `up 4d 11h`, `THU APR 25` with values from the store. The clock-tick `setInterval` already updates `now` each second; reuse it to recompute uptime.

- [ ] **Step 1: Add derived uptime label and date label refresh**

In the `<script>` block, after the existing `now` declarations, add:

```ts
import { format_uptime_label } from '$lib/format';
```

Then create `frontend/src/lib/format.ts` with shared formatting helpers:

```ts
export function format_uptime_label(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  if (days) return `${days}d ${hours}h`;
  if (hours) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}
```

Back in `+page.svelte`, derive the live values:

```ts
const device = $derived(state.device);
const liveUptimeSeconds = $derived(
  state.uptimeOriginSeconds + (now.getTime() - state.uptimePolledAt) / 1000
);
const uptimeLabel = $derived(format_uptime_label(liveUptimeSeconds));
const callsign = $derived(device?.callsign ? `/${device.callsign}` : '');
const lanLabel = $derived(device?.lan_ip ?? device?.hostname ?? '...');
```

- [ ] **Step 2: Replace the status bar JSX**

Find the `.status-left` block and replace the hardcoded spans:

```svelte
<div class="status-left">
  <button type="button" class="brand brand-button" onclick={() => goto('/')} aria-label="home">O-DECK</button>
  {#if callsign}<span class="callsign">{callsign}</span>{/if}
  <span><span class="live-dot">●</span> {lanLabel}</span>
  <span class="dim">up {uptimeLabel}</span>
</div>
```

- [ ] **Step 3: Build + manual verification**

```bash
cd frontend && npm run build
```

On the Pi:
- `/od-04` becomes whatever you set `device.callsign` to in `~/.config/cyberdeck/config.yaml` (default `od-01` until set).
- `odeck.local` becomes the device's actual LAN IP (e.g. `192.168.1.42`).
- `up 4d 11h` becomes the real uptime, ticking each second.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/format.ts frontend/src/routes/+page.svelte
git commit -m "Drive home status bar from device info: callsign, LAN IP, live uptime"
```

---

### Task 12: Drive ODStatusBar (subpages) from real data too

**Files:**
- Modify: `frontend/src/lib/components/ODStatusBar.svelte`

- [ ] **Step 1: Read from the store**

Replace the entire `<script>` block:

```svelte
<script lang="ts">
  import { goto } from '$app/navigation';
  import { appStore } from '$lib/ws';
  import { format_uptime_label } from '$lib/format';
  import { onMount } from 'svelte';

  let {
    app = '',
    accent = 'var(--sand)',
  }: {
    app?: string;
    accent?: string;
  } = $props();

  const state = $derived($appStore);
  const device = $derived(state.device);
  let now = $state(Date.now());
  onMount(() => {
    const id = setInterval(() => { now = Date.now(); }, 1000);
    return () => clearInterval(id);
  });
  const liveUptime = $derived(
    state.uptimeOriginSeconds + (now - state.uptimePolledAt) / 1000
  );
  const uptimeLabel = $derived(format_uptime_label(liveUptime));
  const lanLabel = $derived(device?.lan_ip ?? device?.hostname ?? '...');
  const dateLabel = $derived(
    new Date(now).toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short',
      timeZone: 'UTC' /* leave UTC; users see local clock on home page */
    }).toUpperCase()
  );
</script>
```

- [ ] **Step 2: Replace the header markup**

```svelte
<header class="od-status-bar" style:--od-status-accent={accent}>
  <div class="od-status-bar__left">
    <button type="button" class="od-status-bar__brand od-status-bar__brand-button" onclick={() => goto('/')} aria-label="home">O-DECK</button>
    {#if app}
      <span class="od-status-bar__separator">/</span>
      <span class="od-status-bar__app">{app}</span>
    {/if}
    <span class="od-status-bar__host"><span class="live-dot">●</span> {lanLabel}</span>
    <span>up {uptimeLabel}</span>
  </div>

  <div class="od-status-bar__right" aria-label="connection and date">
    <span>{state.connected ? 'ws live' : 'ws idle'}</span>
    <span class="od-status-bar__date">{dateLabel}</span>
  </div>
</header>
```

- [ ] **Step 3: Build + manual verification**

`npm run build`. Visit each subpage on the Pi: status bar shows correct LAN IP, uptime, ws status, date.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/components/ODStatusBar.svelte
git commit -m "Drive subpage status bar from store data + live uptime"
```

---

### Task 13: Theme tap with auto-decay

**Files:**
- Modify: `frontend/src/lib/ws.ts`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Add override + decay helpers**

In `frontend/src/lib/ws.ts`, after the existing `deriveMotionMode` function, add:

```ts
const THEME_OVERRIDE_DECAY_MS = 60_000;
let themeOverrideTimer: ReturnType<typeof setTimeout> | null = null;
const themeCycle: MotionMode[] = ['calm', 'music', 'rain', 'thunder'];

export function tapTheme(): void {
  appStore.update((state) => {
    const current = state.themeOverride ?? state.motionMode;
    const idx = themeCycle.indexOf(current);
    const next = themeCycle[(idx + 1) % themeCycle.length];
    return { ...state, themeOverride: next, motionMode: next };
  });
  if (themeOverrideTimer) clearTimeout(themeOverrideTimer);
  themeOverrideTimer = setTimeout(() => {
    appStore.update((state) => ({
      ...state,
      themeOverride: null,
      motionMode: deriveMotionMode(state)
    }));
  }, THEME_OVERRIDE_DECAY_MS);
}
```

- [ ] **Step 2: Honor the override in `applyEvent`**

In the same file, edit `applyEvent` so it does not stomp the override on data updates. Replace the trailing two lines:

```ts
    next.motionMode = deriveMotionMode(next);
    return next;
```

with:

```ts
    next.motionMode = next.themeOverride ?? deriveMotionMode(next);
    return next;
```

- [ ] **Step 3: Wire tap on the home status bar indicator**

In `frontend/src/routes/+page.svelte`, import:

```ts
import { tapTheme } from '$lib/ws';
```

Replace the theme indicator span:

```svelte
<span class:music={mode === 'music'} class:rain={mode === 'rain'} class:thunder={mode === 'thunder'}>◌ {mode}</span>
```

with:

```svelte
<button
  type="button"
  class="theme-tap"
  class:music={mode === 'music'}
  class:rain={mode === 'rain'}
  class:thunder={mode === 'thunder'}
  class:overridden={state.themeOverride !== null}
  onclick={tapTheme}
  aria-label="cycle theme"
>◌ {mode}</button>
```

Add to the `<style>` block:

```css
.theme-tap {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  letter-spacing: inherit;
  cursor: pointer;
}
.theme-tap.overridden {
  text-decoration: underline dotted currentColor;
  text-underline-offset: 3px;
}
```

- [ ] **Step 4: Manual verification**

`npm run build`. On the Pi:
- Tap `◌ calm` → cycles to `◌ music` (drift orbs change palette).
- Wait 60s → reverts to whatever the data says (e.g. `calm` if no music playing).
- Tap rapidly → each tap resets the decay window.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/ws.ts frontend/src/routes/+page.svelte
git commit -m "Tap theme indicator to override mode; auto-decay after 60s"
```

---

### Task 14: Weather window tap (24h ↔ 6h) with decay + scale labels

**Files:**
- Modify: `frontend/src/lib/components/Sparkline.svelte`
- Modify: `frontend/src/lib/ws.ts`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Add window override helper**

In `frontend/src/lib/ws.ts`, add:

```ts
const WEATHER_WINDOW_DECAY_MS = 30_000;
let weatherWindowTimer: ReturnType<typeof setTimeout> | null = null;

export function tapWeatherWindow(): void {
  appStore.update((state) => ({
    ...state,
    weatherWindow: state.weatherWindow === '24h' ? '6h' : '24h'
  }));
  if (weatherWindowTimer) clearTimeout(weatherWindowTimer);
  weatherWindowTimer = setTimeout(() => {
    appStore.update((state) => ({ ...state, weatherWindow: '24h' }));
  }, WEATHER_WINDOW_DECAY_MS);
}
```

- [ ] **Step 2: Add a `label` slot to Sparkline**

Read `frontend/src/lib/components/Sparkline.svelte` first to see its current props.

Add support for an optional `nowLabel` and `endLabel` rendered as small text under the chart (or as overlaid SVG `<text>` at the start/end). Minimal change — append two new props:

```svelte
let {
  points = [],
  color = 'var(--ink)',
  width = 100,
  height = 30,
  nowLabel = '',
  endLabel = ''
}: {
  points?: Array<{ h: string; t: number }>;
  color?: string;
  width?: number;
  height?: number;
  nowLabel?: string;
  endLabel?: string;
} = $props();
```

In the SVG output, after the polyline, add (only when labels are non-empty):

```svelte
{#if nowLabel}
  <text x="0" y={height - 1} font-size="8" fill="var(--ink-dim)" font-family="var(--font-mono)">
    {nowLabel}
  </text>
{/if}
{#if endLabel}
  <text x={width} y={height - 1} text-anchor="end" font-size="8" fill="var(--ink-dim)" font-family="var(--font-mono)">
    {endLabel}
  </text>
{/if}
```

(If the existing Sparkline structure differs, adapt — but keep the overall shape: two new optional props, two conditional `<text>` elements.)

- [ ] **Step 3: Wire window selection on the home page**

In `frontend/src/routes/+page.svelte`:

Import the helper:

```ts
import { tapWeatherWindow } from '$lib/ws';
```

Add a derived series:

```ts
const weatherWindow = $derived(state.weatherWindow);
const weatherSeries = $derived(
  weather ? (weatherWindow === '6h' ? weather.hourly.slice(0, 6) : weather.hourly.slice(0, 24)) : []
);
const weatherEndLabel = $derived(weatherWindow === '6h' ? '+6H' : 'TODAY');
```

Replace the `.weather-sparkline` block:

```svelte
<div class="weather-sparkline">
  <Sparkline points={weather.hourly} color="var(--sage)" width={140} height={30} />
</div>
```

with:

```svelte
<button type="button" class="weather-sparkline-btn" onclick={tapWeatherWindow} aria-label="toggle weather window">
  <Sparkline
    points={weatherSeries}
    color="var(--sage)"
    width={140}
    height={36}
    nowLabel="NOW"
    endLabel={weatherEndLabel}
  />
</button>
```

Add a button-reset in the `<style>` block:

```css
.weather-sparkline-btn {
  margin-left: auto;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
}
```

(And remove the now-unused `.weather-sparkline` rule if it only set margin/padding — keep if it does layout work used elsewhere.)

- [ ] **Step 4: Manual verification**

`npm run build`. On the Pi:
- Sparkline shows up to 24 points by default with `NOW` and `TODAY` labels under it.
- Tap → reduces to 6 points, label becomes `+6H`.
- Wait 30s → reverts to 24h.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/Sparkline.svelte frontend/src/lib/ws.ts frontend/src/routes/+page.svelte
git commit -m "Tap weather sparkline to toggle 24h/6h; show now+window labels"
```

---

## Phase 6 — Polish: data-driven git heartbeat, loading vs empty

### Task 15: Make CommitHeartbeat data-driven

**Files:**
- Modify: `frontend/src/lib/components/CommitHeartbeat.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Read the existing component**

Run: `cat frontend/src/lib/components/CommitHeartbeat.svelte`
Note the current props (likely `color` + `count`). The component currently generates synthetic bars — replace with a real series.

- [ ] **Step 2: Accept a `series` prop**

Replace the `<script>` block:

```svelte
<script lang="ts">
  let {
    color = 'var(--sage)',
    series = [] as number[],
    bars = 36,
    height = 14
  }: {
    color?: string;
    series?: number[];
    bars?: number;
    height?: number;
  } = $props();

  const padded = $derived(() => {
    if (series.length >= bars) return series.slice(-bars);
    return Array(bars - series.length).fill(0).concat(series);
  });
  const max = $derived(Math.max(1, ...padded()));
</script>
```

Replace the markup:

```svelte
<div class="heartbeat" style:--hb-color={color} style:height={`${height}px`}>
  {#each padded() as value, i}
    <span
      class="bar"
      class:zero={value === 0}
      style:height={`${Math.max(2, (value / max) * height)}px`}
      style:opacity={value === 0 ? 0.18 : 0.55 + (value / max) * 0.45}
    ></span>
  {/each}
</div>

<style>
  .heartbeat {
    display: inline-flex;
    align-items: flex-end;
    gap: 2px;
    height: var(--hb-height, 14px);
  }
  .bar {
    width: 2px;
    background: var(--hb-color);
    border-radius: 1px;
  }
  .bar.zero {
    background: var(--ink-sub);
  }
</style>
```

- [ ] **Step 3: Build a series from `github.commits` on the home page**

In `frontend/src/routes/+page.svelte`, add a derived series — count commits per "bucket" (use 36 buckets each representing ~1h, falling back to per-commit count if timestamps aren't usable):

```ts
const commitSeries = $derived.by(() => {
  if (!github?.commits.length) return [] as number[];
  // Each commit is a recent push; we don't have precise timestamps in the typed data.
  // Distribute commits into 36 trailing buckets by index for now (one bar per commit, capped at 36).
  const out = new Array(36).fill(0);
  const recent = github.commits.slice(0, 36);
  for (let i = 0; i < recent.length; i++) {
    out[36 - recent.length + i] = 1;
  }
  return out;
});
```

Replace:

```svelte
<CommitHeartbeat color="var(--sage)" count={36} />
```

with:

```svelte
<CommitHeartbeat color="var(--sage)" series={commitSeries} />
```

- [ ] **Step 4: Build + manual verification**

`npm run build`. On the Pi:
- With no GitHub data: bars are flat dim grey (zero state) — no longer a misleading sine wave.
- Once GitHub data populates (after Phase 1's diagnostic work surfaces and you fix the github auth — covered in a follow-up plan): bars reflect the actual commit count.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/components/CommitHeartbeat.svelte frontend/src/routes/+page.svelte
git commit -m "Make git heartbeat data-driven instead of decorative"
```

---

### Task 16: Distinguish "loading" vs "empty" vs "errored" across home widgets

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

The home page currently shows `transit loading...`, `calendar loading...`, `nothing playing` even when the integration has errored or simply has nothing to show. Use the `integrationStatus` array (populated in Task 10) to pick the right copy.

- [ ] **Step 1: Add a small helper**

In the `<script>` block of `+page.svelte`:

```ts
function statusFor(name: string) {
  return state.integrationStatus.find((s) => s.name === name);
}
function copyForEmpty(name: string, emptyCopy: string): string {
  const s = statusFor(name);
  if (!s) return 'loading...';
  if (s.last_success === null && s.error_count > 0) return 'unavailable';
  if (s.last_success === null) return 'loading...';
  return emptyCopy;
}
```

- [ ] **Step 2: Use it in the three loading spots**

Replace `transit loading...`:

```svelte
<div class="loading">{copyForEmpty('transit', 'no trains')}</div>
```

Replace `calendar loading...`:

```svelte
<div class="loading">{copyForEmpty('calendar', 'no events today')}</div>
```

Replace `nothing playing`:

```svelte
<div class="loading">{copyForEmpty('spotify', 'nothing playing')}</div>
```

- [ ] **Step 3: Manual verification**

On the Pi (with Phase 1 deployed so `integrationStatus` is populated):
- Calendar that succeeded but is empty shows `no events today` (matches Oliver's screenshot — calendar is fine, just empty).
- Spotify with auth errors shows `unavailable`.
- Transit with errors shows `unavailable`.
- Briefly on first load, before the first poll, shows `loading...`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/+page.svelte
git commit -m "Distinguish loading/empty/unavailable on home widgets"
```

> **Subpage parity (optional, same task pattern):** the `copyForEmpty` helper also belongs in `/doomscroll` (RSS — currently shows "feed loading" with no QR because RSS is erroring; will read "unavailable" until the follow-up plan fixes RSS) and `/github` (currently shows nothing). If you want parity now, lift `copyForEmpty` into `frontend/src/lib/format.ts`, import it from those routes, and replace each "loading..." string. Doing this in one extra commit is fine.

---

## Verification checklist

After all 16 tasks ship:

- [ ] `uv run pytest backend/tests -q` — all green
- [ ] `cd frontend && npm run build` — clean
- [ ] On Pi: reboot → no keyring prompt, lands on dashboard
- [ ] Home status bar shows real callsign, LAN IP, live-ticking uptime
- [ ] Tap O-DECK from any subpage → returns home
- [ ] Tap `◌ calm` → cycles theme; reverts after 60s
- [ ] Tap weather sparkline → shows 6h with `+6H` label; reverts after 30s
- [ ] `/pomodoro` Start button visible; tapping starts the timer
- [ ] Footer pinned to bottom of 800×480 viewport
- [ ] Calendar with no events shows "no events today" (not "loading")
- [ ] `curl localhost:8080/api/status | jq .integrations[].last_error` returns the actual error strings — feed those into the follow-up plan to fix Spotify/transit/GitHub/RSS.

---

## Follow-up (separate plan, not this one)

Once `/api/status` shows real `last_error` strings, the next plan triages each:
- **transit:** likely wrong MTA URL (`https://api-endpoint.mta.info/Feeds` looks stale; current MTA GTFS-RT moved). Verify URL + that key is required.
- **spotify:** confirm `.env` has SPOTIFY_CLIENT_ID/SECRET/REFRESH_TOKEN; if so, look at the actual error.
- **github:** confirm `github.username` set in config.yaml; check 403/rate-limit vs 404.
- **rss:** check feed URLs in config.yaml resolve.
