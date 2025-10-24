# Docker Quick Reference for terraform-ingest

## Build Images

```bash
# Build individual modes
docker build -t terraform-ingest:cli --target cli .
docker build -t terraform-ingest:api --target api .
docker build -t terraform-ingest:mcp --target mcp .

# Build with docker-compose
docker-compose build
```

## CLI Mode (One-off Tasks)

```bash
# Run ingestion
docker run -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:cli ingest /app/config/config.yaml

# With cleanup
docker run -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:cli ingest /app/config/config.yaml --cleanup

# Analyze single repo
docker run terraform-ingest:cli analyze https://github.com/user/repo
```

## API Mode (REST Service)

```bash
# Start API server
docker run -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:api

# Or with docker-compose
docker-compose up terraform-ingest-api

# Test health
curl http://localhost:8000/health

# View API docs
curl http://localhost:8000/docs
```

## MCP Mode (AI Agent Integration)

```bash
# Start MCP server
docker run \
  -v $(pwd)/config.yaml:/app/config/config.yaml \
  -v $(pwd)/output:/app/output \
  terraform-ingest:mcp

# With docker-compose
docker-compose up terraform-ingest-mcp

# Configure auto-ingestion
docker run \
  -e TERRAFORM_INGEST_MCP_AUTO_INGEST=true \
  -e TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP=true \
  terraform-ingest:mcp
```

## Development Mode

```bash
# Start development container
docker-compose up -d terraform-ingest-dev
docker-compose exec terraform-ingest-dev bash

# Run tests
docker run terraform-ingest:dev pytest tests/

# Format code
docker run -v $(pwd):/app terraform-ingest:dev black src/
```

## Common Options

| Option | Usage | Example |
|--------|-------|---------|
| Config mount | `-v config.yaml:/app/config/config.yaml` | ✓ |
| Output mount | `-v output:/app/output` | ✓ |
| SSH keys | `-v ~/.ssh:/root/.ssh:ro` | Private repos |
| API port | `-p 8000:8000` | API mode |
| Environment vars | `-e VAR=value` | Configuration |
| Interactive | `-it` | Development |
| Daemonized | `-d` | Background |
| Remove on exit | `--rm` | Cleanup |

## Environment Variables

### API Mode
- `UVICORN_HOST` - Server host (default: 0.0.0.0)
- `UVICORN_PORT` - Server port (default: 8000)
- `UVICORN_LOG_LEVEL` - Logging level (default: info)
- `UVICORN_WORKERS` - Worker processes (default: 1)

### MCP Mode
- `TERRAFORM_INGEST_MCP_AUTO_INGEST` - Enable auto-ingest (default: true)
- `TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP` - Ingest on startup (default: false)
- `TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS` - Refresh interval (default: 24)

### All Modes
- `TERRAFORM_INGEST_CONFIG` - Config file path (default: /app/config/config.yaml)
- `PYTHONUNBUFFERED` - Unbuffered output (default: 1)

## Docker Compose Profiles

```bash
# Run by profile
docker-compose --profile cli up
docker-compose --profile api up
docker-compose --profile mcp up
docker-compose --profile dev up

# Run specific service
docker-compose up terraform-ingest-api
```

## Health Checks

```bash
# API health
curl http://localhost:8000/health

# Check container health
docker ps --filter "name=terraform-ingest" --format "{{.Names}}\t{{.Status}}"
```

## Logs

```bash
# View logs
docker logs -f <container_name>

# With docker-compose
docker-compose logs -f terraform-ingest-api

# View specific lines
docker logs --tail 100 <container_name>
```

## Cleanup

```bash
# Remove container
docker rm <container_name>

# Remove image
docker rmi terraform-ingest:cli

# Prune unused
docker system prune -a

# Docker compose cleanup
docker-compose down -v
```

## Docker Compose Shortcuts

```bash
# Build all images
docker-compose build

# Run CLI in container
docker-compose run --rm terraform-ingest-cli ingest /app/config/config.yaml

# View logs
docker-compose logs -f

# Stop all
docker-compose down

# Stop specific service
docker-compose stop terraform-ingest-api

# Restart service
docker-compose restart terraform-ingest-api
```
