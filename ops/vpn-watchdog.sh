#!/bin/bash
# VPN Watchdog - checks VPN-Komarovo, reconnects if down, logs issues only
VPN_NAME="VPN-Komarovo"
LOG="$HOME/.openclaw/workspace/ops/vpn-watchdog.log"

if nmcli connection show --active 2>/dev/null | grep -q "$VPN_NAME"; then
  exit 0
fi

echo "$(date): VPN down, reconnecting..." >> "$LOG"
for i in 1 2 3; do
  nmcli connection up "$VPN_NAME" >> "$LOG" 2>&1
  sleep 5
  if nmcli connection show --active 2>/dev/null | grep -q "$VPN_NAME"; then
    echo "$(date): VPN restored on attempt $i" >> "$LOG"
    exit 0
  fi
done
echo "$(date): FAILED to restore VPN after 3 attempts" >> "$LOG"
