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
