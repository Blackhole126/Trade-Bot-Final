#!/usr/bin/env bash
# =====================================================================
# Render Start Script — Single Service, Both Backends
# rootDir: backend/
#
# Render assigns $PORT for the main web process (HFT backend).
# api_server runs on PORT+1 (ML predictions, internal only).
# Frontend calls HFT backend ($PORT) for all API calls.
# =====================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Writable dirs on Render (ephemeral filesystem) ──────────────────
export DATA_DIR="${DATA_DIR:-/tmp/data}"
export LOGS_DIR="${LOGS_DIR:-/tmp/logs}"
mkdir -p /tmp/logs \
         /tmp/data \
         /tmp/data/cache \
         /tmp/data/features \
         /tmp/data/logs \
         /tmp/stock_analysis \
         /tmp/data/backups

# Install Playwright browser binaries if playwright is installed
# (needed for browser-based scraping; falls back to requests-based methods if unavailable)
if python -c "import playwright" 2>/dev/null; then
    echo "[render_start] Installing Playwright Chromium browser..."
    python -m playwright install chromium --with-deps 2>/dev/null || echo "[render_start] Playwright Chromium install skipped (non-fatal)"
fi

# ── Load env from hft2/backend/env if present (local keys) ──────────
HFT2_ENV_FILE="${SCRIPT_DIR}/hft2/backend/env"
if [ -f "${HFT2_ENV_FILE}" ]; then
    echo "[render_start] Loading env from hft2/backend/env"
    # Export all non-comment, non-empty lines
    set -o allexport
    source "${HFT2_ENV_FILE}" || true
    set +o allexport
fi

# ── Port assignment ──────────────────────────────────────────────────
HFT_PORT="${PORT:-10000}"
API_PORT=$((HFT_PORT + 1))

# api_server reads PORT to decide what port to bind
export HFT2_BACKEND_URL="http://127.0.0.1:${HFT_PORT}"
export KARAN_ML_URL="http://127.0.0.1:${API_PORT}"
export DATA_SERVICE_URL="${DATA_SERVICE_URL:-http://127.0.0.1:8002}"

# ── Skip Fyers data service on Render (uses yfinance fallback) ───────
export FYERS_ALLOW_MOCK="${FYERS_ALLOW_MOCK:-true}"
export RENDER=true            # Flag so web_backend can detect cloud env

echo "=========================================="
echo " Trade Bot Unified Backend"
echo " HFT backend (main) -> port ${HFT_PORT}"
echo " ML  backend (side) -> port ${API_PORT}"
echo " DATA_DIR = ${DATA_DIR}"
echo "=========================================="

# ── Start ML api_server in background ───────────────────────────────
echo "[api_server] Starting on port ${API_PORT}..."
cd "${SCRIPT_DIR}"
PORT="${API_PORT}" python api_server.py &
API_PID=$!
echo "[api_server] PID=${API_PID}"

# Small delay to let api_server bind its port
sleep 5

# ── Start HFT web_backend in foreground (Render health-checks this) ──
echo "[web_backend] Starting on port ${HFT_PORT}..."
export PORT="${HFT_PORT}"
cd "${SCRIPT_DIR}/hft2/backend"
exec uvicorn web_backend:app --host 0.0.0.0 --port "${HFT_PORT}" --workers 1 --timeout-keep-alive 120 --log-level info --access-log
