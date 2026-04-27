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
