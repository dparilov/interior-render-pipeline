#!/bin/bash
#
# Minimal Pod Render Execution
# Uploads render package, executes workflow, downloads results
#
# Usage: ./scripts/pod_render.sh <pod_ip> <pod_port> <render_package.zip>
#
# Output: render_timing.json with full timing breakdown

set -e

POD_IP="${1:?Usage: $0 <pod_ip> <pod_port> <render_package.zip>}"
POD_PORT="${2:?Usage: $0 <pod_ip> <pod_port> <render_package.zip>}"
RENDER_PACKAGE="${3:?Usage: $0 <pod_ip> <pod_port> <render_package.zip>}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_ed25519}"

# Extract experiment name from package
EXPERIMENT=$(basename "$RENDER_PACKAGE" | sed 's/_render_package.zip//')
OUTPUT_DIR=$(dirname "$RENDER_PACKAGE")

echo "=== Pod Render: $EXPERIMENT ==="
echo "Pod: $POD_IP:$POD_PORT"
echo "Package: $RENDER_PACKAGE"
echo ""

START_TOTAL=$(date +%s.%N)

# SSH helper
ssh_run() {
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        root@$POD_IP -p $POD_PORT -i $SSH_KEY "$@"
}

# SCP helper
scp_to() {
    scp -o StrictHostKeyChecking=no -P $POD_PORT -i $SSH_KEY "$1" "root@$POD_IP:$2"
}

scp_from() {
    scp -o StrictHostKeyChecking=no -P $POD_PORT -i $SSH_KEY "root@$POD_IP:$1" "$2"
}

# Step 1: Upload render package
echo "[1/4] Uploading render package..."
START=$(date +%s.%N)
PACKAGE_SIZE=$(stat -f%z "$RENDER_PACKAGE" 2>/dev/null || stat -c%s "$RENDER_PACKAGE")

scp_to "$RENDER_PACKAGE" "/tmp/"

# Extract on pod
PACKAGE_NAME=$(basename "$RENDER_PACKAGE")
ssh_run "cd /tmp && unzip -o $PACKAGE_NAME -d /workspace/ComfyUI/input/"

UPLOAD_SEC=$(echo "$(date +%s.%N) - $START" | bc)
echo "  Uploaded $PACKAGE_SIZE bytes in ${UPLOAD_SEC}s"

# Step 2: Submit workflow
echo "[2/4] Submitting workflow..."
START=$(date +%s.%N)

# Get workflow from extracted package
WORKFLOW=$(ssh_run "cat /workspace/ComfyUI/input/workflow_api.json")

# Submit to ComfyUI
PROMPT_RESPONSE=$(ssh_run "curl -s -X POST localhost:8188/prompt -H 'Content-Type: application/json' -d '$(echo "$WORKFLOW" | tr -d '\n')'")
PROMPT_ID=$(echo "$PROMPT_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('prompt_id', ''))")

if [ -z "$PROMPT_ID" ]; then
    echo "  FAIL: Could not submit workflow"
    echo "  Response: $PROMPT_RESPONSE"
    exit 1
fi

SUBMIT_SEC=$(echo "$(date +%s.%N) - $START" | bc)
echo "  Submitted: $PROMPT_ID (${SUBMIT_SEC}s)"

# Step 3: Wait for completion
echo "[3/4] Waiting for render..."
START=$(date +%s.%N)

MAX_WAIT=120
WAITED=0
OUTPUT_FILE=""

while [ $WAITED -lt $MAX_WAIT ]; do
    HISTORY=$(ssh_run "curl -s 'localhost:8188/history/$PROMPT_ID'")
    
    COMPLETED=$(echo "$HISTORY" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data:
    prompt_data = list(data.values())[0]
    status = prompt_data.get('status', {})
    if status.get('completed'):
        outputs = prompt_data.get('outputs', {})
        save_image = outputs.get('save_image', {})
        images = save_image.get('images', [])
        if images:
            print(images[0].get('filename', ''))
        else:
            print('DONE_NO_OUTPUT')
" 2>/dev/null)
    
    if [ -n "$COMPLETED" ]; then
        OUTPUT_FILE="$COMPLETED"
        break
    fi
    
    sleep 2
    WAITED=$((WAITED + 2))
    echo -n "."
done
echo ""

RENDER_SEC=$(echo "$(date +%s.%N) - $START" | bc)

if [ -z "$OUTPUT_FILE" ] || [ "$OUTPUT_FILE" = "DONE_NO_OUTPUT" ]; then
    echo "  FAIL: Render did not complete"
    exit 1
fi

echo "  Completed: $OUTPUT_FILE (${RENDER_SEC}s)"

# Step 4: Download results
echo "[4/4] Downloading results..."
START=$(date +%s.%N)

# Download output image
scp_from "/workspace/ComfyUI/output/$OUTPUT_FILE" "$OUTPUT_DIR/"
OUTPUT_SIZE=$(stat -f%z "$OUTPUT_DIR/$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_DIR/$OUTPUT_FILE")

DOWNLOAD_SEC=$(echo "$(date +%s.%N) - $START" | bc)
echo "  Downloaded $OUTPUT_SIZE bytes in ${DOWNLOAD_SEC}s"

TOTAL_SEC=$(echo "$(date +%s.%N) - $START_TOTAL" | bc)

# Calculate billable time (upload + render + download)
BILLABLE_SEC=$(echo "$UPLOAD_SEC + $SUBMIT_SEC + $RENDER_SEC + $DOWNLOAD_SEC" | bc)

# Output timing JSON
cat > "$OUTPUT_DIR/render_timing.json" << EOF
{
  "experiment": "$EXPERIMENT",
  "timestamp": "$(date -Iseconds)",
  "prompt_id": "$PROMPT_ID",
  "output_file": "$OUTPUT_FILE",
  "phases": {
    "upload": {"duration_sec": $UPLOAD_SEC, "bytes": $PACKAGE_SIZE},
    "submit": {"duration_sec": $SUBMIT_SEC},
    "render": {"duration_sec": $RENDER_SEC},
    "download": {"duration_sec": $DOWNLOAD_SEC, "bytes": $OUTPUT_SIZE}
  },
  "total_sec": $TOTAL_SEC,
  "billable_sec": $BILLABLE_SEC,
  "status": "ok"
}
EOF

echo ""
echo "=== Render Complete ==="
echo "Output: $OUTPUT_DIR/$OUTPUT_FILE"
echo "Total time: ${TOTAL_SEC}s"
echo "Billable time: ${BILLABLE_SEC}s"
echo "Timing: $OUTPUT_DIR/render_timing.json"
