#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PORT="${PORT:-5000}"

# CRITICAL: We must run with uvicorn (ASGI server), not plain python.
# We explicitly do NOT use multiple --workers here because the application relies
# on in-memory shared state (_user_bot_states, background asyncio tasks).
# Uvicorn's single asyncio event loop will handle 50+ users concurrently just fine.
echo "Starting FastAPI server with Uvicorn on port $PORT..."
exec uvicorn web_backend:app --host 0.0.0.0 --port "$PORT"
