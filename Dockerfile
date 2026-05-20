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

# Create and use a virtualenv (portable across stages)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model inside the venv
RUN python -m spacy download en_core_web_lg

# --------------- Stage 2: Runtime ---------------
FROM python:3.11-slim AS runtime

# Security: run as non-root user
RUN groupadd -r parksmart && useradd -r -g parksmart -d /app -s /sbin/nologin parksmart

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

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
