"""Tests for MCP ingestion lifecycle helpers."""

from terraform_ingest.mcp_ingestion import (
    McpStartupSettings,
    get_ingestion_status_dict,
    set_startup_settings,
)
from terraform_ingest.ingestion_progress import get_ingestion_tracker, IngestionPhase


def test_get_ingestion_status_dict_reflects_tracker_state():
    tracker = get_ingestion_tracker()
    tracker.set_notify_clients(False)
    tracker.start(1, message="test ingestion")

    status = get_ingestion_status_dict()
    assert status["status"] == IngestionPhase.STARTING.value
    assert status["message"] == "test ingestion"
    assert "recent_messages" in status


def test_build_startup_settings_from_config(tmp_path):
    from terraform_ingest.mcp_service import _build_startup_settings
    from terraform_ingest.models import IngestConfig, McpConfig, RepositoryConfig

    config = IngestConfig(
        repositories=[RepositoryConfig(url="https://example.com/repo.git")],
        mcp=McpConfig(
            ingest_on_startup=True,
            blocking_ingest_on_startup=True,
            notify_ingestion_progress=False,
        ),
    )

    settings = _build_startup_settings("config.yaml", config, True)
    assert settings.ingest_on_startup is True
    assert settings.blocking_ingest_on_startup is True
    assert settings.notify_ingestion_progress is False


def test_set_startup_settings_round_trip():
    settings = McpStartupSettings(
        config_file="config.yaml",
        ingest_config=None,
        ingest_on_startup=True,
    )
    set_startup_settings(settings)

    from terraform_ingest.mcp_ingestion import get_startup_settings

    assert get_startup_settings() == settings
    set_startup_settings(None)
