"""Tests for ingestion progress tracking."""

from terraform_ingest.ingestion_progress import (
    IngestionPhase,
    IngestionProgressTracker,
    get_ingestion_tracker,
)


def test_tracker_start_and_complete():
    tracker = IngestionProgressTracker()
    tracker.set_notify_clients(False)

    tracker.start(2, message="Starting test ingestion")
    tracker.update(
        IngestionPhase.CLONING,
        "Cloning repository",
        current=1,
        total=2,
    )
    tracker.add_modules(3)
    tracker.complete("Done", modules_processed=3)

    snapshot = tracker.snapshot()
    assert snapshot.status == IngestionPhase.COMPLETED.value
    assert snapshot.phase == IngestionPhase.COMPLETED.value
    assert snapshot.modules_processed == 3
    assert snapshot.current == 2
    assert snapshot.total == 2
    assert snapshot.started_at is not None
    assert snapshot.completed_at is not None
    assert "Cloning repository" in snapshot.recent_messages


def test_tracker_failure():
    tracker = IngestionProgressTracker()
    tracker.set_notify_clients(False)
    tracker.start(1)
    tracker.fail("Clone failed", error="network timeout")

    snapshot = tracker.snapshot()
    assert snapshot.status == IngestionPhase.FAILED.value
    assert snapshot.error == "network timeout"


def test_get_ingestion_tracker_returns_singleton():
    assert get_ingestion_tracker() is get_ingestion_tracker()


def test_tracker_is_active():
    tracker = IngestionProgressTracker()
    tracker.set_notify_clients(False)
    assert tracker.is_active() is False

    tracker.start(1)
    assert tracker.is_active() is True

    tracker.complete("done")
    assert tracker.is_active() is False


def test_snapshot_to_dict():
    tracker = IngestionProgressTracker()
    tracker.set_notify_clients(False)
    tracker.start(1)

    data = tracker.snapshot().to_dict()
    assert data["status"] == IngestionPhase.STARTING.value
    assert "recent_messages" in data
