#!/usr/bin/env bash
# Production entrypoint for Render (Docker Web Service).
# Render injects $PORT; we default to 10000 which is Render's default
# web-service port (Render's proxy routes traffic there).
set -euo pipefail

PORT="${PORT:-10000}"

echo "Starting Streamlit on 0.0.0.0:${PORT} (Render routes via \$PORT)"

exec streamlit run app.py \
  --server.port="${PORT}" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.fileWatcherType=none \
  --browser.gatherUsageStats=false