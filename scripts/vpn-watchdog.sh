#!/bin/bash
# vpn-watchdog.sh — следит за доступностью api.telegram.org и перезапускает VPN если нет связи

VPN_NAME="VPN-Komarovo"
CHECK_HOST="api.telegram.org"
CHECK_URL="https://api.telegram.org"
LOG_FILE="/tmp/vpn-watchdog.log"
MAX_LOG_LINES=500
FAIL_THRESHOLD=2   # сколько провалов подряд перед перезапуском
SLEEP_INTERVAL=30  # секунд между проверками

fail_count=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

trim_log() {
    if [ -f "$LOG_FILE" ]; then
        local lines
        lines=$(wc -l < "$LOG_FILE")
        if [ "$lines" -gt "$MAX_LOG_LINES" ]; then
            tail -n "$MAX_LOG_LINES" "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
        fi
    fi
}

check_telegram() {
    # Пробуем curl с таймаутом 10 сек
    if curl -sf --max-time 10 --head "$CHECK_URL" -o /dev/null 2>/dev/null; then
        return 0
    fi
    # Фоллбэк: просто ping
    if ping -c 1 -W 5 "$CHECK_HOST" &>/dev/null 2>&1; then
        return 0
    fi
    return 1
}

restart_vpn() {
    log "Перезапускаю VPN: $VPN_NAME"
    nmcli connection down "$VPN_NAME" 2>&1 | while read -r line; do log "  down: $line"; done
    sleep 3
    nmcli connection up "$VPN_NAME" 2>&1 | while read -r line; do log "  up: $line"; done
    sleep 5
    if check_telegram; then
        log "✅ VPN перезапущен, связь с Telegram восстановлена"
        return 0
    else
        log "⚠️  VPN перезапущен, но Telegram всё ещё недоступен"
        return 1
    fi
}

log "=== VPN Watchdog запущен (VPN: $VPN_NAME, цель: $CHECK_HOST, интервал: ${SLEEP_INTERVAL}s) ==="

while true; do
    trim_log

    if check_telegram; then
        if [ "$fail_count" -gt 0 ]; then
            log "✅ Telegram снова доступен (было сбоев: $fail_count)"
            fail_count=0
        fi
    else
        fail_count=$((fail_count + 1))
        log "❌ Telegram недоступен (сбой #$fail_count из $FAIL_THRESHOLD)"

        if [ "$fail_count" -ge "$FAIL_THRESHOLD" ]; then
            log "🔄 Порог достигнут, перезапускаю VPN..."
            restart_vpn
            fail_count=0
        fi
    fi

    sleep "$SLEEP_INTERVAL"
done
