# CLI MCP Command Implementation

## Overview
Added a new `mcp` command to the CLI that starts the MCP (Model Context Protocol) server with auto-ingestion capabilities.

## Changes Made

### Updated CLI (`src/terraform_ingest/cli.py`)
- Added new `mcp` command with configuration file option
- Integrated with existing MCP service functionality
- Added proper environment variable handling for custom config files
- Included user-friendly help text and examples

## Command Usage

### Basic Usage
```bash
# Start MCP server with default config.yaml
terraform-ingest mcp

# Start MCP server with custom configuration
terraform-ingest mcp --config my-config.yaml
```

### Command Options
- `-c, --config TEXT`: Configuration file for auto-ingestion settings (default: config.yaml)

### Command Help
```bash
terraform-ingest mcp --help
```

## Integration with Auto-Ingestion

The MCP command automatically:

1. **Loads Configuration**: Reads the specified config file (default: `config.yaml`)
2. **Sets Environment**: Sets `TERRAFORM_INGEST_CONFIG` if custom config provided
3. **Runs Auto-Ingestion**: Executes startup ingestion if `mcp.ingest_on_startup=true`
4. **Starts Periodic Refresh**: Begins background thread if `mcp.refresh_interval_hours` is set
5. **Launches MCP Server**: Starts FastMCP server for AI agent communication

## CLI Command Structure

The complete CLI now includes:
- `analyze` - Analyze a single repository
- `ingest` - Batch ingest from configuration  
- `init` - Initialize sample configuration
- `mcp` - **NEW** - Start MCP server with auto-ingestion
- `serve` - Start FastAPI REST server

## Examples

### Start MCP with Auto-Ingestion
```bash
# Uses config.yaml, runs startup ingestion, starts periodic refresh
terraform-ingest mcp
```

### Start MCP with Custom Config
```bash
# Uses custom-config.yaml for all MCP settings
terraform-ingest mcp --config custom-config.yaml
```

### MCP Configuration Dependencies
The `mcp` command behavior depends on the configuration file:

```yaml
mcp:
  auto_ingest: true               # Enable auto-ingestion features
  ingest_on_startup: true         # Run ingestion on MCP startup  
  refresh_interval_hours: 24      # Background refresh every 24 hours
```

## User Experience

### Command Feedback
```
$ terraform-ingest mcp
Starting MCP server with config: config.yaml
Press CTRL+C to quit
MCP auto-ingestion enabled, running initial ingestion...
Auto-ingestion completed: 37 modules processed
Started periodic ingestion thread (every 24h)
Starting FastMCP server...
```

### Graceful Shutdown
- Supports `CTRL+C` to stop the server
- Shows appropriate shutdown message
- Background threads terminate cleanly

## Benefits

1. **Unified CLI**: Single entry point for all terraform-ingest functionality
2. **Configuration Flexibility**: Supports custom config files via command line
3. **Auto-Ingestion Integration**: Seamlessly integrates with MCP auto-ingestion features
4. **User-Friendly**: Clear feedback and help text
5. **Consistent Interface**: Follows same patterns as other CLI commands

## Backward Compatibility

- Existing `terraform-ingest-mcp` script continues to work
- New `terraform-ingest mcp` provides the same functionality with CLI integration
- Configuration file format unchanged
- Environment variable support maintained