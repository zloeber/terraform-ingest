# FastMCP Configurable Instructions Feature

## Overview
The FastMCP instructions are now configurable through the `config.yaml` file, allowing users to customize the instructions that the MCP service provides to AI agents without modifying code.

## Changes Made

### 1. **Model Updates** (`src/terraform_ingest/models.py`)
Added an `instructions` field to the `McpConfig` class:

```python
class McpConfig(BaseModel):
    """Configuration for the MCP (Model Context Protocol) service."""

    auto_ingest: bool = False
    ingest_on_startup: bool = False
    refresh_interval_hours: Optional[int] = None
    instructions: str = "Service for querying ingested Terraform modules from Git repositories."
```

- **Type**: `str`
- **Default**: "Service for querying ingested Terraform modules from Git repositories."
- **Description**: Customizable instructions for the FastMCP service that AI agents will see

### 2. **Configuration File Updates** (`config.yaml`)
Updated the `mcp` section to include an `instructions` field:

```yaml
mcp:
  auto_ingest: true
  ingest_on_startup: true
  refresh_interval_hours: 6
  config_file: config.yaml
  instructions: "Service for querying ingested Terraform modules from Git repositories. Provides tools to list repositories and search modules by keywords, providers, or other criteria."
```

### 3. **MCP Service Updates** (`src/terraform_ingest/mcp_service.py`)

#### A. FastMCP Initialization
Updated the global FastMCP instance to use default instructions:

```python
mcp = FastMCP(
    name="terraform-ingest",
    instructions="Service for querying ingested Terraform modules from Git repositories.",
)
```

#### B. New Function: `_update_mcp_instructions()`
Added a new helper function to update MCP instructions from the configuration:

```python
def _update_mcp_instructions(config: Optional[IngestConfig]):
    """Update FastMCP server instructions from configuration.

    Args:
        config: Loaded IngestConfig, or None to use default instructions
    """
    global mcp

    if config and config.mcp and config.mcp.instructions:
        mcp.instructions = config.mcp.instructions
    else:
        mcp.instructions = (
            "Service for querying ingested Terraform modules from Git repositories."
        )
```

#### C. Updated `start()` Function
Integrated instruction loading into the startup sequence:

```python
def start(config_file: str = None):
    """Run the FastMCP server."""
    # ... existing code ...
    config = _load_config_file(config_file)

    # Update MCP instructions from configuration
    _update_mcp_instructions(config)
    
    # ... rest of startup ...
```

#### D. Updated `main()` Function
Similarly updated the main entry point:

```python
def main():
    """Run the FastMCP server."""
    config_file = os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")
    config = _load_config_file(config_file)

    # Update MCP instructions from configuration
    _update_mcp_instructions(config)
    
    # ... rest of startup ...
```

## Usage

### Default Behavior
If no `instructions` field is specified in the `config.yaml`, the default instructions are used:
```
"Service for querying ingested Terraform modules from Git repositories."
```

### Custom Instructions
To customize the instructions, add the `instructions` field to the `mcp` section of `config.yaml`:

```yaml
mcp:
  auto_ingest: true
  ingest_on_startup: true
  refresh_interval_hours: 6
  instructions: "Your custom instructions for the AI agent to use with this MCP service."
```

### Example Configurations

**Minimal Configuration:**
```yaml
mcp:
  auto_ingest: true
```
Uses default instructions.

**Custom Instructions:**
```yaml
mcp:
  auto_ingest: true
  ingest_on_startup: true
  refresh_interval_hours: 6
  instructions: |
    You are an expert in Terraform modules. Help users find and understand 
    Terraform modules from AWS, Azure, and Google Cloud providers. 
    Use the available tools to search and list modules.
```

## Benefits

1. **Customization**: Users can tailor the AI agent's behavior without code changes
2. **Flexibility**: Different deployment configurations can have different instructions
3. **Clarity**: Instructions are centralized in the configuration file
4. **Fallback**: Default instructions are always available if none are specified
5. **Consistency**: Instructions are loaded consistently through both `start()` and `main()` entry points

## Testing

All existing tests pass, including:
- Model validation tests
- MCP service functionality tests
- Configuration loading tests

The feature is fully tested and maintains backward compatibility.

## Integration

This feature integrates seamlessly with:
- Auto-ingestion configuration
- Vector database embedding configuration
- Periodic refresh intervals
- All existing MCP functionality

The instructions field is optional and does not affect any other functionality.
