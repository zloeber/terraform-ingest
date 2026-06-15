# MCP Ingestion Progress

The MCP server can run initial and scheduled ingestion without blocking client
connections. Progress is exposed through MCP notifications, a tool, and a resource.

## Behavior

| Setting | Default | Effect |
|---------|---------|--------|
| `mcp.ingest_on_startup` | `false` | Run ingestion when the MCP server starts |
| `mcp.blocking_ingest_on_startup` | `false` | Block server startup until ingestion finishes |
| `mcp.notify_ingestion_progress` | `true` | Send MCP log notifications to connected clients |

With the defaults, the server accepts MCP connections immediately while ingestion
runs in a background thread. Clients that support MCP logging see live updates for:

- Repository cloning and updates
- Branch and tag parsing
- JSON summary writes
- Module index finalization
- Vector embedding upserts

Terminal output continues to use the existing TTY logger.

## Client APIs

All interfaces expose the same ingestion behavior:

| Interface | Start ingestion | Poll progress |
|-----------|-----------------|---------------|
| MCP | `run_ingestion` tool | `get_ingestion_status` tool or `ingestion://status` resource |
| CLI | `terraform-ingest ingestion run` | `terraform-ingest ingestion status` |
| API | `POST /ingest/background` | `GET /ingestion/status` |

Synchronous ingestion (blocking until complete) is available via:

- MCP: `run_ingestion(background=false)`
- CLI: `terraform-ingest ingest config.yaml` or `terraform-ingest ingestion run`
- API: `POST /ingest`, `POST /analyze`, or `POST /ingest-from-yaml`

### `run_ingestion` tool (MCP)

Starts ingestion from a YAML config file. Defaults to background mode.

### `get_ingestion_status` tool (MCP)

Returns a JSON object with `status`, `phase`, `message`, `current`, `total`,
`modules_processed`, timestamps, and `recent_messages`.

### `ingestion://status` resource (MCP)

Same data as the tool, formatted as JSON for resource-based polling.

### MCP log notifications

When `notify_ingestion_progress` is enabled, the server sends
`notifications/message` events with logger name `terraform-ingest`.

## Example configuration

```yaml
mcp:
  ingest_on_startup: true
  auto_ingest: true
  refresh_interval_hours: 24
  notify_ingestion_progress: true
  blocking_ingest_on_startup: false
```

## Blocking mode

Set `blocking_ingest_on_startup: true` if downstream automation requires every
module to be indexed before the first tool call. This matches the pre-2026 behavior
and disables client notifications during the initial ingest because no client is
connected yet.
