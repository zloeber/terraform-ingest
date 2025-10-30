# 🐳 Docker Guide - terraform-ingest

> Multi-stage Docker images for CLI, API, and MCP server modes

## 🚀 Quick Start

### 1. Build the Images

```bash
# Build all images
docker-compose build

# Or build individual images
docker build -t terraform-ingest:cli --target cli .
docker build -t terraform-ingest:api --target api .
docker build -t terraform-ingest:mcp --target mcp .
```

### 2. Choose Your Mode

#### 🖥️ **CLI Mode** (One-off Tasks)
```bash
docker run --rm \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:cli ingest /app/config/config.yaml
```

#### 🌐 **API Mode** (REST Service)
```bash
docker run -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:api
```

Visit: `http://localhost:8000/docs`

#### 🤖 **MCP Mode** (AI Agent)
```bash
docker run \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:mcp
```

#### 👨‍💻 **Dev Mode** (Development)
```bash
docker-compose up -d terraform-ingest-dev
docker-compose exec terraform-ingest-dev bash
```

### 3. Using Docker Compose

```bash
# Run CLI mode
docker-compose run --rm terraform-ingest-cli ingest /app/config/config.yaml

# Start API service
docker-compose up -d terraform-ingest-api

# View logs
docker-compose logs -f terraform-ingest-api

# Stop all services
docker-compose down
```

## 📖 Documentation

- **[Full Guide](docker_guide.md)** - Comprehensive documentation
- **[Quick Reference](docker_quick_ref.md)** - Common commands
- **[Implementation Details](docker_complete.md)** - How it works
- **[Checklist](DOCKER_CHECKLIST.md)** - Verification checklist

## 🎯 Features

### Multi-Stage Builds
- **builder** - Compiles application
- **runtime-base** - Shared runtime
- **cli** - CLI mode
- **api** - REST API service
- **mcp** - MCP server
- **dev** - Development tools

### Security
✅ Minimal base image (python:3.13-slim)  
✅ No build tools in production  
✅ Read-only config mounts  
✅ Health checks  
✅ Trivy security scanning  

### Developer Experience
✅ Docker Compose profiles  
✅ Volume mounts for development  
✅ Hot reloading support  
✅ Full testing environment  

### Production Ready
✅ Health check endpoints  
✅ Graceful error handling  
✅ Configurable logging  
✅ Multi-worker support  
✅ Resource limits  

## 📋 Configuration

Create a `config.yaml`:

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc
    branches: ["main"]
    recursive: true

output_dir: ./output
clone_dir: ./repos

mcp:
  auto_ingest: true
  ingest_on_startup: false
  refresh_interval_hours: 24
```

## 🔧 Common Tasks

### Run Ingestion
```bash
docker-compose run --rm terraform-ingest-cli ingest /app/config/config.yaml
```

### Start API
```bash
docker-compose up -d terraform-ingest-api
curl http://localhost:8000/health
```

### View Logs
```bash
docker-compose logs -f terraform-ingest-api
```

### Stop Services
```bash
docker-compose down
```

### Development
```bash
docker-compose up -d terraform-ingest-dev
docker-compose exec terraform-ingest-dev bash
pytest tests/
```

## 📦 Volume Mounts

| Mount | Purpose | Required |
|-------|---------|----------|
| `/app/config/config.yaml` | Config file | Yes |
| `/app/output` | Results | Yes |
| `/app/repos` | Repo cache | Yes |
| `~/.ssh` | SSH keys | Private repos |
| `~/.gitconfig` | Git config | Optional |

## 🌍 Environment Variables

**API Mode**:
- `UVICORN_PORT` (default: 8000)
- `UVICORN_LOG_LEVEL` (default: info)
- `UVICORN_WORKERS` (default: 1)

**MCP Mode**:
- `TERRAFORM_INGEST_MCP_AUTO_INGEST` (default: true)
- `TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP` (default: false)
- `TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS` (default: 24)

**All Modes**:
- `TERRAFORM_INGEST_CONFIG` (default: /app/config/config.yaml)

## 🐛 Troubleshooting

### Container won't start
```bash
docker logs <container_name>
```

### Permission denied
```bash
chmod 600 ~/.ssh/id_rsa
chmod 700 ~/.ssh
```

### Port already in use
```bash
docker run -p 8001:8000 terraform-ingest:api  # Use different port
```

### See logs
```bash
docker-compose logs -f
```

## 📚 More Info

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [terraform-ingest README](README.md)

## 💡 Tips

**Use profiles for selective startup:**
```bash
docker-compose --profile api up
docker-compose --profile mcp up
docker-compose --profile cli run --rm terraform-ingest-cli
```

**Share SSH credentials with container:**
```bash
docker run -v ~/.ssh:/root/.ssh:ro terraform-ingest:cli
```

**Run with custom config:**
```bash
docker run -v /path/to/custom.yaml:/app/config/config.yaml terraform-ingest:cli
```

**Monitor container health:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

**Ready to use?** Start with the Quick Start section above! 🎉

For detailed information, see [docker_guide.md](docker_guide.md)
