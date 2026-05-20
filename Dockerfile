# ============================================
# ParkSmart Backend - Production Dockerfile
# ============================================
# Multi-stage build with Python slim for minimal image size.
# Runs as non-root user for security.
# ============================================

# --------------- Stage 1: Builder ---------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    python -c "import spacy; spacy.cli.download('en_core_web_lg')"

# --------------- Stage 2: Runtime ---------------
FROM python:3.11-slim AS runtime

# Security: run as non-root user
RUN groupadd -r parksmart && useradd -r -g parksmart -d /app -s /sbin/nologin parksmart

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /root/.local /root/.local

# Copy spaCy model data
COPY --from=builder /usr/local/lib/python3.11/site-packages/en_core_web_lg /usr/local/lib/python3.11/site-packages/en_core_web_lg

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/
COPY main.py .
COPY .env.example .

# Create writable directories for data and logs
RUN mkdir -p /app/data /app/logs && \
    chown -R parksmart:parksmart /app

# Environment variables (overridden at runtime via docker-compose or .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Health check — polls the /api/health endpoint every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Switch to non-root user
USER parksmart

# Start the FastAPI server
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
