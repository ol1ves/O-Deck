# O-Deck Cyberdeck Dashboard — Design Spec

**Date:** 2026-04-26
**Status:** Design (awaiting Claude Design UI handoff before implementation)
**Owner:** Oliver Santana

## Purpose

A desk-resident dashboard / command center running on a Raspberry Pi 4B with a 7" ribbon-cable touchscreen. Acts as an ambient information radiator for daily life in NYC and a personal cyberdeck called O-Deck. The hardware will eventually be repurposed as a head unit for a DJ-deck project; until then it lives on Oliver's desk full-time, on its own SD card, so the DJ project can be developed in parallel without conflict.

## Use mode

- **Hybrid:** ambient by default, interactive on demand.
- **Viewing distance:** ~4 ft, landscape orientation. Touch is a secondary interaction (Oliver will walk over to tap), so the home screen optimizes for legibility from across the desk over information density.
- **Boot behavior:** kiosk mode — boots straight into the dashboard fullscreen with no visible desktop.
- **Operations model:** SSH-first development. After first-boot setup, all configuration and updates happen from a laptop over SSH; the device itself is touch-only.

## Goals

1. Be useful at a glance — Oliver can tell time, weather, next train, today's schedule, and what's playing without touching the device.
2. Be reliable — runs 24/7 without supervision, survives network and API failures gracefully.
3. Be fun — the device should feel personal and have aesthetic identity, with a "Showcase" mode for full-bleed visuals when not actively being used.
4. Be extensible — adding a new widget or integration is a config change plus a new file, not an architectural shift.

## Non-goals (v1)

- Trip planning / multi-leg routing across the MTA. Live arrivals only.
- OpenClaw or any arcade. Cut from v1; revisit later as a "launcher app" pattern.
- Write actions to external services (no replying to GitHub, no Spotify control, no creating Notion todos). Read-only across the board.
- Smart home / Home Assistant integration.
- Voice / wake-word.
- Idle-timeout behavior. Showcase mode is manual-toggle only in v1.
- Multi-user; this is Oliver's personal device.

## Hardware

- **Compute:** Raspberry Pi 4B (4GB+).
- **Display:** Third-party 7" touchscreen, ribbon-cable connected. Resolution unknown at spec time (commonly 800×480 or 1024×600); detected at install time and written to config. Layout is resolution-aware via responsive units, not pixel-pinned.
- **Touch + drivers:** working out of the box; no special handling needed.
- **Audio:** 3.5mm jack to a desk speaker.
- **Storage:** dedicated SD card (so the DJ project can use a separate one).
- **Network:** WiFi.

## Home screen — content

The home screen is the always-visible ambient view. It contains:

- **Core tiles:** Time, Weather, Transit, Calendar (Today at a glance), RSS.
- **Hero tile (default):** Now Playing.
- **Launcher dock:** small icons that open fullscreen apps — Pomodoro, GitHub, Subway map, Doomscroll, Photo frame, Showcase mode.
- The hero slot is configurable (0–2 entries). v1 ships with one hero (Now Playing); Pomodoro placement may be revisited after Claude Design exploration.

## Fullscreen apps (launcher)

- **Transit detail** — all four configured stations grouped, secondary stations collapsible, full alerts.
- **Calendar** — today day-view, swipe/toggle to week-view. Notion metadata rendered when an event has a linked Notion todo.
- **GitHub** — recent commits, open PRs, assigned issues. Read-only.
- **Subway live map** — vector NYC subway map with line colors, animated live train positions from MTA GTFS-RT vehicle feed; tap a station for arrivals.
- **Doomscroll** — unified RSS feed, filterable by source. Tapping a story renders a QR code that encodes the URL; phone scans, reads on phone. No webview on the Pi.
- **Photo frame** — rotates images from configured source.
- **Pomodoro** — focus mode with customizable work/break durations and named presets. Running session takes over the screen with its own ambient UI (final treatment defined in Claude Design handoff).
- **Showcase** — full-bleed generative visuals; auto-switches to music-reactive when Spotify is playing. Tap anywhere returns to home.

## Integrations

