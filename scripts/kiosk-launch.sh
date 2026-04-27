#!/usr/bin/env bash
# kiosk-launch.sh — wait for backend then launch Chromium in kiosk mode.
# Called from wayfire autostart; runs inside the Wayland session.
set -euo pipefail

for i in $(seq 1 30); do
  curl -sf http://localhost:8080/api/state > /dev/null && break
  sleep 1
done

exec /usr/bin/chromium \
  --password-store=basic \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --touch-events=enabled \
  --ozone-platform=wayland \
  --window-size=800,480 \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  http://localhost:8080
