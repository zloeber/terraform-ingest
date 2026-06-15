"""MCP lifecycle helpers for background ingestion and client notifications."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from fastmcp import FastMCP
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from mcp.types import InitializeRequestParams

from terraform_ingest.ingestion_progress import get_ingestion_tracker
from terraform_ingest.ingestion_runner import (
    IngestionRunOptions,
    get_ingestion_status,
    resolve_config_file,
    run_ingestion_from_yaml,
    schedule_background_ingestion_thread,
)
from terraform_ingest.models import IngestConfig
from terraform_ingest.tty_logger import setup_tty_logger

logger = setup_tty_logger()


@dataclass
class McpStartupSettings:
    """Runtime settings for MCP startup ingestion behavior."""

    config_file: str
    ingest_config: Optional[IngestConfig]
    ingest_on_startup: bool = False
    blocking_ingest_on_startup: bool = False
    notify_ingestion_progress: bool = True


_startup_settings: Optional[McpStartupSettings] = None
_ingestion_task: Optional[asyncio.Task[None]] = None


def set_startup_settings(settings: Optional[McpStartupSettings]) -> None:
    """Configure ingestion behavior before the MCP server starts."""
    global _startup_settings
    _startup_settings = settings


def get_startup_settings() -> Optional[McpStartupSettings]:
    """Return the configured MCP startup settings."""
    return _startup_settings


class IngestionNotificationMiddleware(Middleware):
    """Register MCP client sessions so ingestion progress can be pushed to clients."""

    async def on_initialize(
        self,
        context: MiddlewareContext[InitializeRequestParams],
        call_next: CallNext[InitializeRequestParams, None],
    ) -> None:
        await call_next(context)
        fastmcp_context = context.fastmcp_context
        if fastmcp_context is not None:
            get_ingestion_tracker().register_session(fastmcp_context.session)

    async def on_request(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ):
        fastmcp_context = context.fastmcp_context
        if fastmcp_context is not None:
            get_ingestion_tracker().register_session(fastmcp_context.session)
        return await call_next(context)


def _build_run_options(
    *,
    cleanup: bool = False,
    skip_existing: bool = False,
    no_cache: bool = False,
    notify_progress: bool = True,
) -> IngestionRunOptions:
    """Create ingestion options for MCP-triggered runs."""
    return IngestionRunOptions(
        cleanup=cleanup,
        skip_existing=skip_existing,
        no_cache=no_cache,
        notify_progress=notify_progress,
    )


def _run_ingestion_sync(
    config_file: str,
    options: Optional[IngestionRunOptions] = None,
) -> None:
    """Run ingestion synchronously with progress tracking."""
    run_ingestion_from_yaml(config_file, options)


async def _run_ingestion_background(
    config_file: str,
    options: Optional[IngestionRunOptions] = None,
) -> None:
    """Execute ingestion in a worker thread so the MCP server stays responsive."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_ingestion_sync, config_file, options)


def schedule_background_ingestion(
    config_file: str,
    options: Optional[IngestionRunOptions] = None,
) -> Optional[asyncio.Task[None]]:
    """Schedule ingestion on the current event loop."""
    global _ingestion_task

    tracker = get_ingestion_tracker()
    if tracker.is_active():
        return _ingestion_task

    tracker.set_notify_clients(options.notify_progress if options else True)
    tracker.set_event_loop(asyncio.get_running_loop())

    _ingestion_task = asyncio.create_task(
        _run_ingestion_background(config_file, options)
    )
    return _ingestion_task


def schedule_startup_ingestion(
    settings: McpStartupSettings,
) -> Optional[asyncio.Task[None]]:
    """Schedule non-blocking startup ingestion if enabled."""
    if not settings.ingest_on_startup or settings.blocking_ingest_on_startup:
        return None

    options = _build_run_options(notify_progress=settings.notify_ingestion_progress)
    return schedule_background_ingestion(settings.config_file, options)


def run_blocking_startup_ingestion(settings: McpStartupSettings) -> None:
    """Run startup ingestion synchronously before the MCP server accepts clients."""
    options = _build_run_options(notify_progress=False)
    _run_ingestion_sync(settings.config_file, options)


def trigger_ingestion(
    config_file: Optional[str] = None,
    *,
    background: bool = True,
    cleanup: bool = False,
    skip_existing: bool = False,
    no_cache: bool = False,
    notify_progress: bool = True,
) -> dict:
    """Start ingestion from MCP, returning an immediate status payload."""
    resolved_config = resolve_config_file(config_file)
    options = _build_run_options(
        cleanup=cleanup,
        skip_existing=skip_existing,
        no_cache=no_cache,
        notify_progress=notify_progress,
    )

    tracker = get_ingestion_tracker()
    if tracker.is_active():
        return {
            "success": False,
            "message": "Ingestion is already in progress",
            "error": "ingestion_already_running",
            "started_in_background": True,
            "progress": get_ingestion_status(),
        }

    if background:
        try:
            loop = asyncio.get_running_loop()
            tracker.set_notify_clients(notify_progress)
            tracker.set_event_loop(loop)
            schedule_background_ingestion(resolved_config, options)
            return {
                "success": True,
                "message": f"Background ingestion started from {resolved_config}",
                "started_in_background": True,
                "progress": get_ingestion_status(),
            }
        except RuntimeError:
            result = schedule_background_ingestion_thread(resolved_config, options)
            return result.to_dict()

    result = run_ingestion_from_yaml(resolved_config, options)
    return result.to_dict()


@asynccontextmanager
async def mcp_lifespan(server: FastMCP) -> AsyncIterator[dict[str, object]]:
    """FastMCP lifespan that starts background ingestion when configured."""
    global _ingestion_task

    settings = get_startup_settings()
    task: Optional[asyncio.Task[None]] = None

    if settings is not None:
        get_ingestion_tracker().set_notify_clients(settings.notify_ingestion_progress)
        get_ingestion_tracker().set_event_loop(asyncio.get_running_loop())
        task = schedule_startup_ingestion(settings)

    try:
        yield {"ingestion_task": task}
    finally:
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        _ingestion_task = None


def get_ingestion_status_dict() -> dict:
    """Return the current ingestion status for MCP tools and resources."""
    return get_ingestion_status()
