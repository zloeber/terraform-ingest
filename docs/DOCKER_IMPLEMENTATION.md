# Multi-Stage Docker Implementation Summary

## Overview

I've created a comprehensive multi-stage Docker setup for `terraform-ingest` that supports three distinct execution modes, each optimized for different use cases.

## Files Created/Modified

### 1. **Dockerfile** (Main)
- **Location**: `/Dockerfile`
- **Stages**: 5 production + 1 development
- **Size**: ~148 lines with comprehensive comments

#### Stages:
1. **builder** - Compiles the application using `uv` package manager
2. **runtime-base** - Shared runtime environment with git and dependencies
3. **cli** - CLI mode for one-off ingestion tasks
4. **api** - FastAPI REST service with health checks
5. **mcp** - FastMCP server for AI agent integration
6. **dev** - Development mode with testing tools

### 2. **.dockerignore**
- **Location**: `/.dockerignore`
- Optimizes build context by excluding unnecessary files
- Reduces build time and image size

### 3. **docker-compose.yml**
- **Location**: `/docker-compose.yml`
- Provides ready-to-use service definitions for all modes
- Uses Docker Compose profiles for selective service startup
- Includes volume mounts and environment configuration

### 4. Documentation Files

#### **DOCKER_USAGE_GUIDE.md**
- **Location**: `/docs/DOCKER_USAGE_GUIDE.md`
- Comprehensive guide covering:
  - Quick start instructions
  - Detailed usage for each mode
  - API endpoint documentation
  - MCP configuration
  - Development workflows
  - Volume management
  - Network configuration
  - Resource limits
  - Troubleshooting
  - Best practices

#### **DOCKER_QUICK_REFERENCE.md**
- **Location**: `/docs/DOCKER_QUICK_REFERENCE.md`
- Condensed quick reference with:
  - Common commands
  - Options table
  - Environment variables
  - Docker Compose shortcuts
  - Health checks

### 5. **GitHub Actions Workflow**
- **Location**: `/.github/workflows/docker-build.yml`
- Automated multi-platform builds for:
  - All image targets
  - Multiple architectures (amd64, arm64)
  - Semantic versioning tags
  - Security scanning with Trivy
  - Push to GitHub Container Registry (GHCR)

## Key Features

### 1. CLI Mode
```bash
docker run terraform-ingest:cli ingest /app/config/config.yaml
```

**Use cases**:
- One-off ingestion tasks
- Batch processing
- CI/CD pipelines
- Scheduled jobs

**Features**:
- Full Click CLI support
- All CLI commands available
- Optional cleanup after ingestion
- Private repo SSH key support

### 2. API Mode
```bash
docker run -p 8000:8000 terraform-ingest:api
```

**Use cases**:
- REST API service
- Integration with other systems
- Long-running service
- Kubernetes deployments

**Features**:
- FastAPI with Swagger/ReDoc documentation
- Health check endpoints
- Background task support
- Configurable worker processes
- Graceful error handling

### 3. MCP Server Mode
```bash
docker run terraform-ingest:mcp
```

**Use cases**:
- AI agent integration
- Claude/LLM interaction
- Model Context Protocol servers
- Intelligent module discovery

**Features**:
- Stdio-based MCP protocol
- Auto-ingestion on startup
- Periodic refresh capability
- List repositories tool
- Search modules tool

### 4. Development Mode
```bash
docker-compose up terraform-ingest-dev
```

**Use cases**:
- Local development
- Testing
- Debugging
- Code formatting

**Features**:
- All dev dependencies installed
- Testing framework (pytest)
- Code quality tools (black, flake8, mypy)
- Interactive shell
- Live code mounting

## Build Optimization

### Layer Caching Strategy
1. **Stage 1 (builder)**: Installs `uv` and builds wheel
   - Cached separately from source changes
   - Rebuild only when dependencies change
   
2. **Stage 2 (runtime-base)**: Installs runtime dependencies
   - Minimal dependencies only
   - No build tools in final images
   
3. **Stages 3-5**: Thin layers using runtime-base
   - Entrypoint configuration only
   - Minimal additional overhead

### Size Optimization
- **Base image**: `python:3.13-slim` (~150MB)
- **Final CLI image**: ~300-400MB (estimate)
- **Final API image**: ~300-400MB (estimate)
- **Multi-stage prevents**: Build tools, intermediate files

## Docker Compose Profiles

Use profiles to selectively run services:

```bash
# Run CLI mode
docker-compose --profile cli run --rm terraform-ingest-cli ingest config.yaml

# Start API server
docker-compose --profile api up

# Start MCP server
docker-compose --profile mcp up

# Development environment
docker-compose --profile dev up
```

## Volume Management

### Essential Volumes
```yaml
volumes:
  - ./config.yaml:/app/config/config.yaml:ro    # Config (read-only)
  - ./output:/app/output                         # Results
  - ./repos:/app/repos                           # Cloned repos cache
```

### Optional Volumes
```yaml
volumes:
  - ~/.ssh:/root/.ssh:ro                         # SSH keys
  - ~/.gitconfig:/root/.gitconfig:ro             # Git config
  - ~/.netrc:/root/.netrc:ro                     # Git credentials
```

## Security Features

