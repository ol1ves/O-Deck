# Install & Ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a one-shot `install.sh` that turns a freshly-flashed Raspberry Pi OS Bookworm 64-bit into a running O-Deck kiosk, plus all supporting scripts (display detection, SSH hardening, kiosk setup, OAuth helpers, update/uninstall), systemd unit files, and setup documentation.

**Architecture:** All scripts are idempotent bash. `install.sh` orchestrates them in order. Scripts do NOT run on the dev laptop — they run on the Pi via SSH or direct. OAuth helpers (`scripts/auth/`) run on the laptop and produce token files that get SCP'd to the Pi. Manual test checklist in `docs/setup.md`.

**Tech Stack:** bash, systemd user services, Wayfire/labwc, Python OAuth (google-auth-oauthlib, spotipy), uv (Python package manager), Node 20+, Chromium

**Dependency:** Plans 1–4 must be complete. `install.sh` assumes the repo is already cloned on the Pi.

---

## Plan Series

1. Backend Foundation ✅ done
2. Backend Integrations → `2026-04-26-backend-integrations.md`
3. Frontend Foundation → `2026-04-26-frontend-foundation.md`
4. Fullscreen Apps → `2026-04-26-fullscreen-apps.md`
5. **Install & Ops** ← you are here

---

## File Map

```
cyberdeck/
├── install.sh                      # CREATE: master installer (run on Pi)
├── uninstall.sh                    # CREATE
├── scripts/
│   ├── setup-kiosk.sh              # CREATE: Wayfire autostart + auto-login
│   ├── setup-ssh.sh                # CREATE: key-auth enforcement (idempotent)
│   ├── detect-display.sh           # CREATE: write detected resolution to config
│   ├── update.sh                   # CREATE: git pull + selective rebuild + restart
│   └── auth/
│       ├── google-auth.py          # CREATE: OAuth flow → token.json (run on laptop)
│       └── spotify-auth.py         # CREATE: OAuth flow → prints refresh token (run on laptop)
├── systemd/
│   ├── cyberdeck-backend.service   # CREATE
│   └── cyberdeck-kiosk.service     # CREATE
└── docs/
    ├── setup.md                    # CREATE: first-boot guide
    └── integrations.md             # CREATE: per-integration key/token instructions
```

---

## Task 1: Systemd Unit Files

**Files:**
- Create: `systemd/cyberdeck-backend.service`
- Create: `systemd/cyberdeck-kiosk.service`

These are user services (`~/.config/systemd/user/`). No root required.

- [ ] **Step 1: Write the failing verification test**

There's no unit test for systemd files, but we verify syntax:

```bash
# After creating the files, run:
systemd-analyze verify systemd/cyberdeck-backend.service 2>&1 || echo "verify not available (cross-compile)"
```

- [ ] **Step 2: Create `systemd/cyberdeck-backend.service`**

```ini
# systemd/cyberdeck-backend.service
[Unit]
Description=O-Deck Backend (FastAPI)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/cyberdeck
Environment=HOME=%h
ExecStart=%h/cyberdeck/.venv/bin/uvicorn cyberdeck.main:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5
# Write logs to journal only (no SD card writes)
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cyberdeck-backend

[Install]
WantedBy=default.target
```

- [ ] **Step 3: Create `systemd/cyberdeck-kiosk.service`**

```ini
# systemd/cyberdeck-kiosk.service
[Unit]
Description=O-Deck Kiosk (Chromium fullscreen)
After=graphical-session.target cyberdeck-backend.service
Wants=cyberdeck-backend.service
BindsTo=graphical-session.target

[Service]
Type=simple
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-1
# Wait for backend to be ready
ExecStartPre=/bin/bash -c 'for i in $(seq 1 30); do curl -sf http://localhost:8080/api/state && break; sleep 1; done'
ExecStart=/usr/bin/chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --enable-features=OverlayScrollbar \
  --touch-events=enabled \
  --ozone-platform=wayland \
  --window-size=1024,600 \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  http://localhost:8080
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cyberdeck-kiosk

[Install]
WantedBy=graphical-session.target
```

- [ ] **Step 4: Commit**

```bash
mkdir -p systemd
git add systemd/
git commit -m "feat(ops): systemd user unit files for backend and kiosk"
```

---

## Task 2: detect-display.sh

**Files:**
- Create: `scripts/detect-display.sh`

Detects the connected display resolution and writes it to `~/.config/cyberdeck/config.yaml`.

- [ ] **Step 1: Write a manual verification procedure**

```
After creating this script, verify on Pi:
  bash scripts/detect-display.sh
  cat ~/.config/cyberdeck/config.yaml | grep -A2 resolution
Expected: width and height updated to actual display values.
```

- [ ] **Step 2: Create `scripts/detect-display.sh`**

