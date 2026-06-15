"""Track and broadcast ingestion progress to MCP clients."""

from __future__ import annotations

import asyncio
import threading
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from mcp import LoggingLevel
from mcp.server.session import ServerSession


class IngestionPhase(str, Enum):
    """High-level ingestion phases reported to clients."""

    IDLE = "idle"
    STARTING = "starting"
    CLONING = "cloning"
    PARSING = "parsing"
    SAVING = "saving"
    INDEXING = "indexing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionProgressSnapshot:
    """Point-in-time ingestion progress."""

    status: str
    phase: str
    message: str
    current: int = 0
    total: int = 0
    modules_processed: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    recent_messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot for MCP resources and tools."""
        return {
            "status": self.status,
            "phase": self.phase,
            "message": self.message,
            "current": self.current,
            "total": self.total,
            "modules_processed": self.modules_processed,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "recent_messages": list(self.recent_messages),
        }


class IngestionProgressTracker:
    """Thread-safe ingestion progress state with optional MCP client notifications."""

    _MAX_RECENT_MESSAGES = 20

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        self._sessions: weakref.WeakSet[ServerSession] = weakref.WeakSet()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._notify_clients = True
        self._reset_unlocked()

    def _reset_unlocked(self) -> None:
        self.status = IngestionPhase.IDLE
        self.phase = IngestionPhase.IDLE
        self.message = "No ingestion in progress"
        self.current = 0
        self.total = 0
        self.modules_processed = 0
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None
        self.recent_messages: list[str] = []

    def set_notify_clients(self, enabled: bool) -> None:
        """Enable or disable MCP logging notifications."""
        self._notify_clients = enabled

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the server event loop for cross-thread notification delivery."""
        self._event_loop = loop

    def register_session(self, session: ServerSession) -> None:
        """Track a connected MCP client session for progress notifications."""
        self._sessions.add(session)
        snapshot = self.snapshot()
        if snapshot.status != IngestionPhase.IDLE.value:
            self._schedule_client_notification(
                f"Ingestion status: {snapshot.phase} — {snapshot.message}",
                level="info",
            )

    def is_active(self) -> bool:
        """Return True while an ingestion job is running."""
        with self._state_lock:
            return self.status == IngestionPhase.STARTING

    def snapshot(self) -> IngestionProgressSnapshot:
        """Return a copy of the current progress state."""
        with self._state_lock:
            return IngestionProgressSnapshot(
                status=self.status.value,
                phase=self.phase.value,
                message=self.message,
                current=self.current,
                total=self.total,
                modules_processed=self.modules_processed,
                started_at=self.started_at,
                completed_at=self.completed_at,
                error=self.error,
                recent_messages=list(self.recent_messages),
            )

    def start(
        self, total_repositories: int, message: str = "Starting ingestion"
    ) -> None:
        """Mark ingestion as started."""
        now = datetime.now(timezone.utc).isoformat()
        with self._state_lock:
            self._reset_unlocked()
            self.status = IngestionPhase.STARTING
            self.phase = IngestionPhase.STARTING
            self.message = message
            self.total = total_repositories
            self.current = 0
            self.started_at = now
        self._record_and_notify(message, level="info")

    def update(
        self,
        phase: IngestionPhase,
        message: str,
        *,
        current: Optional[int] = None,
        total: Optional[int] = None,
        level: LoggingLevel = "info",
    ) -> None:
        """Update progress for the current phase."""
        with self._state_lock:
            if self.status in (IngestionPhase.COMPLETED, IngestionPhase.FAILED):
                return
            self.status = IngestionPhase.STARTING
            self.phase = phase
            self.message = message
            if current is not None:
                self.current = current
            if total is not None:
                self.total = total
        self._record_and_notify(message, level=level)

    def add_modules(self, count: int) -> None:
        """Increment the processed module counter."""
        with self._state_lock:
            self.modules_processed += count

    def complete(self, message: str, modules_processed: Optional[int] = None) -> None:
        """Mark ingestion as successfully completed."""
        now = datetime.now(timezone.utc).isoformat()
        with self._state_lock:
            self.status = IngestionPhase.COMPLETED
            self.phase = IngestionPhase.COMPLETED
            self.message = message
            self.completed_at = now
            if modules_processed is not None:
                self.modules_processed = modules_processed
            if self.total and self.current < self.total:
                self.current = self.total
        self._record_and_notify(message, level="info")

    def fail(self, message: str, error: Optional[str] = None) -> None:
        """Mark ingestion as failed."""
        now = datetime.now(timezone.utc).isoformat()
        with self._state_lock:
            self.status = IngestionPhase.FAILED
            self.phase = IngestionPhase.FAILED
            self.message = message
            self.error = error or message
            self.completed_at = now
        self._record_and_notify(message, level="error")

    def _record_and_notify(self, message: str, level: LoggingLevel = "info") -> None:
        with self._state_lock:
            self.recent_messages.append(message)
            if len(self.recent_messages) > self._MAX_RECENT_MESSAGES:
                self.recent_messages = self.recent_messages[
                    -self._MAX_RECENT_MESSAGES :
                ]
        if self._notify_clients:
            self._schedule_client_notification(message, level=level)

    def _schedule_client_notification(
        self, message: str, level: LoggingLevel = "info"
    ) -> None:
        loop = self._event_loop
        if loop is None or not loop.is_running():
            return

        asyncio.run_coroutine_threadsafe(
            self._broadcast_log_message(message, level=level),
            loop,
        )

    async def _broadcast_log_message(
        self, message: str, level: LoggingLevel = "info"
    ) -> None:
        """Send a log notification to all connected MCP client sessions."""
        sessions = list(self._sessions)
        for session in sessions:
            try:
                await session.send_log_message(
                    level=level,
                    data={"msg": message},
                    logger="terraform-ingest",
                )
            except Exception:
                self._sessions.discard(session)


_tracker = IngestionProgressTracker()


def get_ingestion_tracker() -> IngestionProgressTracker:
    """Return the shared ingestion progress tracker."""
    return _tracker
