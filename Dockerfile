# syntax=docker/dockerfile:1

# =====================================================================
# PDF Chat Bot — production image for Render (Docker Web Service)
# =====================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# ---- System dependencies --------------------------------------------
# poppler-utils (pdf2image) and tesseract-ocr (pytesseract) power the OCR
# fallback for scanned PDFs in src/ocr.py. docling was dropped to stay well
# under Render's 512 MB free-tier RAM limit.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        curl \
        poppler-utils \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies (layer-cached) -----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- Application code ------------------------------------------------
COPY . .

# ---- Runtime ---------------------------------------------------------
# EXPOSE is informational only — Render routes to the port from $PORT
# (default 10000, or the override set in render.yaml). 10000 matches
# Render's default web-service port and is also the fallback used when
# PORT is unset (see scripts/start.sh).
EXPOSE 10000

# Healthcheck must probe whatever port the app actually bound to ($PORT),
# not a hardcoded one, or the container is marked unhealthy on Render (502).
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '10000') + '/_stcore/health', timeout=5)" || exit 1

CMD ["bash", "scripts/start.sh"]