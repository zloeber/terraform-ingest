# Multi-stage Dockerfile for terraform-ingest
# Supports three execution modes:
# 1. CLI mode: terraform-ingest ingest config.yaml
# 2. API mode: FastAPI REST service on port 8000
# 3. MCP mode: FastMCP server for AI agent access

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.13-slim AS builder

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

# Build the application with uv
RUN if [ -n "$VERSION" ]; then \
        SETUPTOOLS_SCM_PRETEND_VERSION=$VERSION; \
    fi && \
    uv sync --frozen && \
    uv build --sdist --wheel

# ============================================================================
# Stage 2: Runtime Base
# ============================================================================
FROM python:3.13-slim AS runtime-base

WORKDIR /app

# Install runtime dependencies (git for cloning repos, ca-certificates for HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the application and its dependencies
COPY --from=builder /build/dist /tmp/dist
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
# Stage 3: CLI Mode
# ============================================================================
FROM runtime-base AS cli

LABEL mode="cli" \
      description="CLI mode - run terraform-ingest commands"

# Default command for CLI mode
ENTRYPOINT ["terraform-ingest"]
CMD ["--help"]

# ============================================================================
# Stage 4: API Mode
# ============================================================================
FROM runtime-base AS api

LABEL mode="api" \
      description="API mode - FastAPI REST service on port 8000"

# Expose API port
EXPOSE 8000

# Health check for API
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0).raise_for_status()" || exit 1

# Environment variables for API
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_LOG_LEVEL=info

# Default command for API mode
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["terraform_ingest.api:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Stage 5: MCP Server Mode
# ============================================================================
FROM runtime-base AS mcp

LABEL mode="mcp" \
      description="MCP mode - FastMCP server for AI agent access"

# MCP typically uses stdio for communication
# Health check is minimal AS MCP runs in stdio mode
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=2 \
    CMD ps aux | grep -q "terraform-ingest-mcp" || exit 1

# Environment variables for MCP
ENV TERRAFORM_INGEST_MCP_AUTO_INGEST=true \
    TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP=false \
    TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS=24

# Default command for MCP mode
ENTRYPOINT ["terraform-ingest-mcp"]
CMD []

# ============================================================================
# Stage 6: Development Mode (optional)
# ============================================================================
FROM runtime-base AS dev

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
