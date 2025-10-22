# MCP Auto-Ingestion Configuration Feature

## Overview
Added MCP (Model Context Protocol) configuration section to `config.yaml` that enables automatic ingestion of Terraform modules when the MCP server starts, with optional periodic refresh functionality.

## Changes Made

### 1. Enhanced Models (`src/terraform_ingest/models.py`)
- Added `McpConfig` class with auto-ingestion settings:
  - `auto_ingest: bool = False` - Master toggle for auto-ingestion
  - `ingest_on_startup: bool = False` - Run ingestion immediately when MCP server starts  
  - `refresh_interval_hours: Optional[int] = None` - Periodic refresh interval (null to disable)
  - `config_file: str = "config.yaml"` - Configuration file to use for ingestion

- Updated `IngestConfig` to include optional `mcp: Optional[McpConfig] = None` field

### 2. Enhanced MCP Service (`src/terraform_ingest/mcp_service.py`)
- Added configuration loading and auto-ingestion logic
- Implemented startup ingestion when `ingest_on_startup=true`
- Added periodic refresh using background daemon thread
- Enhanced `main()` function to check for MCP configuration and execute auto-ingestion

### 3. Updated Configuration Files
- **Main config** (`config.yaml`): Added comprehensive MCP section with all options
- **Example config** (`examples/config.yaml`): Added MCP section with different refresh interval

## Configuration Options

### MCP Section in config.yaml
```yaml
mcp:
  auto_ingest: true               # Enable automatic ingestion when MCP server starts
  ingest_on_startup: true         # Run ingestion immediately on startup
  refresh_interval_hours: 24      # Auto-refresh every 24 hours (null to disable)
  config_file: config.yaml        # Configuration file to use for auto-ingestion
```

### Configuration Scenarios

#### Startup Ingestion Only
```yaml
mcp:
  auto_ingest: true
  ingest_on_startup: true
  refresh_interval_hours: null    # No periodic refresh
```

#### Periodic Refresh Only  
```yaml
mcp:
  auto_ingest: true
  ingest_on_startup: false        # Skip startup ingestion
  refresh_interval_hours: 6       # Refresh every 6 hours
```

#### Full Auto-Ingestion
```yaml
mcp:
  auto_ingest: true
  ingest_on_startup: true         # Initial ingestion on startup
  refresh_interval_hours: 24      # Plus periodic refresh every 24 hours
```

#### Disabled (Default)
```yaml
mcp:
  auto_ingest: false              # All auto-ingestion disabled
```

## Implementation Details

### Startup Flow
1. MCP service starts and loads configuration from `config.yaml`
2. If `mcp.auto_ingest=true` and `mcp.ingest_on_startup=true`:
   - Runs full ingestion process using specified config file
   - Processes all repositories, branches, and tags as configured
3. If `mcp.refresh_interval_hours` is set:
   - Starts background daemon thread for periodic refresh
4. MCP server becomes ready to serve AI agents

### Periodic Refresh
- Runs in separate daemon thread (non-blocking)
- Uses configured refresh interval in hours
- Executes same ingestion process as startup
- Continues running until MCP server shutdown

### Configuration Discovery
- Default config file: `config.yaml` in current directory
- Override via `TERRAFORM_INGEST_CONFIG` environment variable
- Falls back gracefully if config file not found

## Usage Examples

### Start MCP with Auto-Ingestion
```bash
# Uses default config.yaml with MCP settings
terraform-ingest-mcp

# Use custom config file
TERRAFORM_INGEST_CONFIG=my-config.yaml terraform-ingest-mcp
```

### Configuration Validation
The MCP configuration is validated at startup:
- Invalid refresh intervals are handled gracefully
- Missing config files produce warnings but don't crash the service
- Malformed YAML produces clear error messages

## Benefits

1. **Zero-Touch Operation**: MCP server automatically has fresh data without manual intervention
2. **Always Current**: Periodic refresh ensures AI agents access latest module versions
3. **Flexible Scheduling**: Configurable refresh intervals for different use cases
4. **Resource Efficient**: Background threading doesn't block MCP service requests
5. **Robust Error Handling**: Configuration errors don't prevent MCP server startup
6. **Environment Integration**: Works with existing `terraform-ingest` CLI and configuration

## Use Cases

- **Development Environments**: Auto-refresh every few hours to catch rapid changes
- **Production RAG Systems**: Daily refresh for stable, current module information
- **CI/CD Integration**: Startup ingestion ensures fresh data after deployments
- **Multi-Repository Monitoring**: Automatic tracking of changes across many Terraform repos

## Error Handling

- Configuration file not found: Warning logged, MCP server continues
- Ingestion failures: Logged but don't crash MCP service
- Invalid refresh intervals: Ignored with warning
- Thread exceptions: Daemon threads exit gracefully

The implementation provides robust auto-ingestion capabilities while maintaining the reliability and performance of the MCP service for AI agent interactions.