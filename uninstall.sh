#!/usr/bin/env bash
# uninstall.sh — remove O-Deck services and autostart config
# Does NOT delete config or secrets. Does NOT remove the repo.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

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
echo "Repo preserved at ${REPO_DIR}"
echo "To fully remove: rm -rf ~/.config/cyberdeck && rm -rf ~/cyberdeck"
