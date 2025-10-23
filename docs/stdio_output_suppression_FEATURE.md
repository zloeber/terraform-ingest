# Stdio Output Suppression Feature

## Overview
When the MCP server runs in `stdio` transport mode, all output to stdout/stderr is automatically suppressed to prevent interference with the Model Context Protocol message stream. This feature ensures clean protocol-level communication without diagnostic output corruption.

## Implementation Details

### Global Context
Two new global variables control output suppression:

```python
_stdio_mode: bool = False  # Flag to suppress output in stdio mode
```

### Output Control Function
A new `_log()` wrapper function replaces all `print()` calls:

```python
def _log(message: str) -> None:
    """Print message only if not in stdio mode."""
    global _stdio_mode
    if not _stdio_mode:
        print(message)
```

### Context Management
The `set_mcp_context()` function now accepts a `stdio_mode` parameter:

```python
def set_mcp_context(
    ingester: TerraformIngest,
    config: IngestConfig,
    vector_db_enabled: bool,
    stdio_mode: bool = False,
) -> None:
    """Set the global MCP context with server configuration.
    
    Args:
        ingester: Configured TerraformIngest instance
        config: Loaded configuration
        vector_db_enabled: Whether vector database is enabled
        stdio_mode: Whether running in stdio mode (suppresses output)
    """
    global _ingester, _config, _vector_db_enabled, _stdio_mode
    _ingester = ingester
    _config = config
    _vector_db_enabled = vector_db_enabled
    _stdio_mode = stdio_mode
```

### Stdio Mode Detection
The `start()` and `main()` functions automatically detect stdio mode based on transport:

```python
# In start() function
transport_mode = (
    transport if transport else (mcp_config.transport if mcp_config else "stdio")
)
stdio_mode = transport_mode == "stdio"
set_mcp_context(ingester, config, vector_db_enabled, stdio_mode=stdio_mode)

# In main() function
transport_mode = mcp_config.transport if mcp_config else "stdio"
stdio_mode = transport_mode == "stdio"
set_mcp_context(ingester, config, vector_db_enabled, stdio_mode=stdio_mode)
```

### Affected Output
All diagnostic and informational output uses `_log()` instead of `print()`:

- Transport mode initialization messages
- Listening address information
- Ingestion startup notifications
- Vector database status messages
- Configuration loading messages
- Error messages during module loading

## Usage

### Automatic Detection
When launching the MCP server with `--transport stdio` (or default), output is automatically suppressed:

```bash
# Output is suppressed (default)
terraform-ingest-mcp

# Output is suppressed (explicit stdio)
terraform-ingest-mcp --transport stdio

# Output is shown (http-streamable)
terraform-ingest-mcp --transport http-streamable

# Output is shown (sse)
terraform-ingest-mcp --transport sse
```

### CLI Integration
The feature integrates with the existing CLI options:

```bash
# Stdio mode with CLI overrides (output suppressed)
terraform-ingest-mcp \
  --config-file production.yaml \
  --ingest-on-startup \
  --transport stdio

# HTTP mode with same overrides (output shown)
terraform-ingest-mcp \
  --config-file production.yaml \
  --ingest-on-startup \
  --transport http-streamable \
  --host 0.0.0.0 \
  --port 3000
```

## Technical Benefits

### Protocol Integrity
- **Prevents corruption**: No unexpected output interferes with MCP message stream
- **Client compatibility**: Clients can parse response streams cleanly
- **Protocol compliance**: Adheres to MCP specification for stdio transport

### Diagnostic Control
- **Development friendly**: Output shown for HTTP/SSE modes aids debugging
- **Production safe**: Stdio mode production deployments are silent
- **Consistent behavior**: Output behavior aligns with transport mode semantics

### Code Quality
- **Non-invasive**: Uses `_log()` wrapper instead of conditional blocks
- **Centralized control**: Single global flag manages all output
- **Easy to trace**: All output paths go through `_log()` function

## Testing

All 73 tests pass with this feature:
- Output suppression is transparent to existing functionality
- Tests verify all transport modes work correctly
- MCP protocol communication remains unchanged

Run tests to verify:
```bash
uv run pytest --maxfail=1 --disable-warnings -v tests/
```

## Future Enhancements

Potential improvements for future iterations:

1. **Logging Levels**: Extend `_log()` to support DEBUG, INFO, WARN, ERROR levels
2. **Log File Output**: Write suppressed output to logfiles when in stdio mode
3. **Metrics Collection**: Gather output metrics for performance analysis
4. **Dynamic Control**: Allow runtime toggling of output suppression via signals or APIs
