# Docker Architecture Diagram & Overview

## 🏗️ Multi-Stage Build Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Dockerfile                              │
│                    (148 lines, 6 stages)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐   ┌──────────┐
        │ Builder  │    │ Runtime  │   │   Dev    │
        │ Stage 1  │───▶│  Base    │◀──│ Stage 6  │
        │          │    │ Stage 2  │   │          │
        │ - uv     │    │          │   │ - pytest │
        │ - build  │    │ - git    │   │ - black  │
        │ - wheel  │    │ - deps   │   │ - flake8 │
        └──────────┘    └──────────┘   │ - mypy   │
                              │          └──────────┘
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
            ┌────────┐   ┌────────┐   ┌────────┐
            │  CLI   │   │  API   │   │  MCP   │
            │ Stage  │   │ Stage  │   │ Stage  │
            │   3    │   │   4    │   │   5    │
            │        │   │        │   │        │
            │ Entry: │   │ Entry: │   │ Entry: │
            │  CLI   │   │Uvicorn│   │ MCP    │
            │ tool   │   │ REST   │   │ Server │
            │        │   │        │   │        │
            └────────┘   └────────┘   └────────┘
                │             │             │
                ▼             ▼             ▼
        terraform-ingest   terraform-ingest  terraform-ingest
           :cli             :api              :mcp
        (~350MB)         (~350MB)           (~350MB)
```

## 📦 Image Specification

### Base Layer (All Images)
```
Python 3.13-slim
├── apt dependencies
│   ├── git
│   └── ca-certificates
├── Python packages (via pip)
│   ├── click
│   ├── fastapi
│   ├── fastmcp
│   ├── gitpython
│   ├── httpx
│   ├── loguru
│   ├── pydantic
│   ├── python-hcl2
│   ├── pyyaml
│   └── uvicorn
└── Application (from wheel)
    └── terraform_ingest
```

### CLI Mode
```
runtime-base
├── Entry: terraform-ingest command
├── Features:
│   ├── Full Click CLI
│   ├── Ingest command
│   ├── Analyze command
│   └── Help system
└── Use: Docker run with command args
```

### API Mode
```
runtime-base
├── Entry: uvicorn terraform_ingest.api:app
├── Features:
│   ├── FastAPI REST service
│   ├── Swagger UI (/docs)
│   ├── ReDoc (/redoc)
│   ├── Health check (/health)
│   ├── Ingest endpoint (/ingest)
│   └── Analyze endpoint (/analyze)
├── Port: 8000
└── Use: Long-running service
```

### MCP Mode
```
runtime-base
├── Entry: terraform-ingest-mcp
├── Features:
│   ├── FastMCP server
│   ├── Stdio protocol
│   ├── Auto-ingestion
│   ├── Periodic refresh
│   ├── list_repositories tool
│   └── search_modules tool
└── Use: AI agent integration
```

### Dev Mode
```
runtime-base
├── pytest (testing)
├── black (formatting)
├── flake8 (linting)
├── mypy (type checking)
├── ipython (interactive)
├── ipdb (debugging)
└── Entry: /bin/bash (interactive)
```

## 🚀 Execution Flow by Mode

### CLI Mode Flow
```
docker run terraform-ingest:cli ingest config.yaml
         │
         ├─► Parse CLI arguments
         │
         ├─► Load YAML config
         │
         ├─► Ingest repositories
         │   ├─► Clone repos
         │   ├─► Parse Terraform
         │   └─► Generate JSON
         │
         └─► Exit (0 = success)
```

### API Mode Flow
```
docker run -p 8000:8000 terraform-ingest:api
         │
         ├─► Start Uvicorn server
         │
         ├─► Listen on 0.0.0.0:8000
         │
         ├─► Handle requests
         │   ├─► GET /health → OK
         │   ├─► GET /docs → Swagger UI
         │   ├─► POST /ingest → Process
         │   └─► POST /analyze → Process
         │
         └─► Run indefinitely
             (until container stops)
```

### MCP Mode Flow
```
docker run terraform-ingest:mcp
         │
         ├─► Check config
         │
         ├─► Optional: Run ingestion
         │
         ├─► Start MCP server
         │
         ├─► Listen on stdio
         │
         ├─► Handle MCP requests
         │   ├─► list_repositories
         │   └─► search_modules
         │
         └─► Run indefinitely
             (until container stops)
```

## 📊 Volume Mount Architecture

```
Host System                          Container
─────────────                        ──────────

~/.ssh/
├── id_rsa      ────────────────────► /root/.ssh/id_rsa (ro)
├── id_rsa.pub  ────────────────────► /root/.ssh/id_rsa.pub (ro)
└── known_hosts ────────────────────► /root/.ssh/known_hosts (ro)

$(pwd)/config.yaml ────────────────► /app/config/config.yaml (ro)

$(pwd)/output/
├── module1.json ◄────────────────── /app/output/module1.json
└── module2.json ◄────────────────── /app/output/module2.json

$(pwd)/repos/
├── repo1/ ◄────────────────────── /app/repos/repo1/
└── repo2/ ◄────────────────────── /app/repos/repo2/

.venv/                ┌──────────────► /app/.venv/ (dev only)
```

## 🔄 CI/CD Pipeline Flow

```
GitHub Push/Tag/PR
       │
       ▼