```bash
#!/usr/bin/env bash
# detect-display.sh — detect connected display resolution and write to config.yaml
# Idempotent. Safe to run multiple times.
set -euo pipefail

CONFIG_DIR="${HOME}/.config/cyberdeck"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"

detect_resolution() {
  local width=1024 height=600

  # Method 1: wlr-randr (Wayland)
  if command -v wlr-randr &>/dev/null; then
    local mode
    mode=$(wlr-randr 2>/dev/null | grep -oP '\d+x\d+' | head -1 || true)
    if [[ -n "$mode" ]]; then
      width="${mode%x*}"
      height="${mode#*x}"
      echo "Detected via wlr-randr: ${width}x${height}"
      echo "${width} ${height}"
      return
    fi
  fi

  # Method 2: xrandr (X11 fallback)
  if command -v xrandr &>/dev/null && [[ -n "${DISPLAY:-}" ]]; then
    local mode
    mode=$(xrandr 2>/dev/null | grep '^\s' | grep '*' | grep -oP '\d+x\d+' | head -1 || true)
    if [[ -n "$mode" ]]; then
      width="${mode%x*}"
      height="${mode#*x}"
      echo "Detected via xrandr: ${width}x${height}"
      echo "${width} ${height}"
      return
    fi
  fi

  # Method 3: /sys/class/drm (kernel)
  local drm_modes
  drm_modes=$(cat /sys/class/drm/*/modes 2>/dev/null | head -1 || true)
  if [[ -n "$drm_modes" ]]; then
    width="${drm_modes%x*}"
    height="${drm_modes#*x}"
    echo "Detected via /sys/class/drm: ${width}x${height}"
    echo "${width} ${height}"
    return
  fi

  echo "Could not detect display; defaulting to ${width}x${height}" >&2
  echo "${width} ${height}"
}

read -r WIDTH HEIGHT < <(detect_resolution)

mkdir -p "${CONFIG_DIR}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  cp "$(dirname "$0")/../config.example.yaml" "${CONFIG_FILE}"
  echo "Copied config.example.yaml → ${CONFIG_FILE}"
fi

# Use python3 to update the YAML safely (preserves structure and comments)
python3 - "${CONFIG_FILE}" "${WIDTH}" "${HEIGHT}" << 'PYEOF'
import sys, re

config_path, width, height = sys.argv[1], sys.argv[2], sys.argv[3]

with open(config_path) as f:
    content = f.read()

# Replace width and height under the resolution: block
content = re.sub(
    r'(resolution:\s*\n\s*width:\s*)\d+',
    lambda m: m.group(1) + width,
    content,
)
content = re.sub(
    r'(resolution:\s*\n\s*width:\s*\d+\s*\n\s*height:\s*)\d+',
    lambda m: m.group(1) + height,
    content,
)

with open(config_path, 'w') as f:
    f.write(content)

print(f"Updated {config_path}: resolution {width}x{height}")
PYEOF
```

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x scripts/detect-display.sh
git add scripts/detect-display.sh
git commit -m "feat(ops): detect-display.sh — auto-detect resolution and write to config.yaml"
```

---

## Task 3: setup-ssh.sh

**Files:**
- Create: `scripts/setup-ssh.sh`

Hardens SSH: disables password auth if a public key is already installed. Idempotent.

- [ ] **Step 1: Create `scripts/setup-ssh.sh`**

```bash
#!/usr/bin/env bash
# setup-ssh.sh — harden SSH: key-only auth if key is installed
# Idempotent. Will NOT lock you out if no key is installed.
set -euo pipefail

SSHD_CONFIG="/etc/ssh/sshd_config"
AUTHORIZED_KEYS="${HOME}/.ssh/authorized_keys"

echo "=== O-Deck SSH Hardening ==="

if [[ ! -s "${AUTHORIZED_KEYS}" ]]; then
  echo "WARNING: No authorized_keys found at ${AUTHORIZED_KEYS}."
  echo "         Add your public key before running this script to enable key-only auth."
  echo "         Skipping password auth changes to avoid lockout."
  exit 0
fi

echo "Found authorized key(s). Proceeding with hardening..."

# Backup sshd_config
cp "${SSHD_CONFIG}" "${SSHD_CONFIG}.bak.$(date +%Y%m%d%H%M%S)"

# Apply settings via sed (idempotent)
apply_setting() {
  local key="$1" value="$2"
  if grep -qP "^${key}\s" "${SSHD_CONFIG}"; then
    sudo sed -i "s|^${key}.*|${key} ${value}|" "${SSHD_CONFIG}"
  elif grep -qP "^#${key}\s" "${SSHD_CONFIG}"; then
    sudo sed -i "s|^#${key}.*|${key} ${value}|" "${SSHD_CONFIG}"
  else
    echo "${key} ${value}" | sudo tee -a "${SSHD_CONFIG}" > /dev/null
  fi
}

apply_setting "PasswordAuthentication" "no"
apply_setting "PubkeyAuthentication"   "yes"
apply_setting "PermitRootLogin"        "no"
apply_setting "X11Forwarding"          "no"
apply_setting "MaxAuthTries"           "3"

echo "Testing sshd_config syntax..."
sudo sshd -t

echo "Reloading sshd..."
sudo systemctl reload ssh || sudo systemctl reload sshd

echo "SSH hardening complete. Password auth disabled — key-only access."
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x scripts/setup-ssh.sh
git add scripts/setup-ssh.sh
git commit -m "feat(ops): setup-ssh.sh — idempotent SSH hardening (key-auth only when key exists)"
```

---

## Task 4: setup-kiosk.sh

**Files:**
- Create: `scripts/setup-kiosk.sh`

Configures Wayfire autostart, TTY1 auto-login, and screen blanking suppression.

- [ ] **Step 1: Create `scripts/setup-kiosk.sh`**

```bash
#!/usr/bin/env bash
# setup-kiosk.sh — configure Wayfire kiosk autostart and TTY1 auto-login
# Idempotent.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER="${USER:-pi}"
AUTOLOGIN_CONF="/etc/systemd/system/getty@tty1.service.d/autologin.conf"
WAYFIRE_CONFIG="${HOME}/.config/wayfire.ini"
WLROOTS_ENV="${HOME}/.config/environment.d/cyberdeck.conf"