| Integration | Purpose | Provider | Auth |
|---|---|---|---|
| Weather | Current temp, condition, high/low; alert badges (rain/snow/heat spike/cold drop/severe) | Open-Meteo | None |
| Transit | Live arrivals at four stations; service alerts | MTA GTFS-RT | None |
| Calendar | Today + week view, joined Notion + Google data | Google Calendar API + Notion API | OAuth (Google), Internal Integration token (Notion) |
| Now Playing | Track + artist + album art, display-only | Spotify Web API | OAuth refresh-token flow |
| GitHub activity | Personal commits, PRs, assigned issues | GitHub REST API | Fine-grained PAT (read-only) |
| RSS | Headlines (TLDR, HN, configurable subs/YT) | Feed URLs | None; TLDR via kill-the-newsletter.com |
| Photos | Image rotation for Photo frame + idle | iCloud Shared Album (public share URL) or local folder | None |

### Transit configuration (v1 default)

Configurable via `config.yaml`. Default stations:

**Primary (home — Jay St / DeKalb):**
- Jay St–MetroTech, uptown: A, C, F, R
- DeKalb Av, uptown: Q

**Secondary (return-home stations):**
- 14 St–Union Sq, downtown: 4, 5, 6, R, Q
- W 4 St–Wash Sq, downtown: F, A, C

Home tile shows primaries by default; fullscreen view groups all four with secondary collapsible. Service alerts surface as badges on lines and expand in fullscreen.

