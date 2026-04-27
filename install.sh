#!/usr/bin/env bash
# install.sh — O-Deck one-shot installer for Raspberry Pi OS Bookworm 64-bit
# Prerequisites:
#   - Repo cloned anywhere (installer detects its own path)
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

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
else
  error "Cannot read /etc/os-release to detect operating system."
fi

if [[ "${ID:-}" != "debian" ]]; then
  error "This installer currently supports Debian-based systems only. Detected: ${ID:-unknown}"
fi

if [[ "${VERSION_CODENAME:-}" == "bookworm" ]]; then
  info "Detected Debian Bookworm-compatible system."
elif [[ "${VERSION_CODENAME:-}" == "trixie" ]]; then
  warning "Detected Debian Trixie. Proceeding, but package names/behavior may differ from Bookworm."
else
  error "This installer requires Debian Bookworm or Trixie. Detected codename: ${VERSION_CODENAME:-unknown}"
fi

if [[ "${EUID}" -eq 0 ]]; then
  error "Do NOT run this script as root. Run as the regular user (e.g. pi)."
fi

info "OS: $(. /etc/os-release && echo "${PRETTY_NAME}")"
info "User: ${USER}, Home: ${HOME}"

# ─── Step 2: System packages ─────────────────────────────────────────────────
info "Step 2/10: Installing system packages"

CHROMIUM_PKG=""

has_install_candidate() {
  local pkg="$1"
  local candidate
  candidate="$(apt-cache policy "${pkg}" 2>/dev/null | awk -F': ' '/Candidate:/ {print $2; exit}')"
  [[ -n "${candidate}" && "${candidate}" != "(none)" ]]
}

if has_install_candidate "chromium-browser"; then
  CHROMIUM_PKG="chromium-browser"
elif has_install_candidate "chromium"; then
  CHROMIUM_PKG="chromium"
else
  error "Could not find a Chromium package (tried: chromium-browser, chromium)."
fi

info "Using Chromium package: ${CHROMIUM_PKG}"

sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  python3 python3-pip python3-venv python3-dev \
  nodejs npm \
  "${CHROMIUM_PKG}" \
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

sed "s|CYBERDECK_REPO_DIR|${REPO_DIR}|g" systemd/cyberdeck-backend.service > "${UNIT_DIR}/cyberdeck-backend.service"
cp systemd/cyberdeck-kiosk.service "${UNIT_DIR}/"

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
