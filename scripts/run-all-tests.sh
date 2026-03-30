#!/bin/bash
# Run all IRP test workflows
# Usage: ./run-all-tests.sh [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
COMFYUI_URL="${COMFYUI_URL:-http://localhost:8188}"
DRY_RUN=false

if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE ==="
fi

# Check ComfyUI
if [ "$DRY_RUN" = false ]; then
    if ! curl -s "$COMFYUI_URL/system_stats" > /dev/null 2>&1; then
        echo "Error: ComfyUI not running"
        exit 1
    fi
    GPU=$(curl -s "$COMFYUI_URL/system_stats" | python3 -c "import sys,json; print(json.load(sys.stdin)['devices'][0]['name'])")
    echo "GPU: $GPU"
fi

echo ""
echo "=== Finding API-format workflows ==="

# Find all _api.json workflows
WORKFLOWS=$(find "$REPO_DIR/results" -name "*_api.json" -type f | sort)
TOTAL=$(echo "$WORKFLOWS" | wc -l)

echo "Found $TOTAL workflows"
echo ""

# Results array
PASSED=0
FAILED=0
RESULTS_FILE="/tmp/test_results_$(date +%Y%m%d_%H%M%S).json"
echo "[" > "$RESULTS_FILE"

for WF in $WORKFLOWS; do
    WF_NAME=$(basename "$(dirname "$WF")")/$(basename "$WF")
    
    if [ "$DRY_RUN" = true ]; then
        # Validate workflow format
        VALID=$(cat "$WF" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    prompt = d.get('prompt', d)
    if not prompt:
        print('empty')
    elif list(prompt.keys())[0].isdigit():
        print('valid')
    else:
        print('ui_format')
except:
    print('invalid')
" 2>/dev/null)
        
        if [ "$VALID" = "valid" ]; then
            echo "✓ $WF_NAME"
            ((PASSED++))
        else
            echo "✗ $WF_NAME ($VALID)"
            ((FAILED++))
        fi
    else
        echo "--- Running: $WF_NAME ---"
        RESULT=$("$SCRIPT_DIR/run-workflow.sh" "$WF" 2>&1)
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 0 ]; then
            ((PASSED++))
            echo "✓ PASSED"
        else
            ((FAILED++))
            echo "✗ FAILED"
            echo "$RESULT" | tail -3
        fi
        
        # Append to results
        echo "  {\"workflow\": \"$WF_NAME\", \"exit_code\": $EXIT_CODE}," >> "$RESULTS_FILE"
        echo ""
    fi
done

# Close JSON array
echo "  {}" >> "$RESULTS_FILE"
echo "]" >> "$RESULTS_FILE"

echo ""
echo "=== Summary ==="
echo "Total: $TOTAL"
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ "$DRY_RUN" = false ]; then
    echo "Results: $RESULTS_FILE"
fi

exit $FAILED
