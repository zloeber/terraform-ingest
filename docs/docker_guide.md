# Docker Usage Guide for terraform-ingest

This guide explains how to use the multi-stage Docker image for `terraform-ingest` in three different execution modes: CLI, API, and MCP Server.

## Overview

The Dockerfile provides multiple build targets for different use cases:

- **cli**: Command-line interface for one-off ingestion tasks
- **api**: FastAPI REST service for HTTP-based access
- **mcp**: FastMCP server for AI agent integration
- **dev**: Development mode with testing and debugging tools

## Quick Start

### Building the Images

Build all images:
```bash
docker build -t terraform-ingest:cli --target cli .
docker build -t terraform-ingest:api --target api .
docker build -t terraform-ingest:mcp --target mcp .
```

Or use Docker Compose:
```bash
docker-compose build
```

## Mode 1: CLI Mode

Use the CLI mode for one-off terraform module ingestion tasks.

### Basic Usage

Run ingestion from a config file:
```bash
docker run -v /path/to/config.yaml:/app/config/config.yaml \
  -v /path/to/output:/app/output \
  -v /path/to/repos:/app/repos \
  terraform-ingest:cli ingest /app/config/config.yaml
```

### With Docker Compose

```bash
docker-compose run --rm terraform-ingest-cli ingest /app/config/config.yaml
```

### Available CLI Commands

```bash
# Show help
docker run terraform-ingest:cli --help

# Ingest from configuration file
docker run terraform-ingest:cli ingest /app/config/config.yaml

# Ingest with custom output directory
docker run terraform-ingest:cli ingest /app/config/config.yaml -o /app/output -c /app/repos

# Ingest with cleanup (remove cloned repos after)
docker run terraform-ingest:cli ingest /app/config/config.yaml --cleanup

# Analyze a single repository
docker run terraform-ingest:cli analyze https://github.com/user/terraform-module --recursive
```

### Private Repository Access

For private repositories, mount your SSH key:
```bash
docker run -v ~/.ssh:/root/.ssh:ro \
  -v /path/to/config.yaml:/app/config/config.yaml \
  -v /path/to/output:/app/output \
  terraform-ingest:cli ingest /app/config/config.yaml
```

### Environment Variables

```bash
docker run -e TERRAFORM_INGEST_CONFIG=/app/config/config.yaml \
  terraform-ingest:cli ingest /app/config/config.yaml
```

## Mode 2: API Mode

Use the API mode to run terraform-ingest as a REST service.

### Starting the API Service

```bash
docker run -p 8000:8000 \
  -v /path/to/config.yaml:/app/config/config.yaml \
  -v /path/to/output:/app/output \
  -v /path/to/repos:/app/repos \
  terraform-ingest:api
```

### With Docker Compose

```bash
docker-compose up terraform-ingest-api
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### API Documentation
```
http://localhost:8000/docs  # Interactive Swagger UI
http://localhost:8000/redoc  # ReDoc API documentation
```

#### Ingest Repositories
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "repositories": [
      {
        "url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
        "branches": ["main"],
        "recursive": true
      }
    ],
    "output_dir": "/app/output",
    "clone_dir": "/app/repos"
  }'
```

#### Analyze Single Repository
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/terraform-aws-modules/terraform-aws-vpc",
    "branches": ["main"],
    "include_tags": true,
    "max_tags": 10,
    "path": "."
  }'
```

### Configuration

#### Uvicorn Configuration

Control Uvicorn server behavior via environment variables:

```bash
docker run -e UVICORN_HOST=0.0.0.0 \
  -e UVICORN_PORT=8000 \
  -e UVICORN_LOG_LEVEL=info \
  -e UVICORN_WORKERS=4 \
  -p 8000:8000 \
  terraform-ingest:api