echo "=== O-Deck Kiosk Setup ==="

# --- Auto-login on TTY1 ---
echo "Configuring TTY1 auto-login for user ${USER}..."
sudo mkdir -p "$(dirname "${AUTOLOGIN_CONF}")"
sudo tee "${AUTOLOGIN_CONF}" > /dev/null << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ${USER} --noclear %I \$TERM
EOF

# --- Wayfire config ---
echo "Configuring Wayfire for kiosk mode..."
mkdir -p "$(dirname "${WAYFIRE_CONFIG}")"

# Only set the autostart section; preserve other Wayfire settings
if [[ ! -f "${WAYFIRE_CONFIG}" ]]; then
  touch "${WAYFIRE_CONFIG}"
fi

# Ensure [autostart] section exists and has cyberdeck entry
python3 - "${WAYFIRE_CONFIG}" << 'PYEOF'
import sys, configparser

path = sys.argv[1]
config = configparser.ConfigParser(allow_no_value=True)
config.optionxform = str
config.read(path)

if not config.has_section("autostart"):
    config.add_section("autostart")

config.set("autostart", "cyberdeck", "systemctl --user start cyberdeck-kiosk.service")

# Disable screen blanking in [core]
if not config.has_section("core"):
    config.add_section("core")
config.set("core", "idle_timeout", "0")

with open(path, "w") as f:
    config.write(f)

print(f"Updated {path}")
PYEOF

# --- Environment variables for Wayland ---
mkdir -p "$(dirname "${WLROOTS_ENV}")"
tee "${WLROOTS_ENV}" > /dev/null << 'EOF'
# Wayland backend for Chromium
DISPLAY=:0
WAYLAND_DISPLAY=wayland-1
XDG_SESSION_TYPE=wayland
QT_QPA_PLATFORM=wayland
EOF

# --- Disable screen blanking via DPMS ---
# Add to .bash_profile so it runs at TTY login
BASH_PROFILE="${HOME}/.bash_profile"
BLANKING_CMD="xset s off -dpms 2>/dev/null; sway -c /dev/null &>/dev/null &"
MARKER="# cyberdeck-blanking"
if ! grep -q "${MARKER}" "${BASH_PROFILE}" 2>/dev/null; then
  printf '\n%s\n%s\n' "${MARKER}" "${BLANKING_CMD}" >> "${BASH_PROFILE}"
fi

# --- Reload systemd user daemon ---
systemctl --user daemon-reload || true

echo "Kiosk autostart configured."
echo "Reboot to activate. After reboot, TTY1 auto-logs in and Wayfire starts the kiosk."
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x scripts/setup-kiosk.sh
git add scripts/setup-kiosk.sh
git commit -m "feat(ops): setup-kiosk.sh — Wayfire autostart, TTY1 auto-login, screen blanking suppression"
```

---

## Task 5: update.sh

**Files:**
- Create: `scripts/update.sh`

Git pull + selective rebuild (frontend only if JS files changed) + selective restart.

- [ ] **Step 1: Create `scripts/update.sh`**

```bash
#!/usr/bin/env bash
# update.sh — pull latest code, rebuild if needed, restart services
# Run on Pi from ~/cyberdeck: ./scripts/update.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_DIR}"

echo "=== O-Deck Update ==="
echo "Pulling latest from origin..."

BEFORE=$(git rev-parse HEAD)
git pull --ff-only
AFTER=$(git rev-parse HEAD)

if [[ "${BEFORE}" == "${AFTER}" ]]; then
  echo "Already up to date. No changes."
  exit 0
fi

echo "Updated from ${BEFORE:0:7} → ${AFTER:0:7}"
git log --oneline "${BEFORE}..${AFTER}"

# Check what changed
BACKEND_CHANGED=$(git diff --name-only "${BEFORE}" "${AFTER}" | grep -E '^backend/|^pyproject\.toml' | wc -l)
FRONTEND_CHANGED=$(git diff --name-only "${BEFORE}" "${AFTER}" | grep -E '^frontend/' | wc -l)

# --- Backend ---
if [[ "${BACKEND_CHANGED}" -gt 0 ]]; then
  echo ""
  echo "Backend files changed — reinstalling dependencies..."
  .venv/bin/uv pip install -e . --quiet || \
    .venv/bin/pip install -e . --quiet
  echo "Restarting cyberdeck-backend..."
  systemctl --user restart cyberdeck-backend.service
  echo "Backend restarted."
else
  echo "No backend changes."
fi

# --- Frontend ---
if [[ "${FRONTEND_CHANGED}" -gt 0 ]]; then
  echo ""
  echo "Frontend files changed — rebuilding..."
  cd frontend
  npm ci --silent
  npm run build
  cd ..
  echo "Frontend rebuilt."
  # Kiosk reloads automatically (Chromium serves from build/ via backend)
  # Force Chromium reload by restarting kiosk service
  systemctl --user restart cyberdeck-kiosk.service
  echo "Kiosk restarted."
else
  echo "No frontend changes."
fi

echo ""
echo "Update complete. Services:"
systemctl --user status cyberdeck-backend.service --no-pager -l | head -5
systemctl --user status cyberdeck-kiosk.service --no-pager -l | head -5
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x scripts/update.sh
git add scripts/update.sh
git commit -m "feat(ops): update.sh — selective rebuild + restart on git pull"
```

---

## Task 6: uninstall.sh

**Files:**
- Create: `uninstall.sh`

- [ ] **Step 1: Create `uninstall.sh`**

```bash
#!/usr/bin/env bash
# uninstall.sh — remove O-Deck services and autostart config
# Does NOT delete config or secrets. Does NOT remove the repo.
set -euo pipefail

