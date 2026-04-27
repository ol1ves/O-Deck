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
