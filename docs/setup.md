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
