#!/bin/bash
# Run a ComfyUI workflow via API
# Usage: ./run-workflow.sh <workflow.json> [output_dir]

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <workflow.json> [output_dir]"
    exit 1
fi

WORKFLOW_FILE="$1"
OUTPUT_DIR="${2:-/workspace/ComfyUI/output}"
COMFYUI_URL="${COMFYUI_URL:-http://localhost:8188}"

# Check ComfyUI is running
if ! curl -s "$COMFYUI_URL/system_stats" > /dev/null 2>&1; then
    echo "Error: ComfyUI not running at $COMFYUI_URL"
    exit 1
fi

# Load workflow
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "Error: Workflow file not found: $WORKFLOW_FILE"
    exit 1
fi

# Extract prompt (handle wrapped format)
PROMPT=$(cat "$WORKFLOW_FILE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
prompt = d.get('prompt', d)
print(json.dumps(prompt))
")

# Get workflow name
WF_NAME=$(basename "$WORKFLOW_FILE" .json)

echo "=== Running: $WF_NAME ==="
START=$(date +%s)

# Submit workflow
RESULT=$(curl -s -X POST "$COMFYUI_URL/prompt" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": $PROMPT}")

PROMPT_ID=$(echo "$RESULT" | jq -r '.prompt_id // empty')
NODE_ERRORS=$(echo "$RESULT" | jq -r '.node_errors | length // 0')

if [ -z "$PROMPT_ID" ] || [ "$PROMPT_ID" = "null" ]; then
    echo "Error: Failed to submit workflow"
    echo "Node errors: $NODE_ERRORS"
    echo "$RESULT" | jq '.node_errors | keys[:5]' 2>/dev/null
    exit 1
fi

echo "Prompt ID: $PROMPT_ID"

# Wait for completion
for i in {1..300}; do
    HIST=$(curl -s "$COMFYUI_URL/history/$PROMPT_ID")
    STATUS=$(echo "$HIST" | jq -r ".[\"$PROMPT_ID\"].status.completed // false")
    STATUS_STR=$(echo "$HIST" | jq -r ".[\"$PROMPT_ID\"].status.status_str // empty")
    
    if [ "$STATUS" = "true" ]; then
        END=$(date +%s)
        DURATION=$((END - START))
        
        OUTPUT_FILE=$(echo "$HIST" | jq -r ".[\"$PROMPT_ID\"].outputs | to_entries[0].value.images[0].filename // empty")
        
        echo ""
        echo "✓ Complete in ${DURATION}s"
        echo "Output: $OUTPUT_FILE"
        
        # Return JSON result
        echo "{\"workflow\": \"$WF_NAME\", \"runtime_sec\": $DURATION, \"output\": \"$OUTPUT_FILE\", \"status\": \"success\"}"
        exit 0
    fi
    
    if [ "$STATUS_STR" = "error" ]; then
        ERROR_MSG=$(echo "$HIST" | jq -r ".[\"$PROMPT_ID\"].status.messages[-1][1].exception_message // \"Unknown error\"")
        echo ""
        echo "✗ Error: $ERROR_MSG"
        echo "{\"workflow\": \"$WF_NAME\", \"status\": \"error\", \"error\": \"$ERROR_MSG\"}"
        exit 1
    fi
    
    # Progress indicator
    if [ $((i % 10)) -eq 0 ]; then
        echo -n "."
    fi
    sleep 2
done

echo ""
echo "✗ Timeout after 600s"
exit 1
