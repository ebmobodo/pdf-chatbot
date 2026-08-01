#!/usr/bin/env bash
# Production entrypoint for Render (Docker Web Service).
# Render injects $PORT; we default to 8500 which is Streamlit's default
# and maps well to Render's $PORT (< 10000) for free tier.
set -euo pipefail

PORT="${PORT:-8500}"

exec streamlit run app.py \
  --server.port="${PORT}" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false