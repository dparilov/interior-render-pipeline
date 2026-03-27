#!/bin/bash
# ComfyUI Watchdog - проверяет статус и рапортует проблемы
# Использование: comfyui-watchdog.sh [timeout_seconds]

TIMEOUT=${1:-300}  # 5 минут по умолчанию
API="http://127.0.0.1:8188"
LOG="/tmp/comfyui.log"

check_running() {
    pgrep -f "python main.py.*8188" > /dev/null
}

check_api() {
    curl -sf --max-time 5 "$API/system_stats" > /dev/null 2>&1
}

check_queue() {
    curl -sf --max-time 5 "$API/queue" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
running=len(d.get('queue_running',[]))
pending=len(d.get('queue_pending',[]))
print(f'{running},{pending}')
" 2>/dev/null
}

get_last_error() {
    tail -100 "$LOG" 2>/dev/null | grep -E "Error|Exception|Traceback|RuntimeError" | tail -5
}

# Статус
echo "=== ComfyUI Watchdog ==="
echo "Time: $(date '+%H:%M:%S')"

if ! check_running; then
    echo "❌ STATUS: NOT RUNNING"
    echo ""
    echo "Last errors from log:"
    get_last_error
    echo ""
    echo "ACTION: Restart ComfyUI with:"
    echo "  cd ~/ComfyUI && source venv/bin/activate && python main.py --listen --cpu &"
    exit 1
fi

if ! check_api; then
    echo "⚠️ STATUS: RUNNING BUT API NOT RESPONDING"
    echo "Process exists but API timeout. May be starting up or frozen."
    exit 2
fi

QUEUE=$(check_queue)
RUNNING=$(echo $QUEUE | cut -d',' -f1)
PENDING=$(echo $QUEUE | cut -d',' -f2)

echo "✅ STATUS: RUNNING"
echo "   API: OK"
echo "   Queue: $RUNNING running, $PENDING pending"

# Проверка на зависшую генерацию
if [ "$RUNNING" -gt 0 ]; then
    echo ""
    echo "⏳ Generation in progress..."
    
    # Проверить лог на прогресс
    LAST_PROGRESS=$(tail -20 "$LOG" 2>/dev/null | grep -E "^\s*[0-9]+%|it/s\]" | tail -1)
    if [ -n "$LAST_PROGRESS" ]; then
        echo "   Progress: $LAST_PROGRESS"
    fi
    
    # Проверить на ошибки в последних строках
    RECENT_ERROR=$(tail -10 "$LOG" 2>/dev/null | grep -E "Error|Exception" | head -1)
    if [ -n "$RECENT_ERROR" ]; then
        echo "⚠️ RECENT ERROR DETECTED:"
        echo "   $RECENT_ERROR"
    fi
fi

exit 0
