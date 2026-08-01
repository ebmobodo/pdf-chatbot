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
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies (layer-cached) -----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- Application code ------------------------------------------------
COPY . .

# ---- Runtime ---------------------------------------------------------
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8500/_stcore/health', timeout=5)" || exit 1

CMD ["bash", "scripts/start.sh"]