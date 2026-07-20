FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── System deps ───────────────────────────────────────────────────────────────
# tesseract-ocr         — OCR engine
# tesseract-ocr-ben     — Bangla language pack
# tesseract-ocr-eng     — English language pack (usually included)
# libpq-dev             — PostgreSQL client
# gcc                   — compile Python extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    tesseract-ocr \
    tesseract-ocr-ben \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ── App code ──────────────────────────────────────────────────────────────────
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