```

#### Available Options

- `UVICORN_HOST`: Server host (default: 0.0.0.0)
- `UVICORN_PORT`: Server port (default: 8000)
- `UVICORN_LOG_LEVEL`: Logging level - critical, error, warning, info, debug, trace (default: info)
- `UVICORN_WORKERS`: Number of worker processes (default: 1)
- `UVICORN_RELOAD`: Enable auto-reload on code changes (default: false)

#### Private Repository Access

```bash
docker run -p 8000:8000 \
  -v ~/.ssh:/root/.ssh:ro \
  -v /path/to/config.yaml:/app/config/config.yaml \
  -v /path/to/output:/app/output \
  terraform-ingest:api
```

### Docker Compose Example

```bash
# Start API service
docker-compose up terraform-ingest-api

# In another terminal, make requests
curl http://localhost:8000/health

# Stop service
docker-compose down terraform-ingest-api
```

## Mode 3: MCP Server Mode

Use the MCP mode to expose terraform modules to AI agents via the Model Context Protocol.

### Starting the MCP Server

```bash
docker run \
  -v /path/to/config.yaml:/app/config/config.yaml \
  -v /path/to/output:/app/output \
  -v /path/to/repos:/app/repos \
  terraform-ingest:mcp
```

### With Docker Compose

```bash
docker-compose up terraform-ingest-mcp
```

### MCP Configuration

Configure MCP auto-ingestion via environment variables:

```bash
docker run \
  -e TERRAFORM_INGEST_CONFIG=/app/config/config.yaml \
  -e TERRAFORM_INGEST_MCP_AUTO_INGEST=true \
  -e TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP=false \
  -e TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS=24 \
  terraform-ingest:mcp
```

#### Available MCP Configuration Options

- `TERRAFORM_INGEST_MCP_AUTO_INGEST`: Enable automatic ingestion (default: true)
- `TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP`: Run ingestion when server starts (default: false)
- `TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS`: Hours between refresh cycles (default: 24)

### MCP Server Tools

The MCP server exposes the following tools for AI agents:

- **list_repositories**: List all discovered repositories and their metadata
- **search_modules**: Search for terraform modules by query, provider, or repository

### Usage with AI Agents

Example configuration for Claude or similar AI models:

```json
{
  "terraform-ingest-mcp": {
    "command": "docker",
    "args": ["run", "--rm", "-v", "/path/to/output:/app/output", "terraform-ingest:mcp"]
  }
}
```

Or with Docker Compose:

```json
{
  "terraform-ingest-mcp": {
    "command": "docker-compose",
    "args": ["exec", "terraform-ingest-mcp"]
  }
}
```

### Private Repository Access

```bash
docker run \
  -v ~/.ssh:/root/.ssh:ro \
  -v /path/to/config.yaml:/app/config/config.yaml \
  -v /path/to/output:/app/output \
  terraform-ingest:mcp
```

## Development Mode

Development mode includes testing tools and allows live code editing.

### Starting Development Container

```bash
docker-compose up -d terraform-ingest-dev
docker-compose exec terraform-ingest-dev bash
```

### Running Tests

```bash
docker run --rm \
  -v $(pwd):/app \
  terraform-ingest:dev \
  pytest tests/
```

### Code Formatting and Linting

```bash
docker run --rm \
  -v $(pwd):/app \
  terraform-ingest:dev \
  black src/

docker run --rm \
  -v $(pwd):/app \
  terraform-ingest:dev \
  flake8 src/

docker run --rm \
  -v $(pwd):/app \
  terraform-ingest:dev \
  mypy src/
```

## Configuration File

Create a `config.yaml` file for ingestion:

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc
    branches: ["main"]
    recursive: true
    
  - url: https://github.com/terraform-aws-modules/terraform-aws-security-group
    branches: ["main", "v5.0"]
    include_tags: true
    max_tags: 5

output_dir: ./output
clone_dir: ./repos

mcp:
  auto_ingest: true
  ingest_on_startup: false
  refresh_interval_hours: 24
  config_file: /app/config/config.yaml
```

## Volume Mounts

### Essential Volumes

```bash
docker run \
  -v /path/to/config.yaml:/app/config/config.yaml:ro \  # Read-only config
  -v /path/to/output:/app/output \                       # Output directory
  -v /path/to/repos:/app/repos \                         # Cloned repos cache
  terraform-ingest:cli
```