echo "=== O-Deck Uninstall ==="
echo "This removes services and autostart config."
echo "Config at ~/.config/cyberdeck/ and the repo are preserved."
read -rp "Continue? [y/N] " CONFIRM
[[ "${CONFIRM}" =~ ^[yY]$ ]] || { echo "Aborted."; exit 0; }

# Stop and disable services
for svc in cyberdeck-kiosk.service cyberdeck-backend.service; do
  if systemctl --user is-active "${svc}" &>/dev/null; then
    systemctl --user stop "${svc}"
    echo "Stopped ${svc}"
  fi
  if systemctl --user is-enabled "${svc}" &>/dev/null; then
    systemctl --user disable "${svc}"
    echo "Disabled ${svc}"
  fi
done

# Remove unit files
UNIT_DIR="${HOME}/.config/systemd/user"
rm -f "${UNIT_DIR}/cyberdeck-backend.service" "${UNIT_DIR}/cyberdeck-kiosk.service"
systemctl --user daemon-reload

# Remove Wayfire autostart entry
WAYFIRE_CONFIG="${HOME}/.config/wayfire.ini"
if [[ -f "${WAYFIRE_CONFIG}" ]]; then
  python3 - "${WAYFIRE_CONFIG}" << 'PYEOF'
import sys, configparser
path = sys.argv[1]
config = configparser.ConfigParser(allow_no_value=True)
config.optionxform = str
config.read(path)
if config.has_section("autostart") and config.has_option("autostart", "cyberdeck"):
    config.remove_option("autostart", "cyberdeck")
with open(path, "w") as f:
    config.write(f)
print(f"Removed cyberdeck from {path} autostart")
PYEOF
fi

# Remove auto-login
AUTOLOGIN_CONF="/etc/systemd/system/getty@tty1.service.d/autologin.conf"
if [[ -f "${AUTOLOGIN_CONF}" ]]; then
  sudo rm -f "${AUTOLOGIN_CONF}"
  sudo systemctl daemon-reload
  echo "Removed TTY1 auto-login"
fi

