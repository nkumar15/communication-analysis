# Unified Dockerfile for Enterprise SSO
# Supports: B2B, Platform, B2C microservices AND E2E Testing

# ==========================================
# 1. Base Stage (Common Runtime)
# ==========================================
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies (common for all services)
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user and cache directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/.cache/huggingface && \
    chown -R appuser:appuser /app

# Ensure specialized libraries use this cache
ENV HF_HOME=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/torch

# ==========================================
# 2. Builder Stage (Dependency Caching)
# ==========================================
FROM base AS builder

WORKDIR /app

COPY requirements.txt .
# Install production deps using uv (10-100x faster than pip)
RUN uv pip install --system --no-cache -r requirements.txt

# ==========================================
# 3. Test Base Stage (Heavy Test Deps)
# ==========================================
FROM base AS test-base

# Install Playwright system dependencies (Heavy, but cached)
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Install test python dependencies using uv
COPY requirements.txt .
COPY requirements-ai-api.txt .
COPY requirements-test.txt .
RUN uv pip install --system --no-cache -r requirements-test.txt

# Install Playwright browsers (Heavy, cached)
# Set fixed path for browsers so both root and appuser can find them
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright && chmod 777 /ms-playwright

# Install Playwright browsers (Heavy, cached)
RUN playwright install chromium && chmod -R 777 /ms-playwright

# ==========================================
# 4. Production Stages (Microservices)
# ==========================================

# --- B2B Microservice ---
FROM builder AS b2b
USER appuser
# Copy only necessary code
COPY --chown=appuser:appuser core /app/core
COPY --chown=appuser:appuser infrastructure /app/infrastructure
COPY --chown=appuser:appuser modules/domains /app/modules/domains
COPY --chown=appuser:appuser modules/b2b /app/modules/b2b
COPY --chown=appuser:appuser migrations /app/migrations
EXPOSE 8000
CMD ["uvicorn", "modules.b2b.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Platform Microservice ---
FROM builder AS platform
USER appuser
COPY --chown=appuser:appuser core /app/core
COPY --chown=appuser:appuser infrastructure /app/infrastructure
COPY --chown=appuser:appuser modules/platform /app/modules/platform
COPY --chown=appuser:appuser migrations /app/migrations
EXPOSE 8001
CMD ["uvicorn", "modules.platform.main:app", "--host", "0.0.0.0", "--port", "8001"]

# --- B2C Microservice ---
FROM builder AS b2c
USER appuser
# Copy code
COPY core/ /app/core/
COPY infrastructure/ /app/infrastructure/
COPY modules/b2c/ /app/modules/b2c/
COPY modules/__init__.py /app/modules/
WORKDIR /app
EXPOSE 8002
CMD ["uvicorn", "modules.b2c.main:app", "--host", "0.0.0.0", "--port", "8002"]

# --- Domain Microservice (AI/RAG) ---
FROM builder AS domain

# Install AI-specific dependencies (builder already has requirements.txt)
# uv will only install the NEW packages from requirements-ai-api.txt
COPY requirements-ai-api.txt .
# Increase timeout for AI packages
ENV UV_HTTP_TIMEOUT=300
RUN uv pip install --system --no-cache -r requirements-ai-api.txt

USER appuser
# Copy code
COPY core/ /app/core/
COPY infrastructure/ /app/infrastructure/
COPY modules/domains/ /app/modules/domains/
COPY modules/__init__.py /app/modules/
WORKDIR /app
EXPOSE 8003
CMD ["uvicorn", "modules.domains.main:app", "--host", "0.0.0.0", "--port", "8003"]

# ==========================================
# 5. Test Runner Stage (Development)
# ==========================================
FROM test-base AS test
USER appuser
# Copy EVERYTHING for testing
COPY --chown=appuser:appuser . /app
ENV PYTHONPATH=/app
CMD ["python", "-m", "pytest", "tests/"]

# ==========================================
# 6. Domain Worker (AI/RAG Heavy Processing)
# ==========================================

# Domain Worker Builder - Install heavy AI dependencies
FROM base AS domain-worker-builder
WORKDIR /app

# Install additional system deps for heavy ML libraries
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install AI worker dependencies (heaviest requirements)
COPY requirements.txt .
COPY requirements-ai-api.txt .
COPY requirements-ai-worker.txt .
# Increase timeout for heavy AI packages (torch, nvidia, etc.)
ENV UV_HTTP_TIMEOUT=300
RUN uv pip install --system --no-cache -r requirements-ai-worker.txt

# Domain Worker Stage
FROM domain-worker-builder AS domain-worker
USER appuser

# Copy code
COPY --chown=appuser:appuser core /app/core
COPY --chown=appuser:appuser infrastructure /app/infrastructure
COPY --chown=appuser:appuser modules /app/modules
COPY --chown=appuser:appuser workers /app/workers

# Create cache directories for ML models
RUN mkdir -p /app/.cache/huggingface /home/appuser/.cache/docling

WORKDIR /app
CMD ["celery", "-A", "workers.domain_worker.celery_app", "worker", "--loglevel=info"]
