"""Shared ingestion execution for CLI, API, and MCP interfaces."""

from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from terraform_ingest.ingest import TerraformIngest
from terraform_ingest.ingestion_progress import (
    IngestionProgressTracker,
    get_ingestion_tracker,
)
from terraform_ingest.models import IngestConfig, TerraformModuleSummary
from terraform_ingest.tty_logger import setup_tty_logger

logger = setup_tty_logger()


class IngestionAlreadyRunningError(Exception):
    """Raised when an ingestion job is already in progress."""


@dataclass
class IngestionRunOptions:
    """Options shared across CLI, API, and MCP ingestion entry points."""

    auto_install_deps: bool = True
    skip_existing: bool = False
    cleanup: bool = False
    no_cache: bool = False
    notify_progress: bool = True
    output_dir: Optional[str] = None
    clone_dir: Optional[str] = None


@dataclass
class IngestionRunResult:
    """Result of an ingestion request."""

    success: bool
    message: str
    count: int = 0
    summaries: List[TerraformModuleSummary] = field(default_factory=list)
    error: Optional[str] = None
    started_in_background: bool = False
    progress: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result for JSON APIs and MCP tools."""
        data: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
            "count": self.count,
            "error": self.error,
            "started_in_background": self.started_in_background,
            "progress": self.progress,
        }
        if self.summaries and not self.started_in_background:
            data["summaries"] = [summary.model_dump() for summary in self.summaries]
        return data


def get_ingestion_status() -> dict[str, Any]:
    """Return the current ingestion progress snapshot."""
    return get_ingestion_tracker().snapshot().to_dict()


def is_ingestion_active() -> bool:
    """Return True when an ingestion job is currently running."""
    return get_ingestion_tracker().is_active()


def _apply_path_overrides(
    ingester: TerraformIngest, options: IngestionRunOptions
) -> None:
    """Apply optional output and clone directory overrides."""
    if options.output_dir is not None:
        ingester.config.output_dir = options.output_dir
        ingester.output_dir = Path(options.output_dir)

    if options.clone_dir is not None:
        ingester.config.clone_dir = options.clone_dir
        ingester.repo_manager.clone_dir = Path(options.clone_dir)


def _prepare_workspace(ingester: TerraformIngest, options: IngestionRunOptions) -> None:
    """Prepare output and clone directories before ingestion."""
    if options.no_cache:
        shutil.rmtree(ingester.output_dir, ignore_errors=True)
        shutil.rmtree(ingester.repo_manager.clone_dir, ignore_errors=True)

    ingester.output_dir.mkdir(parents=True, exist_ok=True)
    ingester.repo_manager.clone_dir.mkdir(parents=True, exist_ok=True)


def _update_mcp_context(ingester: TerraformIngest) -> None:
    """Refresh the MCP server context after ingestion completes."""
    try:
        from terraform_ingest.mcp_service import MCPContext

        ctx = MCPContext.get_instance()
        if ctx is not None:
            ctx.ingester = ingester
            ctx.vector_db_enabled = ingester.vector_db is not None
    except Exception:
        pass


def execute_ingestion(
    ingester: TerraformIngest,
    options: Optional[IngestionRunOptions] = None,
    *,
    tracker: Optional[IngestionProgressTracker] = None,
    require_idle: bool = True,
) -> IngestionRunResult:
    """Run ingestion for a prepared TerraformIngest instance."""
    run_options = options or IngestionRunOptions()
    progress = tracker or get_ingestion_tracker()
    progress.set_notify_clients(run_options.notify_progress)

    if require_idle and progress.is_active():
        snapshot = progress.snapshot().to_dict()
        return IngestionRunResult(
            success=False,
            message="Ingestion is already in progress",
            error="ingestion_already_running",
            progress=snapshot,
        )

    _apply_path_overrides(ingester, run_options)
    _prepare_workspace(ingester, run_options)

    try:
        summaries = ingester.ingest(progress=progress)
        if run_options.cleanup:
            ingester.cleanup()

        _update_mcp_context(ingester)

        message = f"Successfully ingested {len(summaries)} module(s)"
        logger.info(message)
        return IngestionRunResult(
            success=True,
            message=message,
            count=len(summaries),
            summaries=summaries,
            progress=progress.snapshot().to_dict(),
        )
    except Exception as exc:
        progress.fail(f"Ingestion failed: {exc}", error=str(exc))
        logger.error(f"Error during ingestion: {exc}")
        return IngestionRunResult(
            success=False,
            message=f"Ingestion failed: {exc}",
            error=str(exc),
            progress=progress.snapshot().to_dict(),
        )


def run_ingestion_from_yaml(
    config_file: str,
    options: Optional[IngestionRunOptions] = None,
    *,
    require_idle: bool = True,
) -> IngestionRunResult:
    """Load a YAML config file and run ingestion."""
    run_options = options or IngestionRunOptions()
    ingester = TerraformIngest.from_yaml(
        config_file,
        logger=logger,
        auto_install_deps=run_options.auto_install_deps,
        skip_existing=run_options.skip_existing,
    )
    return execute_ingestion(
        ingester,
        run_options,
        require_idle=require_idle,
    )


def run_ingestion_from_config(
    config: IngestConfig,
    options: Optional[IngestionRunOptions] = None,
    *,
    require_idle: bool = True,
) -> IngestionRunResult:
    """Run ingestion from an in-memory configuration object."""
    run_options = options or IngestionRunOptions()
    ingester = TerraformIngest(
        config,
        logger=logger,
        auto_install_deps=run_options.auto_install_deps,
        skip_existing=run_options.skip_existing,
    )
    return execute_ingestion(
        ingester,
        run_options,
        require_idle=require_idle,
    )


def resolve_config_file(config_file: Optional[str] = None) -> str:
    """Resolve the config file path from argument or environment."""
    return config_file or os.getenv("TERRAFORM_INGEST_CONFIG", "config.yaml")


_background_thread: Optional[threading.Thread] = None


def schedule_background_ingestion_thread(
    config_file: str,
    options: Optional[IngestionRunOptions] = None,
) -> IngestionRunResult:
    """Start ingestion on a background thread for CLI and API-style callers."""
    global _background_thread

    run_options = options or IngestionRunOptions()
    tracker = get_ingestion_tracker()
    tracker.set_notify_clients(run_options.notify_progress)

    if tracker.is_active():
        return IngestionRunResult(
            success=False,
            message="Ingestion is already in progress",
            error="ingestion_already_running",
            started_in_background=True,
            progress=tracker.snapshot().to_dict(),
        )

    def _target() -> None:
        run_ingestion_from_yaml(config_file, run_options, require_idle=False)

    _background_thread = threading.Thread(target=_target, daemon=True)
    _background_thread.start()

    return IngestionRunResult(
        success=True,
        message=f"Background ingestion started from {config_file}",
        started_in_background=True,
        progress=tracker.snapshot().to_dict(),
    )