### Built-in
- **Health checks** in API mode
- **Read-only mounts** for configuration
- **SSH key isolation** via volume mounts
- **No build tools** in production images
- **Minimal base image** reduces attack surface

### CI/CD
- **GitHub Actions workflow** for automated builds
- **Trivy security scanning** on push
- **Multi-platform builds** (amd64, arm64)
- **SARIF format** integration with GitHub Security

## Environment Configuration

### API Mode
```bash
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_LOG_LEVEL=info
UVICORN_WORKERS=4
```

### MCP Mode
```bash
TERRAFORM_INGEST_MCP_AUTO_INGEST=true
TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP=false
TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS=24
```

### All Modes
```bash
TERRAFORM_INGEST_CONFIG=/app/config/config.yaml
PYTHONUNBUFFERED=1
```

## GitHub Actions Workflow Features

The `.github/workflows/docker-build.yml` provides:

1. **Build Matrix**: Separate jobs for each target (cli, api, mcp, dev)
2. **Multi-platform**: Linux amd64 and arm64 support
3. **Semantic Versioning**: Automatic tag management
4. **Container Registry**: Push to GitHub Container Registry (GHCR)
5. **Cache**: GitHub Actions cache for faster builds
6. **Security**: Trivy vulnerability scanning
7. **Testing**: Basic functionality tests for each image
8. **Conditional**: Only pushes on main/develop or tags

## Usage Examples

### Quick Start

**CLI Mode - Single Ingestion**:
```bash
docker run --rm \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:cli ingest /app/config/config.yaml --cleanup
```

**API Mode - Running Service**:
```bash
docker run -d \
  --name terraform-api \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:api
```

**MCP Mode - AI Integration**:
```bash
docker run -d \
  --name terraform-mcp \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  -e TERRAFORM_INGEST_MCP_AUTO_INGEST=true \
  terraform-ingest:mcp
```

### With Docker Compose

```bash
# Build all images
docker-compose build

# Run CLI
docker-compose run --rm terraform-ingest-cli ingest /app/config/config.yaml

# Start API
docker-compose up -d terraform-ingest-api

# View logs
docker-compose logs -f terraform-ingest-api

# Stop services
docker-compose down
```

## Building Locally

```bash
# Build individual images
docker build -t terraform-ingest:cli --target cli .
docker build -t terraform-ingest:api --target api .
docker build -t terraform-ingest:mcp --target mcp .

# Or with docker-compose
docker-compose build
```

## Testing Images

```bash
# Test CLI
docker run --rm terraform-ingest:cli --help

# Test API (check it starts)
docker run --rm -p 8000:8000 terraform-ingest:api &
sleep 2
curl http://localhost:8000/health

# Test MCP (basic startup)
timeout 5 docker run --rm terraform-ingest:mcp || true
```

## Production Deployment

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: terraform-ingest-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: terraform-ingest-api
  template:
    metadata:
      labels:
        app: terraform-ingest-api
    spec:
      containers:
      - name: api
        image: ghcr.io/zloeber/terraform-ingest:api-latest
        ports:
        - containerPort: 8000
        env:
        - name: UVICORN_WORKERS
          value: "4"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: output
          mountPath: /app/output
        - name: repos
          mountPath: /app/repos
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: terraform-ingest-config
      - name: output
        persistentVolumeClaim:
          claimName: terraform-output
      - name: repos
        persistentVolumeClaim:
          claimName: terraform-repos
```

## Next Steps

1. **Build the images**: `docker build -t terraform-ingest:cli --target cli .`
2. **Test locally**: `docker run --rm terraform-ingest:cli --help`
3. **Set up Docker Compose**: `docker-compose build && docker-compose up terraform-ingest-api`
4. **Push to registry**: Configured in `.github/workflows/docker-build.yml`
5. **Deploy to production**: Use Kubernetes manifests or Docker Swarm

## Benefits

✅ **Flexible**: One Dockerfile for all deployment scenarios
✅ **Optimized**: Multi-stage builds keep images small
✅ **Documented**: Comprehensive guides and quick reference
✅ **Tested**: GitHub Actions CI/CD with security scanning
✅ **Production-ready**: Health checks, logging, resource management
✅ **Developer-friendly**: Dev mode with testing tools
✅ **Scalable**: API mode supports multiple workers
✅ **Secure**: No build tools in production, minimal base image
✅ **Portable**: Multi-platform (amd64, arm64) support
✅ **Easy to use**: Docker Compose profiles for simple startup

## Troubleshooting

If you encounter issues:

1. **Check logs**: `docker logs <container_name>`
2. **Rebuild without cache**: `docker build --no-cache -t terraform-ingest:cli --target cli .`
3. **Test basic functionality**: `docker run --rm terraform-ingest:cli --help`
4. **Review documentation**: See `docs/DOCKER_USAGE_GUIDE.md`
5. **Enable debug logging**: Set `UVICORN_LOG_LEVEL=debug` for API mode

## Additional Resources

- **Full Guide**: `docs/DOCKER_USAGE_GUIDE.md`
- **Quick Reference**: `docs/DOCKER_QUICK_REFERENCE.md`
- **GitHub Actions**: `.github/workflows/docker-build.yml`
- **Docker Compose**: `docker-compose.yml`
- **Build File**: `Dockerfile`
- **Build Ignore**: `.dockerignore`
