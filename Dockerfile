# Multi-stage Dockerfile for News Sentiment Analyzer Backend
# Features: CPU-only PyTorch, multi-stage caching, non-root user, healthcheck

# -------------------------------------------------------------------
# Stage 1: Builder
# -------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build essentials for C extensions if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install CPU-only PyTorch first (drastically reduces image size)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy packaging specifications
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install application and ML dependencies
RUN pip install --no-cache-dir ".[ml,explain]"

# -------------------------------------------------------------------
# Stage 2: Runtime
# -------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install minimal runtime utilities (curl for healthchecks, sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user
RUN groupadd -g 1000 newsent && \
    useradd -u 1000 -g newsent -m -s /bin/bash newsent

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Default environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    LOG_FORMAT=json \
    LOG_LEVEL=INFO \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    DATABASE_URL=sqlite:////app/data/news_sentiment.db

# Create application data directory with proper ownership
RUN mkdir -p /app/data && chown -R newsent:newsent /app

# Copy application code and assets
COPY --chown=newsent:newsent pyproject.toml README.md alembic.ini ./
COPY --chown=newsent:newsent alembic/ ./alembic/
COPY --chown=newsent:newsent src/ ./src/
COPY --chown=newsent:newsent data/ ./data/

# Switch to non-root user
USER newsent

# Expose API port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default startup command
CMD ["uvicorn", "news_sentiment.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
