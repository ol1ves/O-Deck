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
python3 - "${WAYFIRE_CONFIG}" "${REPO_DIR}" << 'PYEOF'
import sys, configparser

path, repo_dir = sys.argv[1], sys.argv[2]
config = configparser.ConfigParser(allow_no_value=True)
config.optionxform = str
config.read(path)

if not config.has_section("autostart"):
    config.add_section("autostart")

config.set("autostart", "cyberdeck", f"{repo_dir}/scripts/kiosk-launch.sh")

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
BLANKING_CMD="xset s off -dpms 2>/dev/null; wayfire &>/dev/null &"
MARKER="# cyberdeck-blanking"
if ! grep -q "${MARKER}" "${BASH_PROFILE}" 2>/dev/null; then
  printf '\n%s\n%s\n' "${MARKER}" "${BLANKING_CMD}" >> "${BASH_PROFILE}"
fi

# --- Reload systemd user daemon ---
systemctl --user daemon-reload || true

echo "Kiosk autostart configured."
echo "Reboot to activate. After reboot, TTY1 auto-logs in and Wayfire starts the kiosk."
