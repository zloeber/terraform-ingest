# MCP Transport Modes

## Overview

The terraform-ingest MCP (Model Context Protocol) server supports multiple transport modes to allow flexible integration with different AI clients and environments. This feature provides three transport options:

1. **stdio** - Standard input/output communication (default)
2. **http-streamable** - HTTP-based streaming transport
3. **sse** - Server-Sent Events over HTTP

## Transport Modes

### Stdio (Default)

The stdio transport uses standard input and output for MCP communication. This is ideal for:

- Local development
- Integration with stdio-based MCP clients
- Subprocess-based communication
- AI agents using stdio transport

**Starting the server with stdio:**

```bash
terraform-ingest mcp

# Or explicitly specify stdio
terraform-ingest mcp --transport stdio
```

**Starting with automatic ingestion:**

```bash
terraform-ingest mcp --config config.yaml
```

### HTTP-Streamable

The http-streamable transport provides HTTP-based communication with streaming support. This mode is useful for:

- Web-based clients
- Remote connections over HTTP
- REST API integration
- Load-balanced deployments

**Starting the server with http-streamable:**

```bash
# Default host and port (127.0.0.1:3000)
terraform-ingest mcp --transport http-streamable

# Specify custom host and port
terraform-ingest mcp --transport http-streamable --host 0.0.0.0 --port 8080

# With configuration file
terraform-ingest mcp --config config.yaml --transport http-streamable --host 0.0.0.0 --port 3000
```

**Connecting to http-streamable server:**

```bash
# Example client connection (protocol depends on MCP client library)
curl -N http://localhost:3000/mcp
```

### Server-Sent Events (SSE)

The SSE transport uses Server-Sent Events over HTTP. This mode is ideal for:

- Browser-based clients
- Long-lived connections
- Real-time updates
- Firewall-friendly communication (HTTP only)

**Starting the server with SSE:**

```bash
# Default host and port (127.0.0.1:3000)
terraform-ingest mcp --transport sse

# Specify custom host and port
terraform-ingest mcp --transport sse --host localhost --port 8000

# With configuration file
terraform-ingest mcp --config config.yaml --transport sse --host 0.0.0.0 --port 3000
```

**Connecting to SSE server:**

```bash
# Example client connection using EventSource
const eventSource = new EventSource('http://localhost:3000/mcp');
eventSource.onmessage = (event) => {
  console.log('Message:', JSON.parse(event.data));
};
```

## Configuration File

Transport settings can be persisted in your `config.yaml` file for easier management:

```yaml
repositories:
  - url: https://github.com/terraform-aws-modules/terraform-aws-vpc
    branches: ["main"]
    include_tags: true

mcp:
  # Transport configuration
  transport: "http-streamable"  # or "stdio", "sse"
  host: "0.0.0.0"              # Bind address (used for http-streamable and sse)
  port: 3000                   # Port (used for http-streamable and sse)
  
  # Auto-ingestion
  auto_ingest: false
  ingest_on_startup: true
  refresh_interval_hours: 24
```

## Command-Line Options

The MCP command supports the following transport-related options:

```bash
terraform-ingest mcp --help
```

Options:
- `--transport, -t [stdio|http-streamable|sse]` - Transport mode (overrides config)
- `--host, -h TEXT` - Host to bind to for http-streamable and sse (overrides config)
- `--port, -p INTEGER` - Port to bind to for http-streamable and sse (overrides config)
- `--config, -c TEXT` - Configuration file path

## Priority Order

When determining which settings to use, the priority is:

1. **Command-line arguments** (highest priority)
   - `--transport`
   - `--host`
   - `--port`

2. **Configuration file** (config.yaml or specified file)
   - `mcp.transport`
   - `mcp.host`
   - `mcp.port`

3. **Defaults** (lowest priority)
   - transport: `stdio`
   - host: `127.0.0.1`
   - port: `3000`

## Examples

### Development with Stdio

```bash
# Simple local development
terraform-ingest mcp --config config.yaml
```

### Production HTTP Server

```bash
# Listen on all interfaces for HTTP clients
terraform-ingest mcp --transport http-streamable --host 0.0.0.0 --port 3000 --config prod-config.yaml
```

### Browser-Based Client with SSE

```bash
# Start SSE server for web client
terraform-ingest mcp --transport sse --host localhost --port 8000 --config config.yaml
```

### Docker Deployment

```yaml
# docker-compose.yml example
services:
  mcp-server:
    image: terraform-ingest:latest
    command: terraform-ingest mcp --transport http-streamable --host 0.0.0.0 --port 3000
    ports:
      - "3000:3000"
    environment:
      - TERRAFORM_INGEST_CONFIG=/config/config.yaml
    volumes:
      - ./config.yaml:/config/config.yaml
      - ./output:/app/output
```

## Troubleshooting

### "Address already in use" error

If you get an address already in use error:

```bash
# Use a different port
terraform-ingest mcp --transport http-streamable --port 8080

# Or on macOS/Linux, find and kill the process
lsof -i :3000
kill -9 <PID>
```

### Connection refused

For http-streamable and SSE transports:

- Ensure the port is not blocked by firewall
- Verify you're connecting to the correct host and port
- Check that the server started successfully (look for "Listening on" message)

### Stdio transport not working

- Ensure no other programs are reading from stdin
- Verify the MCP client is configured to use stdio transport
- Check that stdout/stderr are not being redirected to a file

## Security Considerations

### HTTP Transports (http-streamable and sse)

- By default, binds to `127.0.0.1` (localhost only)
- For remote access, explicitly use `0.0.0.0` or specific IP address
- Consider using a reverse proxy (nginx, Apache) with SSL/TLS in production
- Implement authentication at the proxy level if needed

### Example: Nginx Reverse Proxy with SSL

```nginx
server {
    listen 443 ssl;
    server_name mcp.example.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Related Documentation

- [FastMCP Service Configuration Guide](./MCP.md)
- [Architecture Overview](./DEVELOPMENT.md)
- [Docker Deployment](./DOCKER.md)