### Optional Volume Mounts

```bash
docker run \
  -v ~/.ssh:/root/.ssh:ro \                              # SSH keys for private repos
  -v ~/.gitconfig:/root/.gitconfig:ro \                  # Git configuration
  -v ~/.netrc:/root/.netrc:ro \                          # Git credentials
  terraform-ingest:cli
```

## Networking

### Exposing the API Service

```bash
docker run -p 8000:8000 \
  -p 8001:8001 \
  terraform-ingest:api
```

### Custom Network

```bash
docker network create terraform-ingest-net

docker run --network terraform-ingest-net \
  --name terraform-api \
  -p 8000:8000 \
  terraform-ingest:api

docker run --network terraform-ingest-net \
  --name terraform-client \
  terraform-ingest:cli
```

## Resource Management

### CPU and Memory Limits

```bash
docker run --cpus="2" --memory="4g" \
  terraform-ingest:api

# Or with docker-compose
services:
  terraform-ingest-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Logging

### View Logs

```bash
# Docker CLI
docker logs <container_name> -f

# Docker Compose
docker-compose logs -f terraform-ingest-api
```

### Log Levels

Control logging verbosity:

```bash
# API mode
docker run -e UVICORN_LOG_LEVEL=debug terraform-ingest:api

# Development
docker run -e PYTHONUNBUFFERED=1 terraform-ingest:dev
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs <container_name>

# Run interactively
docker run -it --entrypoint /bin/bash terraform-ingest:api
```

### Permission Denied Errors

If you see "Permission denied" with SSH key mounts:

```bash
# Ensure SSH key has correct permissions
chmod 600 ~/.ssh/id_rsa
chmod 700 ~/.ssh

# Or use --user flag
docker run --user 0:0 \
  -v ~/.ssh:/root/.ssh:ro \
  terraform-ingest:cli
```

### Git Clone Failures

```bash
# Enable SSH key forwarding
docker run \
  -v ~/.ssh:/root/.ssh:ro \
  -v ~/.ssh/known_hosts:/root/.ssh/known_hosts:ro \
  terraform-ingest:cli
```

## Performance Optimization

### Build Cache

```bash
# Use --cache-from to speed up builds
docker build --cache-from terraform-ingest:latest -t terraform-ingest:cli --target cli .
```

### Multi-platform Builds

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 -t terraform-ingest:cli --target cli .
```

### Layer Caching

The Dockerfile is optimized for layer caching:
- Dependencies are cached separately from source code
- Build dependencies are not included in final images
- Development dependencies are only in dev mode

## Examples

### Example 1: One-time Ingestion

```bash
docker run --rm \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:cli ingest /app/config/config.yaml --cleanup
```

### Example 2: Running API in Production

```bash
docker run -d \
  --name terraform-ingest-api \
  --restart unless-stopped \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/repos:/app/repos \
  -e UVICORN_WORKERS=4 \
  terraform-ingest:api
```

### Example 3: MCP Server with Auto-ingestion

```bash
docker run -d \
  --name terraform-ingest-mcp \
  --restart unless-stopped \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  -e TERRAFORM_INGEST_MCP_AUTO_INGEST=true \
  -e TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP=true \
  terraform-ingest:mcp
```

### Example 4: Development Setup

```bash
docker-compose -f docker-compose.yml up -d terraform-ingest-dev

# Work on code
docker-compose exec terraform-ingest-dev bash

# Run tests
docker-compose exec terraform-ingest-dev pytest tests/

# Code formatting
docker-compose exec terraform-ingest-dev black src/
```

## Best Practices

1. **Use specific image tags** instead of `latest` in production
2. **Mount configuration files as read-only** (`ro` flag)
3. **Use named volumes** for persistent data
4. **Set resource limits** to prevent resource exhaustion
5. **Enable restart policies** for production services
6. **Use health checks** to monitor service status
7. **Provide SSH credentials** for private repository access
8. **Use environment variables** for configuration instead of hardcoding
9. **Separate concerns** - use different containers for different tasks
10. **Keep images small** - use minimal base image (python:3.13-slim)
