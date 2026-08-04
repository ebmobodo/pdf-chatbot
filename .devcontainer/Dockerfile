# syntax=docker/dockerfile:1

# Dev container image for PDF Chat Bot.
#
# Adds OCR system dependencies (poppler-utils, tesseract-ocr) on top of the
# standard Python image so the optional OCR fallback (src/ocr.py) works out
# of the box during development. Runtime pip deps are installed in
# postCreateCommand so requirements.txt changes pick up automatically.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ---- System dependencies (incl. OCR toolchain) ------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/pdf-chatbot
