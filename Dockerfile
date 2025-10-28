# Multi-stage Dockerfile for terraform-ingest
# Supports three execution modes:
# 1. CLI mode: terraform-ingest ingest config.yaml
# 2. API mode: FastAPI REST service on port 8000
# 3. MCP mode: FastMCP server for AI agent access

# ============================================================================
# Stage 1: Builder - Lightweight (no embeddings)
# ============================================================================
FROM python:3.13-slim AS builder-slim

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

ARG DEPLOY_VERSION

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VERSION=$DEPLOY_VERSION

WORKDIR /build

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Build the application with uv (without embeddings dependencies)
RUN if [ -n "$VERSION" ]; then \
        SETUPTOOLS_SCM_PRETEND_VERSION=$VERSION; \
    fi && \
    uv sync --frozen && \
    uv build --sdist --wheel

# ============================================================================
# Stage 1b: Builder - With Embeddings
# ============================================================================
FROM python:3.13-slim AS builder-embeddings

# Install build dependencies (includes additional libs for embeddings)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

ARG DEPLOY_VERSION

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VERSION=$DEPLOY_VERSION

WORKDIR /build

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Build the application with embeddings dependencies
RUN if [ -n "$VERSION" ]; then \
        SETUPTOOLS_SCM_PRETEND_VERSION=$VERSION; \
    fi && \
    uv sync --frozen --extra embeddings && \
    uv build --sdist --wheel

# ============================================================================
# Stage 2: Runtime Base (Lightweight - no embeddings)
# ============================================================================
FROM python:3.13-slim AS runtime-base-slim

WORKDIR /app

# Install runtime dependencies (git for cloning repos, ca-certificates for HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the application and its dependencies (without embeddings)
COPY --from=builder-slim /build/dist /tmp/dist
RUN pip install --no-cache-dir /tmp/dist/*.whl && rm -rf /tmp/dist

# Create directories for volumes
RUN mkdir -p /app/config /app/output /app/repos

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TERRAFORM_INGEST_CONFIG=/app/config/config.yaml

# Health check function (shared across modes)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# ============================================================================
# Stage 2b: Runtime Base With Embeddings
# ============================================================================
FROM python:3.13-slim AS runtime-base-embeddings

WORKDIR /app

# Install runtime dependencies plus build tools for embeddings
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install the application with embeddings dependencies
COPY --from=builder-embeddings /build/dist /tmp/dist
RUN pip install --no-cache-dir /tmp/dist/*.whl && rm -rf /tmp/dist

# Create directories for volumes
RUN mkdir -p /app/config /app/output /app/repos

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TERRAFORM_INGEST_CONFIG=/app/config/config.yaml

# Health check function
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# ============================================================================
# Stage 3: Development Mode (optional - slim variant)
# ============================================================================
FROM runtime-base-slim AS dev

LABEL mode="dev" \
      description="Development mode - includes development dependencies and tools"

# Install additional development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Install development dependencies
RUN pip install --no-cache-dir \
    black \
    flake8 \
    mypy \
    pytest \
    pytest-cov \
    ipython \
    ipdb

# Copy source code for development
COPY src/ /app/src/

# Default to bash for interactive development
ENTRYPOINT ["/bin/bash"]
CMD ["-i"]

# ============================================================================
# Stage 4: CLI, API, and MCP Modes With Embeddings
# ============================================================================
FROM runtime-base-embeddings AS app-embeddings

LABEL mode="app-embeddings" \
      description="Multi-purpose mode with vector database embeddings support"

# Expose API port (used when running in API mode)
EXPOSE 8000

# Health check for API mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0).raise_for_status()" || exit 1

# Environment variables for API mode
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_LOG_LEVEL=info \
    TERRAFORM_INGEST_MCP_AUTO_INGEST=true \
    TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP=false \
    TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS=24

# Default command for CLI mode (can be overridden for API or MCP modes)
# - CLI: terraform-ingest ingest config.yaml
# - API: python -m uvicorn terraform_ingest.api:app --host 0.0.0.0 --port 8000
# - MCP: terraform-ingest-mcp
ENTRYPOINT ["terraform-ingest"]
CMD ["--help"]

# ============================================================================
# Stage 5: CLI, API, and MCP Modes (Multi-Purpose - Slim)
# ============================================================================
FROM runtime-base-slim AS app

LABEL mode="app" \
      description="Multi-purpose mode supporting CLI, API, and MCP execution (lightweight)"

# Expose API port (used when running in API mode)
EXPOSE 8000

# Health check for API mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0).raise_for_status()" || exit 1

# Environment variables for API mode
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_LOG_LEVEL=info \
    TERRAFORM_INGEST_MCP_AUTO_INGEST=true \
    TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP=false \
    TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS=24

# Default command for CLI mode (can be overridden for API or MCP modes)
# - CLI: terraform-ingest ingest config.yaml
# - API: python -m uvicorn terraform_ingest.api:app --host 0.0.0.0 --port 8000
# - MCP: terraform-ingest-mcp
ENTRYPOINT ["terraform-ingest"]
CMD ["--help"]