GTFS `stop_id` values in the example config are illustrative; `docs/integrations.md` includes a lookup procedure (MTA's published stops.txt) for swapping in correct IDs. Direction is encoded in the suffix (`N`/`S` uptown/downtown).

### Calendar join semantics

Notion Calendar is a frontend on top of Google Calendar — scheduled Notion todos appear as Google Calendar events with a link back to the Notion page. The integration:

1. Pulls events from configured Google calendars.
2. Pulls todos from configured Notion databases.
3. Joins them by event link (preferred) with title-match fallback.
4. Renders Notion metadata (status, project) on the event when joined; renders plain when not.

### RSS sources (v1 default seed)

- TLDR (via kill-the-newsletter.com bridge)
- Hacker News
- Configurable subreddits (Reddit native RSS at `/r/<sub>/.rss`)
- Configurable YouTube channels (`youtube.com/feeds/videos.xml?channel_id=...`)

Home tile is hybrid: a scrolling ticker line plus a static stack of the latest 2–3 headlines, refreshed periodically. No read/unread tracking.

### Photos

- Default: iCloud Shared Album. Oliver creates one shared album, drops photos in from his phone, pastes the public share URL into config. Stable, no auth gymnastics.
- Fallback: local folder on the SD card (e.g., `~/cyberdeck-photos`).
- Personal (non-shared) iCloud library is **not** supported — no stable public API.

### Audio

- Output via 3.5mm; system audio so any output route works.
- Default: mostly silent. Small chimes for Pomodoro transitions, severe weather alerts. All chimes individually toggleable.
- Master volume in config.

## Architecture

Three layers, all running on the Pi:

```
┌───────────────────────────────────────────┐
│ Chromium kiosk (fullscreen, no chrome)    │
│  └── SvelteKit SPA                        │
│       ├── home + apps (routes)            │
│       └── WebSocket + REST clients        │
└─────────────┬─────────────────────────────┘
              │ ws://localhost:8080/ws
              │ http://localhost:8080/api
              ▼
┌───────────────────────────────────────────┐
│ FastAPI backend (Python 3.11+)            │
│  ├── REST API (config, app actions)       │
│  ├── WebSocket pub/sub (data updates)     │
│  ├── APScheduler (per-integration polls)  │
│  ├── Cache (in-memory + SQLite)           │
│  └── Integrations (one module each)       │
└─────────────┬─────────────────────────────┘
              │
              ▼
        External APIs
```

**Data flow** (transit example):

```
MTA GTFS-RT  ──(every 30s)──▶  transit worker
                                  │
                                  ▼
                              cache (mem + SQLite)
                                  │
                                  ▼ (on change)
                              WebSocket: transit.update
                                  │
                                  ▼
                              frontend store → tile re-renders
```

The backend keeps polling and caching even if the frontend reloads. The frontend is stateless and can be reloaded without disrupting integrations. The backend binds to `0.0.0.0:8080` so the same API is reachable from a laptop browser at `http://<pi-ip>:8080` on the LAN for development; the kiosk uses `localhost`.

## Tech stack

**OS:** Raspberry Pi OS Bookworm 64-bit (Lite). Better-tuned drivers for Pi GPU/GPIO/display than Ubuntu; ribbon-cable touchscreen works without driver wrangling.

**Display server:** Wayland (Wayfire — RPi OS Bookworm default) or labwc. Lightweight; suited for kiosk.

**Backend:**
- `fastapi`, `uvicorn` — HTTP + WebSocket
- `httpx` — async HTTP client
- `apscheduler` — per-integration polling
- `pydantic` v2 — config + data models
- `sqlite3` (stdlib) — small persistent cache
- `python-dotenv` — env var loading
- `gcsa` (Google Calendar), `notion-client`, `spotipy` (Spotify), `gtfs-realtime-bindings` (MTA), `feedparser` (RSS)

**Frontend:**
- **SvelteKit** (small bundle, fast on Pi, clean HTML/CSS handoff from Claude Design)
- **TailwindCSS** (utility-first; resolution-aware layouts trivial)
- **Pixi.js / WebGL shaders** for Showcase mode
- **Web Audio API** for music-reactive visuals (audio stream proxied through backend)
- No React. No Next. No bundler bloat beyond what SvelteKit ships.

**Process management:** systemd user services. One unit for backend, one for kiosk shell. `journalctl` for logs.

**Configuration:** single `config.yaml` (template committed as `config.example.yaml`); real config at `~/.config/cyberdeck/config.yaml`. Secrets in `~/.config/cyberdeck/.env`.

**Frontend ↔ Backend contract:**
- WebSocket emits typed events (`weather.update`, `transit.update`, `calendar.update`, `spotify.update`, `github.update`, `rss.update`, `photos.update`, `system.alert`).
- REST for one-shot reads (`GET /api/config`, `GET /api/state`) and writes (`POST /api/pomodoro/start`, `POST /api/showcase/toggle`).

## Repo layout

```
cyberdeck/
├── README.md
├── install.sh                    # one-shot installer (run on Pi)
├── uninstall.sh
├── config.example.yaml
├── .env.example
├── pyproject.toml
├── package.json
│
├── backend/
│   ├── cyberdeck/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app + WebSocket
│   │   ├── config.py             # pydantic config loader
│   │   ├── scheduler.py          # APScheduler setup
│   │   ├── ws.py                 # WebSocket pub/sub
│   │   ├── cache.py              # SQLite + in-memory cache
│   │   └── integrations/
│   │       ├── base.py           # Integration ABC
│   │       ├── weather.py
│   │       ├── transit.py
│   │       ├── calendar.py       # Google + Notion joined
│   │       ├── spotify.py
│   │       ├── github.py
│   │       ├── rss.py
│   │       └── photos.py
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte      # Home
│   │   │   ├── transit/+page.svelte
│   │   │   ├── calendar/+page.svelte
│   │   │   ├── github/+page.svelte
│   │   │   ├── doomscroll/+page.svelte
│   │   │   ├── photos/+page.svelte
│   │   │   ├── pomodoro/+page.svelte
│   │   │   └── showcase/+page.svelte
│   │   ├── lib/
│   │   │   ├── ws.ts             # WebSocket client + stores
│   │   │   ├── api.ts            # REST helpers
│   │   │   └── widgets/          # tile components
│   │   └── app.css
│   └── static/
│
├── scripts/
│   ├── setup-kiosk.sh            # systemd units, autostart, screen blanking
│   ├── setup-ssh.sh              # key-based auth
│   ├── detect-display.sh         # writes detected resolution to config
│   ├── update.sh                 # git pull + rebuild + restart
│   └── auth/                     # one-shot OAuth helpers (run on laptop)
│       ├── google-auth.py
│       └── spotify-auth.py
│
├── systemd/
│   ├── cyberdeck-backend.service
│   └── cyberdeck-kiosk.service
│
└── docs/
    ├── setup.md                  # first-boot guide
    ├── integrations.md           # how to get each API key/token
    └── superpowers/specs/        # this file
```

## Install flow (`install.sh`)

**Prerequisite:** the repo is already cloned on the Pi (e.g., `git clone git@github.com:<oliver>/cyberdeck.git ~/cyberdeck`). The installer runs from the repo root.

1. **Sanity checks** — confirms RPi OS Bookworm 64-bit; refuses otherwise.
2. **System packages** — `apt install` Python 3.11+, Node 20+, Chromium, git, sqlite3, build-essential, Wayland kiosk deps.
3. **Backend setup** — creates venv, installs Python deps via `uv pip install -e .`.
4. **Frontend build** — `npm install && npm run build`. Backend serves the static bundle.
5. **Config bootstrap** — copies `config.example.yaml` → `~/.config/cyberdeck/config.yaml` if missing; same for `.env.example`.
6. **Display detection** — runs `detect-display.sh`; writes resolution to config.
7. **Systemd units** — drops both unit files into `~/.config/systemd/user/`, enables, reloads.
8. **SSH hardening** — runs `setup-ssh.sh` (idempotent; only enables key auth if a key is already installed; warns otherwise).
9. **Kiosk autostart** — configures Wayfire/labwc to launch the kiosk service at login; enables auto-login on TTY1.
10. **Reboot prompt.**

After install, Oliver SSHes in once, fills in `~/.config/cyberdeck/.env`, runs OAuth helpers from his laptop, SCPs token files over, then `systemctl --user restart cyberdeck-backend`. Frontend just refreshes — no rebuild for config changes.

**Updates:** `cd ~/cyberdeck && ./scripts/update.sh` — git pulls, rebuilds frontend if changed, restarts backend if changed, leaves config + secrets untouched.

## Configuration schema

`config.yaml` (committed as `config.example.yaml`):

```yaml
device:
  name: "O-Deck"
  resolution:                   # auto-filled by detect-display.sh; override here
    width: 1024
    height: 600
  timezone: "America/New_York"
  location:
    lat: 40.6926
    lon: -73.9869

home:
  layout: "default"
  hero_tiles: ["now_playing"]
  core_tiles: ["time", "weather", "transit", "calendar", "rss"]

audio:
  enabled: true
  master_volume: 0.6
  chimes:
    pomodoro: true
    weather_alert: true

weather:
  provider: "open-meteo"
  alerts:
    rain: true
    snow: true
    heat_spike_threshold_f: 90
    cold_drop_threshold_f: 25
    severe: true

transit:
  refresh_seconds: 30
  primary_stations:
    - station: "Jay St-MetroTech"
      stop_id: "A41N"
      lines: ["A", "C", "F", "R"]
    - station: "DeKalb Av"
      stop_id: "R30N"
      lines: ["Q"]
  secondary_stations:
    - station: "14 St-Union Sq"
      stop_id: "635S"
      lines: ["4", "5", "6", "R", "Q"]
    - station: "W 4 St-Wash Sq"
      stop_id: "A32S"
      lines: ["F", "A", "C"]
  show_alerts: true

calendar:
  google:
    calendar_ids: ["primary"]
  notion:
    todo_database_ids: []
    join_strategy: "event_link"
  view: "today_at_a_glance"

spotify:
  enabled: true

github:
  username: "<you>"
  show: ["recent_commits", "open_prs", "assigned_issues"]

rss:
  refresh_seconds: 600
  feeds:
    - name: "TLDR"
      url: "https://kill-the-newsletter.com/feeds/<your-id>.xml"
    - name: "Hacker News"
      url: "https://news.ycombinator.com/rss"
  ticker:
    enabled: true
    speed: "medium"
  headline_stack_size: 3

photos:
  source: "icloud_shared_album"
  icloud_share_url: "https://www.icloud.com/sharedalbum/#..."
  local_folder: "~/cyberdeck-photos"
  rotation_seconds: 30

pomodoro:
  presets:
    - name: "Classic"
      work_min: 25
      break_min: 5
      cycles: 4
      long_break_min: 15
    - name: "Deep"
      work_min: 50
      break_min: 10
      cycles: 3
      long_break_min: 20

doomscroll:
  sources: ["rss"]
  qr_open_on_phone: true

showcase:
  default_mode: "generative"
  music_reactive_when_playing: true
```

Secrets in `.env`:

```
GOOGLE_CALENDAR_CREDENTIALS_PATH=/home/pi/.config/cyberdeck/google-credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=/home/pi/.config/cyberdeck/google-token.json
NOTION_TOKEN=secret_xxx
SPOTIFY_CLIENT_ID=xxx
SPOTIFY_CLIENT_SECRET=xxx
SPOTIFY_REFRESH_TOKEN=xxx
GITHUB_TOKEN=ghp_xxx
```

Each integration has an implicit `enabled` derived from config presence — Oliver can ship a working dashboard before all integrations are configured. Pydantic validates on startup; missing required fields fail loudly with clear messages.

## Error handling

External APIs will fail. The dashboard must never crash, never show a stack trace on screen, and never block working widgets when one integration is down.

**Per-integration failure modes:**
- **Stale data** — every cached payload carries `fetched_at`. Frontend shows a subtle staleness indicator when older than expected refresh × 3.
- **Auth failure** — integration disables itself; one banner: "GitHub auth expired — see logs." Other widgets unaffected.
- **Network down** — all integrations hold last-cached value; banner: "Offline — last updated 2 min ago."
- **Rate limits** — APScheduler exponential backoff; logged, silent on UI unless persistent.
- **Hard crash in a worker** — caught at the integration boundary; logged; worker restarts after backoff.

**Frontend resilience:**
- WebSocket reconnects with backoff if backend dies.
- Widgets are independent — each one's render error stays scoped to that widget (Svelte error boundaries per widget).
- "Last updated" timestamps visible in fullscreen views.

**Logging:** systemd `journalctl`, structured JSON lines for integration events (fetch start/success/failure with timing). Log level configurable via env.

## Testing

Proportional, not exhaustive.

**Unit tests** for things with real logic:
- Config validation (Pydantic).
- Notion ↔ Google calendar join logic.
- Transit arrival sorting and grouping.
- RSS dedup.
- Weather alert trigger thresholds.
- Photo source rotation.

**Integration adapters** tested with **recorded fixtures** — actual API responses captured once and replayed. No live external calls in CI. Catches schema regressions when integrations are touched.

**Frontend** — Playwright smoke test that loads home, asserts each widget mounts and renders without error. No deep UI testing; that lives with Claude Design and the human eye.

**No mocks of internal modules.** Backend tests use real SQLite cache and real APScheduler with sped-up clocks.

**Manual test checklist** in `docs/setup.md` — post-install steps for end-to-end verification of each integration.

## Performance

Targets on Pi 4B (4GB):

| Component | Target | Ceiling |
|---|---|---|
| Backend RSS | <150 MB | ~250 MB |
| Chromium kiosk | <600 MB | ~700 MB (with HW accel) |
| Total system RAM | leaves ≥2 GB free | — |
| Idle CPU | <10% across cores | — |
| Showcase mode | 30 fps capped, GPU shaders | — |

**SD card lifetime:** the device runs 24/7. Writes are minimized:
- `/var/log` mounted as `tmpfs`.
- Ephemeral integration cache held in memory; SQLite writes only on real state changes (e.g., a new RSS item, not on every fetch).
- Logs rotate aggressively.

## Diagnostics

A hidden diagnostics page (`/diagnostics`) surfaces per-integration status, last fetch time, error counts, current memory/CPU. Reachable two ways:
- Tap the time tile 5× on-device.
- Visit `http://<pi-ip>:8080/diagnostics` from the laptop.

No Prometheus, no Grafana — one HTML page that's enough.

## Workflow checkpoint: Claude Design handoff (COMPLETE)

Visual design produced in Claude Design. Source-of-truth artifacts now live in repo:

- **`docs/design.md`** — design baseline (design intent, tokens, motion, IA, app patterns).
- **`design/screens/system.jsx`** — token system + shared shell primitives (`ODScreen`, `ODStatusBar`, `ODDock`, `SectionLabel`).
- **`design/screens/notes.jsx`** — shared mock data + helpers (`MTAPill`, `WeatherIcon`, `EQBars`, `Ticker`, `AlbumArt`).
- **`design/screens/variation-c3.jsx`** — home screen reference (C v3 "Atelier"): `ScreenCv3`, `DriftOrbs`, `RainOverlay`, `Grain`, `Sparkline`, `CommitHeartbeat`, `BlockBar`.
- **`design/screens/apps-1.jsx`** + **`apps-2.jsx`** — fullscreen app reference layouts (Pomodoro, Transit detail, Calendar, GitHub, Doomscroll, Photo, Showcase, Subway map, Diagnostics).
- **`design/O-Deck Home.html`** — runnable canvas of all variants.

### Locked design decisions

**Direction:** Variation C v3 "Atelier" — editorial cyberdeck, asymmetric, time-as-hero, slow blurred orb motion.

**Resolution:** 1024×600 (primary target). 800×480 supported via responsive collapse.

**Palette (from `system.jsx`):**
- `bg #15130f`, `bgRaised rgba(31,28,24,0.78)`, `bgSolid #1f1c18`
- `ink #f0e8d6`, `inkDim 55%`, `inkSub 32%`
- `accentSand #e6c89b` (primary emphasis), `accentSage #a8c19a` (live/healthy), `accentRose #d49a8e` (delay/warning), `accentLav #a08fb3` (music)
- `line rgba(240,232,214,0.08)`

**Type:** Inter (large numerals, headings, body), IBM Plex Mono (status, metadata, dock).

**Hero slot:** Now Playing only (right-side vertical strip, smaller art, type-forward). Pomodoro stays in launcher dock, fullscreen-only.

**Motion modes (driven by integration state):**
- `music` ← Spotify playing
- `rain` ← weather condition rain
- `thunder` ← weather alert thunder/storm
- `calm` ← default

Each mode swaps the orb palette and adds an overlay (rain streaks for `rain`/`thunder`, occasional flash for `thunder`, beat-pulsed orb radius for `music`).

**Showcase mode:** full-bleed generative visuals, no info overlay, tap-to-return. (Tension resolved.)

**Subway map:** abstract live treatment with animated train markers; not a literal MTA map clone.

**Doomscroll:** feed list + selected story detail; QR handoff to phone is the primary read action.

### Implementation guardrails from design

- Token system lifts from `system.jsx` → CSS variables / Tailwind theme.
- Reusable primitives become Svelte components: `<SectionLabel>`, `<ODStatusBar>`, `<ODDock>`, `<Ticker>`, `<MTAPill>`, `<Sparkline>`, `<CommitHeartbeat>`, `<AlbumArt>`, `<EQBars>`, `<BlockBar>`, `<WeatherIcon>`.
- Background motion via canvas (`<DriftOrbs>` + optional `<RainOverlay>` + `<Grain>` overlay).
- Performance: low orb count (≤8), blur via CSS `filter: blur()` on the canvas (cheap), no per-frame layout, prefer `transform`/`opacity`. Cap RAF where possible.
- Diagnostics screen drops the ambient layer (clarity > mood).

## Open items (from design, deferred to on-device pass)

- Final intensity envelope for `<DriftOrbs>` on real Pi hardware (may need to dial down particle/blur cost).
- Keep/cut ASCII system meter in home status line (currently optional).
- Final spacing/tightness after first on-device readability check at 4 ft.

## Success criteria for v1

- Boots into the dashboard with no manual intervention after power-on.
- Time, weather, transit, and calendar render correctly within 10 seconds of boot.
- Touchscreen tap opens the corresponding fullscreen view.
- All integrations recover gracefully from a 60-second network outage.
- Updating from a new commit is one command (`./scripts/update.sh`) and does not require reconfiguring secrets.
- Runs continuously for 7 days without intervention or memory creep beyond stated ceilings.
