#!/usr/bin/env bash
# ==============================================================================
# News Sentiment Analyzer — Automated Scheduled Collection & Analysis Script
# ==============================================================================
# Usage:
#   ./scripts/scheduled_collection.sh
#
# Can be run via crontab (e.g. daily at 06:00 UTC):
#   0 6 * * * /path/to/Sentiment-Analyzer/scripts/scheduled_collection.sh >> /var/log/newsent-cron.log 2>&1
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "======================================================================"
echo "[${TIMESTAMP}] Starting scheduled news collection and sentiment analysis"
echo "======================================================================"

# Determine Python/newsent binary
if [[ -f "${ROOT_DIR}/.venv/bin/newsent" ]]; then
    NEWSENT="${ROOT_DIR}/.venv/bin/newsent"
elif command -v newsent &> /dev/null; then
    NEWSENT="$(command -v newsent)"
elif [[ -f "${ROOT_DIR}/.venv/bin/python" ]]; then
    NEWSENT="${ROOT_DIR}/.venv/bin/python -m news_sentiment.cli"
else
    NEWSENT="python3 -m news_sentiment.cli"
fi

SOURCE="${NEWS_SOURCE:-gdelt}"
LIMIT="${COLLECTION_LIMIT:-50}"
MODELS="${ACTIVE_MODELS:-vader}"

echo "[${TIMESTAMP}] Step 1: Collecting headlines across active topics (source: ${SOURCE}, limit: ${LIMIT})..."
${NEWSENT} collect --source "${SOURCE}" --limit "${LIMIT}"

echo "[${TIMESTAMP}] Step 2: Scoring unanalyzed headlines with model(s)..."
IFS=',' read -ra MODEL_ARRAY <<< "${MODELS}"
for model in "${MODEL_ARRAY[@]}"; do
    # Trim whitespace
    model="$(echo "${model}" | xargs)"
    if [[ -n "${model}" ]]; then
        echo "[${TIMESTAMP}] Running inference with model '${model}'..."
        ${NEWSENT} analyze --model "${model}" || {
            echo "[${TIMESTAMP}] Warning: Analysis for model '${model}' encountered an issue, proceeding to next model."
        }
    fi
done

COMPLETION_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "======================================================================"
echo "[${COMPLETION_TIME}] Scheduled collection and analysis successfully completed."
echo "======================================================================"
