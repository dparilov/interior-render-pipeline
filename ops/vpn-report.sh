#!/bin/bash
# vpn-report.sh — отправляет статус VPN watchdog в Telegram группу каждые 30 минут

LOG="/home/dima/.openclaw/workspace/ops/vpn-watchdog.log"
export PATH="/home/dima/.nvm/versions/node/v22.22.0/bin:$PATH"

# Считаем рестарты и ошибки
if [ -f "$LOG" ] && [ -s "$LOG" ]; then
    restarts=$(grep -c "Перезапускаю VPN" "$LOG" 2>/dev/null || echo 0)
    restored=$(grep -c "✅ VPN перезапущен" "$LOG" 2>/dev/null || echo 0)
    failed=$(grep -c "⚠️" "$LOG" 2>/dev/null || echo 0)
    last_event=$(tail -1 "$LOG" 2>/dev/null)

    if [ "$restarts" -eq 0 ]; then
        msg="✅ VPN watchdog: стабильно, рестартов нет"
    else
        msg="📊 VPN watchdog отчёт:
• Попыток рестарта: $restarts
• Успешно: $restored
• Не восстановлен: $failed
• Последнее: $last_event"
    fi
else
    msg="✅ VPN watchdog: лог пустой, проблем не было"
fi

openclaw message send --channel telegram --target "-1003596522926" --message "$msg" 2>/dev/null || true