Docker Build Job (docker-build.yml)
       │
       ├─► Setup Docker Buildx
       │
       ├─► Extract metadata
       │   ├─► Branch tags
       │   ├─► Semantic version tags
       │   └─► SHA tags
       │
       ├─► Build matrix (4 targets)
       │   ├─► cli
       │   ├─► api
       │   ├─► mcp
       │   └─► dev
       │
       ├─► Multi-platform build
       │   ├─► linux/amd64
       │   └─► linux/arm64
       │
       ├─► Push to GHCR
       │
       ├─► Test stage (if PR)
       │   ├─► CLI: --help, --version
       │   ├─► API: uvicorn check
       │   └─► MCP: startup test
       │
       └─► Security scan (if push)
           ├─► Trivy scan
           └─► Upload SARIF
```

## 🔐 Security Model

```
Production Image Security
───────────────────────────────

✓ Minimal Base Image (python:3.13-slim)
  └─ Only essential packages
     ├─ git (for cloning)
     └─ ca-certificates (for HTTPS)

✓ Multi-Stage Build
  └─ Build tools (uv, gcc) not in final image
     ├─ Smaller image size
     ├─ Reduced attack surface
     └─ Faster deployment

✓ No Build Tools in Runtime
  └─ gcc, make, etc. excluded
     └─ Prevents runtime compilation

✓ Read-Only Config Mounts
  └─ Configuration cannot be modified
     └─ Immutable setup

✓ SSH Key Isolation
  └─ Keys in volumes, not in image
     ├─ No credentials in image
     └─ Easy credential rotation

✓ Health Checks
  └─ Automated monitoring
     ├─ API: HTTP health endpoint
     └─ MCP: Process monitoring

✓ Security Scanning
  └─ Trivy in CI/CD
     ├─ Vulnerability detection
     └─ Automatic SARIF reports
```

## 🎯 Mode Selection Decision Tree

```
What do you want to do?
│
├─ Run ingestion once?
│  └─► CLI Mode
│      docker run terraform-ingest:cli ingest config.yaml
│
├─ Expose REST API?
│  └─► API Mode
│      docker run -p 8000:8000 terraform-ingest:api
│
├─ Integrate with AI agents?
│  └─► MCP Mode
│      docker run terraform-ingest:mcp
│
└─ Develop & test code?
   └─► Dev Mode
       docker-compose up terraform-ingest-dev
       docker-compose exec terraform-ingest-dev bash
```

## Environment Variable Hierarchy

```
Application Configuration
──────────────────────────

Docker Env Vars
     │
     ├─ TERRAFORM_INGEST_CONFIG
     │  └─ Default: /app/config/config.yaml
     │
     ├─ API Mode Only
     │  ├─ UVICORN_HOST (0.0.0.0)
     │  ├─ UVICORN_PORT (8000)
     │  ├─ UVICORN_LOG_LEVEL (info)
     │  └─ UVICORN_WORKERS (1)
     │
     └─ MCP Mode Only
        ├─ TERRAFORM_INGEST_MCP_AUTO_INGEST (true)
        ├─ TERRAFORM_INGEST_MCP_INGEST_ON_STARTUP (false)
        └─ TERRAFORM_INGEST_MCP_REFRESH_INTERVAL_HOURS (24)

Config File (YAML)
     │
     ├─ repositories[]
     ├─ output_dir
     ├─ clone_dir
     └─ mcp:
        ├─ auto_ingest
        ├─ ingest_on_startup
        └─ refresh_interval_hours
```

## 🗂️ Project Structure

```
terraform-ingest/
├── Dockerfile                          ← Build definition
├── .dockerignore                       ← Build optimizations
├── docker-compose.yml                  ← Service definitions
│
├── docker.md                           ← Quick start guide
│
├── docs/
│   ├── docker_complete.md              ← This summary
│   ├── docker_guide.md           ← Full guide (600+ lines)
│   ├── docker_quick_ref.md       ← Quick commands
│   ├── docker_complete.md        ← Technical details
│   └── DOCKER_CHECKLIST.md             ← Verification
│
├── .github/workflows/
│   └── docker-build.yml                ← CI/CD pipeline
│
├── src/terraform_ingest/
│   ├── cli.py                          ← CLI mode
│   ├── api.py                          ← API mode
│   ├── mcp_service.py                  ← MCP mode
│   ├── ingest.py                       ← Core logic
│   └── ...
│
├── pyproject.toml                      ← Python project config
└── config.yaml                         ← Example config
```

## ✨ Quick Reference Matrix

| Aspect | CLI | API | MCP | Dev |
|--------|-----|-----|-----|-----|
| **Image** | `terraform-ingest:cli` | `terraform-ingest:api` | `terraform-ingest:mcp` | `terraform-ingest:dev` |
| **Entry** | terraform-ingest | uvicorn | terraform-ingest-mcp | /bin/bash |
| **Port** | - | 8000 | stdio | - |
| **Duration** | Short-lived | Long-running | Long-running | Interactive |
| **Use** | Batch | Service | AI | Development |
| **Command** | `docker run` | `docker run -p` | `docker run` | `docker-compose exec` |
| **Docker Compose** | `run --rm` | `up -d` | `up -d` | `up -d` then `exec` |

---

**Visual Guide Complete** ✅

For detailed information, see the full documentation files!
