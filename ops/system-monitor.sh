#!/bin/bash
# Мониторинг системы каждые 5 секунд
# Запуск: nohup ./system-monitor.sh > /tmp/sysmon.log 2>&1 &

LOG_FILE="${1:-/tmp/sysmon.jsonl}"
INTERVAL="${2:-5}"

echo "Starting system monitor, logging to $LOG_FILE every ${INTERVAL}s"
echo "PID: $$"

while true; do
    TIMESTAMP=$(date -Iseconds)
    
    # RAM
    read TOTAL USED FREE SHARED BUFF AVAIL <<< $(free -b | awk '/Mem:/ {print $2, $3, $4, $5, $6, $7}')
    RAM_TOTAL_GB=$(echo "scale=2; $TOTAL / 1024 / 1024 / 1024" | bc)
    RAM_USED_GB=$(echo "scale=2; $USED / 1024 / 1024 / 1024" | bc)
    RAM_AVAIL_GB=$(echo "scale=2; $AVAIL / 1024 / 1024 / 1024" | bc)
    RAM_PCT=$(echo "scale=1; $USED * 100 / $TOTAL" | bc)
    
    # CPU load
    read LOAD1 LOAD5 LOAD15 <<< $(cat /proc/loadavg | awk '{print $1, $2, $3}')
    
    # Swap
    read SWAP_TOTAL SWAP_USED <<< $(free -b | awk '/Swap:/ {print $2, $3}')
    SWAP_USED_GB=$(echo "scale=2; $SWAP_USED / 1024 / 1024 / 1024" | bc)
    
    # ComfyUI process
    COMFY_PID=$(pgrep -f "python.*main.py.*8188" | head -1)
    if [ -n "$COMFY_PID" ]; then
        COMFY_RSS=$(ps -o rss= -p $COMFY_PID 2>/dev/null | awk '{print $1/1024/1024}')
        COMFY_STATUS="running"
    else
        COMFY_RSS="0"
        COMFY_STATUS="stopped"
    fi
    
    # Write JSON line
    echo "{\"ts\":\"$TIMESTAMP\",\"ram_used_gb\":$RAM_USED_GB,\"ram_avail_gb\":$RAM_AVAIL_GB,\"ram_pct\":$RAM_PCT,\"swap_gb\":$SWAP_USED_GB,\"load1\":$LOAD1,\"load5\":$LOAD5,\"comfy\":\"$COMFY_STATUS\",\"comfy_gb\":$COMFY_RSS}" >> "$LOG_FILE"
    
    # Alert if RAM > 90%
    if (( $(echo "$RAM_PCT > 90" | bc -l) )); then
        echo "⚠️ WARNING: RAM at ${RAM_PCT}% - $TIMESTAMP"
    fi
    
    sleep $INTERVAL
done
