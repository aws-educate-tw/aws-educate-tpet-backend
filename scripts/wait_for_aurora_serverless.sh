#!/bin/bash
# wait_for_aurora_serverless.sh
#
# This script waits for Aurora Serverless v2 to become ready by polling the health endpoint.
# It ensures the database is awake and accepting connections before running migrations.
#
# Usage:
#   ./wait_for_aurora_serverless.sh <health_check_url> [max_retries] [retry_interval]
#
# Arguments:
#   health_check_url  - Required. The URL to poll for health status.
#   max_retries       - Optional. Maximum number of retry attempts (default: 30)
#   retry_interval    - Optional. Seconds between retries (default: 10)
#
# Exit Codes:
#   0 - Success (Aurora Serverless is healthy)
#   1 - Failure (timeout or error)
#
# Example:
#   ./wait_for_aurora_serverless.sh "https://dev-email-service-internal-api-tpet.aws-educate.tw/dev/email-service/health"

set -euo pipefail

# Arguments
HEALTH_CHECK_URL="${1:-}"
MAX_RETRIES="${2:-30}"
RETRY_INTERVAL="${3:-10}"

# Validation
if [ -z "$HEALTH_CHECK_URL" ]; then
    echo "ERROR: Health check URL is required"
    echo "Usage: $0 <health_check_url> [max_retries] [retry_interval]"
    exit 1
fi

# Main loop
COUNTER=0

echo "============================================"
echo "Aurora Serverless v2 Wake-Up Script"
echo "============================================"
echo "Health Check URL: ${HEALTH_CHECK_URL}"
echo "Max Retries: ${MAX_RETRIES}"
echo "Retry Interval: ${RETRY_INTERVAL} seconds"
echo "Total Timeout: $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
echo "============================================"
echo ""

while [ $COUNTER -lt $MAX_RETRIES ]; do
    COUNTER=$((COUNTER + 1))

    # Make the request and capture response
    RESPONSE=$(curl -s "${HEALTH_CHECK_URL}" 2>/dev/null || echo '{"status":"CONNECTION_ERROR"}')

    # Parse status from JSON response
    STATUS=$(echo "$RESPONSE" | jq -r '.status // "UNKNOWN"' 2>/dev/null || echo "PARSE_ERROR")

    echo "[Attempt ${COUNTER}/${MAX_RETRIES}] Status: ${STATUS}"

    if [ "$STATUS" = "HEALTHY" ]; then
        echo ""
        echo "============================================"
        echo "SUCCESS: Aurora Serverless is ready!"
        echo "Database connection confirmed."
        echo "============================================"
        exit 0
    fi

    if [ $COUNTER -lt $MAX_RETRIES ]; then
        echo "  Database not ready. Waiting ${RETRY_INTERVAL} seconds before retry..."
        sleep $RETRY_INTERVAL
    fi
done

echo ""
echo "============================================"
echo "ERROR: Aurora Serverless failed to become ready"
echo "Exhausted all ${MAX_RETRIES} retry attempts"
echo "============================================"
exit 1
