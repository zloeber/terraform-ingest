"""Tests for shared ingestion runner."""

from unittest.mock import MagicMock, patch


from terraform_ingest.ingestion_progress import get_ingestion_tracker, IngestionPhase
from terraform_ingest.ingestion_runner import (
    IngestionRunOptions,
    execute_ingestion,
    get_ingestion_status,
    is_ingestion_active,
    resolve_config_file,
)


def test_resolve_config_file_uses_env(monkeypatch):
    monkeypatch.setenv("TERRAFORM_INGEST_CONFIG", "/tmp/custom.yaml")
    assert resolve_config_file() == "/tmp/custom.yaml"
    assert resolve_config_file("override.yaml") == "override.yaml"


def test_get_ingestion_status_returns_snapshot():
    tracker = get_ingestion_tracker()
    tracker.set_notify_clients(False)
    tracker.start(2, message="runner test")

    status = get_ingestion_status()
    assert status["message"] == "runner test"
    assert is_ingestion_active() is True


def test_execute_ingestion_rejects_when_already_running():
    tracker = get_ingestion_tracker()
    tracker.set_notify_clients(False)
    tracker.start(1, message="existing job")

    ingester = MagicMock()
    result = execute_ingestion(
        ingester,
        IngestionRunOptions(),
        tracker=tracker,
        require_idle=True,
    )

    assert result.success is False
    assert result.error == "ingestion_already_running"
    ingester.ingest.assert_not_called()


@patch("terraform_ingest.ingestion_runner._update_mcp_context")
def test_execute_ingestion_success(mock_update_context):
    tracker = get_ingestion_tracker()
    tracker.set_notify_clients(False)
    tracker.complete("reset", modules_processed=0)

    ingester = MagicMock()
    ingester.ingest.return_value = []
    ingester.output_dir.mkdir = MagicMock()
    ingester.repo_manager.clone_dir.mkdir = MagicMock()

    result = execute_ingestion(
        ingester,
        IngestionRunOptions(),
        tracker=tracker,
        require_idle=True,
    )

    assert result.success is True
    assert result.count == 0
    assert result.progress["status"] == IngestionPhase.COMPLETED.value