echo ""
echo "Uninstall complete."
echo "Config preserved at ~/.config/cyberdeck/"
echo "Repo preserved at $(pwd)"
echo "To fully remove: rm -rf ~/.config/cyberdeck && rm -rf ~/cyberdeck"
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x uninstall.sh
git add uninstall.sh
git commit -m "feat(ops): uninstall.sh — remove services and autostart, preserve config"
```

---

## Task 7: install.sh (master orchestrator)

**Files:**
- Create: `install.sh`

This is the main script Oliver runs once on a fresh Pi.

- [ ] **Step 1: Create `install.sh`**

```bash
#!/usr/bin/env bash
# install.sh — O-Deck one-shot installer for Raspberry Pi OS Bookworm 64-bit
# Prerequisites:
#   - Repo already cloned to ~/cyberdeck
#   - Run as the regular user (not root)
#   - Internet connectivity
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${REPO_DIR}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[info]${NC} $*"; }
warning() { echo -e "${YELLOW}[warn]${NC} $*"; }
error()   { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

echo ""
echo "  ██████╗       ██████╗ ███████╗ ██████╗██╗  ██╗"
echo "  ██╔═══██╗    ██╔══██╗██╔════╝██╔════╝██║ ██╔╝"
echo "  ██║   ██║    ██║  ██║█████╗  ██║     █████╔╝ "
echo "  ██║   ██║    ██║  ██║██╔══╝  ██║     ██╔═██╗ "
echo "  ╚██████╔╝    ██████╔╝███████╗╚██████╗██║  ██╗"
echo "   ╚═════╝     ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝"
echo ""
echo "  O-Deck Installer"
echo ""

# ─── Step 1: Sanity checks ───────────────────────────────────────────────────
info "Step 1/10: Sanity checks"

if [[ "$(uname -m)" != "aarch64" ]]; then
  error "This installer requires a 64-bit ARM system (aarch64). Got: $(uname -m)"
fi

if ! grep -qi "bookworm" /etc/os-release 2>/dev/null; then
  error "This installer requires Raspberry Pi OS Bookworm. Current OS may not be compatible."
fi

if [[ "${EUID}" -eq 0 ]]; then
  error "Do NOT run this script as root. Run as the regular user (e.g. pi)."
fi

info "OS: $(. /etc/os-release && echo "${PRETTY_NAME}")"
info "User: ${USER}, Home: ${HOME}"

# ─── Step 2: System packages ─────────────────────────────────────────────────
info "Step 2/10: Installing system packages"

sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  python3 python3-pip python3-venv python3-dev \
  nodejs npm \
  chromium-browser \
  git sqlite3 curl wget \
  build-essential \
  libssl-dev libffi-dev \
  wayfire wlr-randr \
  xdg-utils \
  fonts-open-sans

# Install uv (fast Python package manager)
if ! command -v uv &>/dev/null; then
  info "Installing uv (Python package manager)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

info "System packages installed."

# ─── Step 3: Backend setup ───────────────────────────────────────────────────
info "Step 3/10: Backend Python setup"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e ".[dev]"

info "Backend dependencies installed."

# ─── Step 4: Frontend build ──────────────────────────────────────────────────
info "Step 4/10: Frontend build"

cd frontend
npm ci --silent
npm run build
cd ..

info "Frontend built to frontend/build/."

# ─── Step 5: Config bootstrap ────────────────────────────────────────────────
info "Step 5/10: Config bootstrap"

CONFIG_DIR="${HOME}/.config/cyberdeck"
mkdir -p "${CONFIG_DIR}"

if [[ ! -f "${CONFIG_DIR}/config.yaml" ]]; then
  cp config.example.yaml "${CONFIG_DIR}/config.yaml"
  info "Copied config.example.yaml → ${CONFIG_DIR}/config.yaml"
else
  info "config.yaml already exists — skipping copy."
fi

if [[ ! -f "${CONFIG_DIR}/.env" ]]; then
  cp .env.example "${CONFIG_DIR}/.env"
  info "Copied .env.example → ${CONFIG_DIR}/.env"
  warning "Fill in ${CONFIG_DIR}/.env with your API keys and tokens."
else
  info ".env already exists — skipping copy."
fi

# ─── Step 6: Display detection ───────────────────────────────────────────────
info "Step 6/10: Display detection"

bash scripts/detect-display.sh || warning "Display detection failed — using defaults (1024x600)."

# ─── Step 7: Systemd units ───────────────────────────────────────────────────
info "Step 7/10: Systemd user services"

UNIT_DIR="${HOME}/.config/systemd/user"
mkdir -p "${UNIT_DIR}"

cp systemd/cyberdeck-backend.service "${UNIT_DIR}/"
cp systemd/cyberdeck-kiosk.service   "${UNIT_DIR}/"

systemctl --user daemon-reload
systemctl --user enable cyberdeck-backend.service
systemctl --user enable cyberdeck-kiosk.service

info "Systemd units installed and enabled."

# ─── Step 8: SSH hardening ───────────────────────────────────────────────────
info "Step 8/10: SSH hardening"

bash scripts/setup-ssh.sh || warning "SSH hardening skipped (no authorized keys — add your key first)."

# ─── Step 9: Kiosk autostart ─────────────────────────────────────────────────
info "Step 9/10: Kiosk autostart"

bash scripts/setup-kiosk.sh

# Enable lingering so user services start at boot without login
loginctl enable-linger "${USER}"

info "Kiosk autostart configured."

# ─── Step 10: Reboot prompt ──────────────────────────────────────────────────
info "Step 10/10: Installation complete!"

echo ""
echo "  Next steps BEFORE rebooting:"
echo ""
echo "  1. Fill in credentials:"
echo "     nano ${HOME}/.config/cyberdeck/.env"
echo ""
echo "  2. Run OAuth helpers FROM YOUR LAPTOP:"
echo "     python3 scripts/auth/google-auth.py"
echo "     python3 scripts/auth/spotify-auth.py"
echo "     Then SCP the token files to the Pi:"
echo "     scp google-token.json pi@<pi-ip>:~/.config/cyberdeck/"
echo ""
echo "  3. Set your timezone in config.yaml if not America/New_York:"
echo "     nano ${HOME}/.config/cyberdeck/config.yaml"
echo ""
echo "  4. Reboot:"
echo "     sudo reboot"
echo ""
echo "  After reboot, the dashboard should appear on the display."
echo "  SSH in to check logs: journalctl --user -u cyberdeck-backend -f"
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x install.sh
git add install.sh
git commit -m "feat(ops): install.sh — one-shot Pi installer (sanity check through reboot prompt)"
```

---

## Task 8: OAuth Helpers

**Files:**
- Create: `scripts/auth/google-auth.py`
- Create: `scripts/auth/spotify-auth.py`

These run on the **laptop**, not the Pi.

- [ ] **Step 1: Create `scripts/auth/google-auth.py`**

```python
#!/usr/bin/env python3
"""Google Calendar OAuth2 — run on laptop, produces token.json.
Then SCP token.json to Pi: ~/.config/cyberdeck/google-token.json

Usage:
  python3 scripts/auth/google-auth.py --credentials /path/to/credentials.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Install: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Calendar OAuth2 flow")
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        help="Path to credentials.json downloaded from Google Cloud Console",
    )
    parser.add_argument(
        "--output",
        default="google-token.json",
        help="Output path for the token file (default: google-token.json)",
    )
    args = parser.parse_args()

    creds_path = Path(args.credentials)
    if not creds_path.exists():
        print(f"Error: credentials file not found: {creds_path}")
        print("\nTo get credentials.json:")
        print("  1. Go to console.cloud.google.com")
        print("  2. Create a project → Enable Google Calendar API")
        print("  3. OAuth consent screen → External → add your email")
        print("  4. Credentials → Create OAuth client ID → Desktop app → Download JSON")
        sys.exit(1)

    print(f"Starting OAuth flow with {creds_path}...")
    print("A browser window will open. Grant access, then return here.")

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=8888, prompt="consent")

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(token_data, indent=2))

    print(f"\nToken saved to {output_path}")
    print("\nSCP to Pi:")
    print(f"  scp {output_path} pi@<pi-ip>:~/.config/cyberdeck/google-token.json")
    print("\nAlso SCP credentials.json:")
    print(f"  scp {creds_path} pi@<pi-ip>:~/.config/cyberdeck/google-credentials.json")
    print("\nThen update ~/.config/cyberdeck/.env on the Pi:")
    print("  GOOGLE_CALENDAR_CREDENTIALS_PATH=/home/pi/.config/cyberdeck/google-credentials.json")
    print("  GOOGLE_CALENDAR_TOKEN_PATH=/home/pi/.config/cyberdeck/google-token.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `scripts/auth/spotify-auth.py`**

```python
#!/usr/bin/env python3
"""Spotify OAuth2 — run on laptop, prints refresh token.
Copy the refresh token into ~/.config/cyberdeck/.env on the Pi.

Usage:
  SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=xxx python3 scripts/auth/spotify-auth.py

Or pass as args:
  python3 scripts/auth/spotify-auth.py --client-id xxx --client-secret xxx
"""
import argparse
import os
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import requests
except ImportError:
    print("Install: pip install requests")
    sys.exit(1)

SCOPE = "user-read-currently-playing user-read-playback-state"
REDIRECT_URI = "http://localhost:8889/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

received_code: str | None = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        global received_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            received_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authorization complete. Return to terminal.</h2></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args: object) -> None:
        pass  # suppress request logs


def main() -> None:
    parser = argparse.ArgumentParser(description="Spotify OAuth2 flow")
    parser.add_argument("--client-id",     default=os.environ.get("SPOTIFY_CLIENT_ID", ""))
    parser.add_argument("--client-secret", default=os.environ.get("SPOTIFY_CLIENT_SECRET", ""))
    args = parser.parse_args()

    client_id     = args.client_id
    client_secret = args.client_secret

    if not client_id or not client_secret:
        print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required.")
        print("Set as env vars or pass --client-id / --client-secret.")
        print("\nTo get credentials:")
        print("  1. Go to developer.spotify.com/dashboard")
        print("  2. Create an app → Settings → Copy Client ID + Client Secret")
        print("  3. Add redirect URI: http://localhost:8889/callback")
        sys.exit(1)

    auth_params = {
        "client_id":     client_id,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPE,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print(f"Opening browser for Spotify authorization...")
    webbrowser.open(auth_url)
    print(f"If browser didn't open, visit:\n  {auth_url}\n")

    server = HTTPServer(("localhost", 8889), CallbackHandler)
    print("Waiting for callback on localhost:8889...")
    server.handle_request()

    if received_code is None:
        print("Error: did not receive authorization code.")
        sys.exit(1)

    import base64
    creds_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type":   "authorization_code",
            "code":         received_code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Authorization": f"Basic {creds_b64}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    refresh_token = data.get("refresh_token", "")
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print(f"\nSpotify Refresh Token:\n  {refresh_token}")
    print("\nAdd these to ~/.config/cyberdeck/.env on the Pi:")
    print(f"  SPOTIFY_CLIENT_ID={client_id}")
    print(f"  SPOTIFY_CLIENT_SECRET={client_secret}")
    print(f"  SPOTIFY_REFRESH_TOKEN={refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x scripts/auth/google-auth.py scripts/auth/spotify-auth.py
git add scripts/auth/
git commit -m "feat(ops): OAuth helpers for Google Calendar and Spotify (run on laptop)"
```

---

## Task 9: Documentation

**Files:**
- Create: `docs/setup.md`
- Create: `docs/integrations.md`

- [ ] **Step 1: Create `docs/setup.md`**

```markdown
# O-Deck First-Boot Setup Guide

## Prerequisites

- Raspberry Pi 4B (4GB+)
- Raspberry Pi OS Bookworm 64-bit (Lite) flashed to SD card
- SSH access (pi@\<pi-ip\>)
- This repo cloned on the Pi: `git clone git@github.com:<you>/cyberdeck.git ~/cyberdeck`

---

## Step 1: Clone and install

```bash
ssh pi@<pi-ip>
cd ~/cyberdeck
bash install.sh
```

The installer will:
1. Check you're on Bookworm 64-bit
2. Install system packages (Python, Node, Chromium, Wayfire)
3. Set up Python venv + install dependencies
4. Build the frontend
5. Copy config templates
6. Detect display resolution
7. Install and enable systemd user services
8. Optionally harden SSH
9. Configure kiosk autostart

---

## Step 2: Fill in credentials

```bash
nano ~/.config/cyberdeck/.env
```

Fill in the values. See `docs/integrations.md` for how to get each one.

Minimum for a working dashboard (weather + transit work with no keys):
- No keys required for weather (Open-Meteo is free and open)
- No keys required for transit if `MTA_API_KEY` is left blank (legacy feed)

---

## Step 3: Run OAuth flows (on laptop)

```bash
# On laptop, from the repo directory:

# Google Calendar (optional):
pip install google-auth-oauthlib
python3 scripts/auth/google-auth.py --credentials ~/Downloads/credentials.json
scp google-token.json pi@<pi-ip>:~/.config/cyberdeck/google-token.json
scp ~/Downloads/credentials.json pi@<pi-ip>:~/.config/cyberdeck/google-credentials.json

# Spotify (optional):
pip install requests
SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=xxx python3 scripts/auth/spotify-auth.py
# Copy the refresh token into .env on Pi
```

---

## Step 4: Reboot

```bash
sudo reboot
```

The dashboard should appear on the display within 30 seconds of boot.

---

## Step 5: Verify

SSH back in after reboot:

```bash
# Backend health:
curl http://localhost:8080/api/state | python3 -m json.tool

# Service status:
systemctl --user status cyberdeck-backend
systemctl --user status cyberdeck-kiosk

# Live logs:
journalctl --user -u cyberdeck-backend -f
```

---

## Manual Integration Test Checklist

After first boot, verify each widget:

- [ ] **Time** — clock shows correct local time, seconds tick
- [ ] **Weather** — temperature and condition shown, sparkline visible
- [ ] **Transit** — at least one station shows train arrivals with minutes
- [ ] **Calendar** — today's events appear (requires Google auth)
- [ ] **Now Playing** — shows current track when Spotify plays (requires Spotify auth)
- [ ] **RSS** — ticker scrolls, headlines visible (may take 10 min to populate)
- [ ] **GitHub** — commits + PRs visible (requires GitHub token)
- [ ] **Photos** — photo rotates (local folder: add images to `~/cyberdeck-photos/`)

**Fullscreen app check:**
- [ ] Tap POMO → Pomodoro loads, Start works
- [ ] Tap GH → GitHub app loads
- [ ] Tap MAP → Subway map with animated trains
- [ ] Tap DOOM → RSS feed + QR code
- [ ] Tap PHOTO → Full-bleed photo
- [ ] Tap SHOW → Showcase (DriftOrbs), tap to return home
- [ ] Tap time 5× → Diagnostics page opens

**Resilience check:**
- [ ] Disconnect WiFi for 60s → reconnect → all widgets recover
- [ ] `systemctl --user restart cyberdeck-backend` → dashboard reconnects via WS

---

## Updates

```bash
cd ~/cyberdeck && ./scripts/update.sh
```

Only rebuilds what changed (backend or frontend). Leaves config and secrets untouched.
```

- [ ] **Step 2: Create `docs/integrations.md`**

```markdown
# O-Deck Integration Setup

Each integration is optional. Missing credentials disable that integration gracefully; other widgets continue to work.

---

## Weather (Open-Meteo)

**Auth:** None. Completely free.

Configure in `~/.config/cyberdeck/config.yaml`:
```yaml
device:
  location:
    lat: 40.6926   # your latitude
    lon: -73.9869  # your longitude
```

---

## Transit (MTA GTFS-RT)

**Auth:** None required (free open data feed).

If you get 401 errors, register for a free MTA API key at:
https://api.mta.info/#/AccessKey

Then add to `~/.config/cyberdeck/.env`:
```
MTA_API_KEY=your-key-here
```

Configure stations in `config.yaml` → `transit.primary_stations` and `transit.secondary_stations`.

To find stop IDs for your stations:
1. Download GTFS static data: https://api-endpoint.mta.info/Feeds/http://realtime.mta.info/
2. Look up your station in `stops.txt`
3. Stop IDs end in `N` (Uptown) or `S` (Downtown)
4. Example: Jay St–MetroTech A/C/F/R uptown = `A41N`

---

## Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Google Calendar API**
4. OAuth consent screen → External → Add your email as test user
5. Credentials → Create OAuth client ID → Desktop application → Download JSON as `credentials.json`
6. Run OAuth flow from your laptop:
   ```bash
   pip install google-auth-oauthlib
   python3 scripts/auth/google-auth.py --credentials credentials.json
   ```
7. SCP files to Pi:
   ```bash
   scp google-token.json pi@<pi-ip>:~/.config/cyberdeck/google-token.json
   scp credentials.json pi@<pi-ip>:~/.config/cyberdeck/google-credentials.json
   ```
8. Add to `.env`:
   ```
   GOOGLE_CALENDAR_CREDENTIALS_PATH=/home/pi/.config/cyberdeck/google-credentials.json
   GOOGLE_CALENDAR_TOKEN_PATH=/home/pi/.config/cyberdeck/google-token.json
   ```

---

## Notion

1. Go to [Notion Integrations](https://www.notion.so/profile/integrations)
2. Create a new internal integration → Select workspace
3. Copy the **Internal Integration Token**
4. Share your todo databases with the integration (share button → invite → your integration)
5. Get database IDs from the URL: `notion.so/<workspace>/<database-id>?v=...`
6. Add to `.env`:
   ```
   NOTION_TOKEN=secret_xxx
   ```
7. Add database IDs to `config.yaml`:
   ```yaml
   calendar:
     notion:
       todo_database_ids:
         - your-database-id-here
   ```

---

## Spotify

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app → Settings → note Client ID and Client Secret
3. Add redirect URI: `http://localhost:8889/callback`
4. Run OAuth flow from your laptop:
   ```bash
   pip install requests
   SPOTIFY_CLIENT_ID=xxx SPOTIFY_CLIENT_SECRET=xxx python3 scripts/auth/spotify-auth.py
   ```
5. Copy the refresh token to `.env`:
   ```
   SPOTIFY_CLIENT_ID=xxx
   SPOTIFY_CLIENT_SECRET=xxx
   SPOTIFY_REFRESH_TOKEN=xxx
   ```

---

## GitHub

1. Go to GitHub → Settings → Developer settings → Fine-grained personal access tokens
2. Create new token → Repository access: Public Repositories only (read-only)
3. Permissions: Contents (read), Issues (read), Pull requests (read), Metadata (read)
4. Add to `.env`:
   ```
   GITHUB_TOKEN=ghp_xxx
   ```
5. Add to `config.yaml`:
   ```yaml
   github:
     username: your-github-username
   ```

---

## RSS

Configure feeds in `config.yaml`:
```yaml
rss:
  feeds:
    - name: "TLDR"
      url: "https://kill-the-newsletter.com/feeds/<your-id>.xml"
    - name: "Hacker News"
      url: "https://news.ycombinator.com/rss"
    - name: "r/nyc"
      url: "https://www.reddit.com/r/nyc/.rss"
```

For TLDR: subscribe at https://tldr.tech and use kill-the-newsletter.com to get an RSS URL.

---

## Photos

### Local folder (simplest)
```bash
mkdir ~/cyberdeck-photos
# Drop photos into this folder from laptop:
scp ~/Pictures/*.jpg pi@<pi-ip>:~/cyberdeck-photos/
```

In `config.yaml`:
```yaml
photos:
  source: "local"
  local_folder: "~/cyberdeck-photos"
  rotation_seconds: 30
```

### iCloud Shared Album
1. On iPhone: Photos → open album → Share → Create Shared Album → get the share URL
2. In `config.yaml`:
   ```yaml
   photos:
     source: "icloud_shared_album"
     icloud_share_url: "https://www.icloud.com/sharedalbum/#B0xxx"
   ```

Note: iCloud shared album API is unofficial and may break if Apple changes their CDN.
The fallback is always local folder.
```

- [ ] **Step 3: Commit documentation**

```bash
mkdir -p docs
git add docs/setup.md docs/integrations.md
git commit -m "docs: first-boot setup guide and per-integration key instructions"
```

---

## Task 10: Final integration verification on Pi (manual)

This task is manual — execute on the Pi after installing.

- [ ] **Step 1: Run the installer**

```bash
ssh pi@<pi-ip>
cd ~/cyberdeck
bash install.sh
```

Expected: completes without errors, prints "Installation complete!".

- [ ] **Step 2: Add minimum credentials**

```bash
# Edit .env — at minimum, add GitHub token if desired
nano ~/.config/cyberdeck/.env
```

- [ ] **Step 3: Start backend manually to verify**

```bash
# Don't reboot yet — test backend manually first
cd ~/cyberdeck
.venv/bin/uvicorn cyberdeck.main:app --host 0.0.0.0 --port 8080
```

From laptop: `curl http://<pi-ip>:8080/api/state | python3 -m json.tool`

Expected: JSON with all integration keys.

- [ ] **Step 4: Reboot and verify kiosk**

```bash
sudo reboot
# After reboot, from laptop:
ssh pi@<pi-ip>
journalctl --user -u cyberdeck-backend -f
curl http://localhost:8080/api/state
systemctl --user status cyberdeck-kiosk
```

Expected: backend running, kiosk process started, dashboard visible on display.

- [ ] **Step 5: Run manual test checklist from docs/setup.md**

Go through every item in the "Manual Integration Test Checklist" section.

---

## Self-Review

**Spec coverage:**
- Sanity check (Bookworm 64-bit): ✅ in install.sh step 1
- System packages: ✅ Python, Node, Chromium, Wayfire, git, sqlite3
- Backend setup via uv: ✅ step 3
- Frontend build: ✅ step 4
- Config bootstrap: ✅ step 5 (copies config.example.yaml + .env.example)
- Display detection: ✅ step 6, detect-display.sh (3 detection methods)
- Systemd units: ✅ step 7, both services with backend health check
- SSH hardening: ✅ step 8, idempotent, no lockout risk
- Kiosk autostart: ✅ step 9, Wayfire + TTY1 auto-login + loginctl linger
- Reboot prompt: ✅ step 10
- OAuth helpers: ✅ google-auth.py, spotify-auth.py (run on laptop)
- update.sh: ✅ selective rebuild, no config overwrite
- uninstall.sh: ✅ preserves config + secrets
- docs/setup.md: ✅ post-install checklist
- docs/integrations.md: ✅ per-integration instructions with stop_id lookup note
- journalctl logs: ✅ both services log to journal (no SD card tmpfs writes needed — services are stateless for logs)

**Placeholder scan:** None.

**Type consistency:** Shell scripts — no types. Python helpers have `str | None` annotations for Python 3.10+ compatibility.

---

## Parallelization Strategy

- **This plan** depends on Plans 2, 3, 4 being complete (or nearly complete).
- Tasks 1–3 (systemd, detect-display, setup-ssh) are independent — can run in parallel.
- Task 7 (install.sh) depends on all other scripts existing.
- Task 9 (docs) can run in parallel with anything.
- Task 10 (manual verification) must run last, on the Pi.

**Recommended order:**
1. Tasks 1, 2, 3, 4, 5, 6 in parallel (all independent scripts)
2. Task 7 (install.sh) after all scripts exist
3. Task 8 (OAuth helpers) in parallel with Task 7
4. Task 9 (docs) in parallel
5. Task 10 (manual test) last, requires Pi hardware

---

## New Chat Handoff Prompt

```
You are implementing the O-Deck install and operations plan.

Repo: /Users/oliversantana/Documents/dev/cyberdeck
Worktree: main branch or a new feature/install-ops branch
Plan: docs/superpowers/plans/2026-04-26-install-ops.md

Context:
- Plans 1–4 (backend + frontend) are complete or nearly complete.
- You are writing: install.sh, uninstall.sh, scripts/setup-kiosk.sh, scripts/setup-ssh.sh,
  scripts/detect-display.sh, scripts/update.sh, scripts/auth/google-auth.py,
  scripts/auth/spotify-auth.py, systemd unit files, docs/setup.md, docs/integrations.md
- All scripts must be idempotent bash (except OAuth helpers which are Python and run on laptop).
- DO NOT run install.sh or systemd commands during implementation — they're for the Pi.
- Verify scripts with `bash -n <script>` (syntax check) after writing.
- After each task: `bash -n <script>` must pass.
- Use superpowers:subagent-driven-development.

Start with Task 1 (systemd unit files).
```
