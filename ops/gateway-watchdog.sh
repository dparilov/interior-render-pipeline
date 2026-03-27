#!/bin/bash
# Gateway Watchdog — проверяет Telegram polling и рестартует если завис
# Запускать через cron каждые 5 минут

LOG="/tmp/openclaw/gateway-watchdog.log"
GATEWAY_LOG="/tmp/openclaw/openclaw-$(date +%Y-%m-%d).log"
LAST_ACTIVITY_FILE="/tmp/openclaw/last-telegram-activity"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

# Проверяем что gateway работает
if ! systemctl --user is-active --quiet openclaw-gateway; then
    log "Gateway not running, starting..."
    systemctl --user start openclaw-gateway
    exit 0
fi

# Ищем последнюю активность Telegram (sendMessage или incoming)
LAST_TG_LINE=$(grep -E "telegram.*(sendMessage|inbound|update)" "$GATEWAY_LOG" 2>/dev/null | tail -1)

if [ -z "$LAST_TG_LINE" ]; then
    # Нет активности вообще — может только запустился
    UPTIME=$(systemctl --user show openclaw-gateway --property=ActiveEnterTimestamp --value)
    log "No Telegram activity found. Gateway uptime: $UPTIME"
    exit 0
fi

# Извлекаем timestamp последней активности
LAST_TS=$(echo "$LAST_TG_LINE" | grep -oP '"date":"[^"]+"' | head -1 | cut -d'"' -f4)

if [ -z "$LAST_TS" ]; then
    log "Could not parse timestamp from log"
    exit 0
fi

# Конвертируем в epoch
LAST_EPOCH=$(date -d "$LAST_TS" +%s 2>/dev/null)
NOW_EPOCH=$(date +%s)

if [ -z "$LAST_EPOCH" ]; then
    log "Could not convert timestamp: $LAST_TS"
    exit 0
fi

# Если прошло больше 10 минут без активности — подозрительно
# Но рестартуем только если есть признаки зависания
DIFF=$((NOW_EPOCH - LAST_EPOCH))

if [ $DIFF -gt 600 ]; then
    # Проверяем есть ли heartbeat (каждые 30 мин) — если есть, gateway жив
    LAST_HB=$(grep "heartbeat" "$GATEWAY_LOG" 2>/dev/null | tail -1 | grep -oP '"date":"[^"]+"' | cut -d'"' -f4)
    
    if [ -n "$LAST_HB" ]; then
        HB_EPOCH=$(date -d "$LAST_HB" +%s 2>/dev/null)
        HB_DIFF=$((NOW_EPOCH - HB_EPOCH))
        
        if [ $HB_DIFF -lt 2100 ]; then
            # Heartbeat был менее 35 мин назад — gateway жив, просто нет сообщений
            exit 0
        fi
    fi
    
    log "No Telegram activity for ${DIFF}s, no recent heartbeat. Restarting gateway..."
    systemctl --user restart openclaw-gateway
    sleep 5
    
    if systemctl --user is-active --quiet openclaw-gateway; then
        log "Gateway restarted successfully"
    else
        log "ERROR: Gateway failed to restart!"
    fi
fi
