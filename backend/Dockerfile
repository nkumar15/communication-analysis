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

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

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
COPY requirements-test.txt .
RUN uv pip install --system --no-cache -r requirements.txt && \
    uv pip install --system --no-cache -r requirements-test.txt

# Install Playwright browsers (Heavy, cached)
RUN playwright install chromium

# ==========================================
# 4. Production Stages (Microservices)
# ==========================================

# --- B2B Microservice ---
FROM builder AS b2b
USER appuser
# Copy only necessary code
COPY --chown=appuser:appuser core /app/core
COPY --chown=appuser:appuser services/domains /app/services/domains
COPY --chown=appuser:appuser services/b2b /app/services/b2b
COPY --chown=appuser:appuser migrations /app/migrations
EXPOSE 8000
CMD ["uvicorn", "services.b2b.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Platform Microservice ---
FROM builder AS platform
USER appuser
COPY --chown=appuser:appuser core /app/core
COPY --chown=appuser:appuser services/platform /app/services/platform
COPY --chown=appuser:appuser migrations /app/migrations
EXPOSE 8001
CMD ["uvicorn", "services.platform.main:app", "--host", "0.0.0.0", "--port", "8001"]

# --- B2C Microservice ---
FROM builder AS b2c
USER appuser
# Copy code
COPY core/ /app/core/
COPY services/b2c/ /app/services/b2c/
COPY services/__init__.py /app/services/
WORKDIR /app
EXPOSE 8002
CMD ["uvicorn", "services.b2c.main:app", "--host", "0.0.0.0", "--port", "8002"]

# --- Domain Microservice ---
FROM builder AS domain
USER appuser
# Copy code
COPY core/ /app/core/
COPY services/domains/ /app/services/domains/
COPY services/__init__.py /app/services/
WORKDIR /app
EXPOSE 8003
CMD ["uvicorn", "services.domains.main:app", "--host", "0.0.0.0", "--port", "8003"]

# ==========================================
# 5. Test Runner Stage (Development)
# ==========================================
FROM test-base AS test
USER appuser
# Copy EVERYTHING for testing
COPY --chown=appuser:appuser . /app
ENV PYTHONPATH=/app
CMD ["python", "-m", "pytest", "tests/"]
