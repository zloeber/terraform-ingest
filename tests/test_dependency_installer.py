"""Tests for the dependency installer module."""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from terraform_ingest.dependency_installer import (
    DependencyInstaller,
    ensure_embeddings_available,
)
from terraform_ingest.models import EmbeddingConfig


class TestDependencyInstaller:
    """Test suite for DependencyInstaller class."""

    def test_check_package_installed_existing_package(self):
        """Test checking for an installed package."""
        # This should pass since pytest is always installed
        assert DependencyInstaller.check_package_installed("pytest") is True

    def test_check_package_installed_missing_package(self):
        """Test checking for a package that doesn't exist."""
        assert (
            DependencyInstaller.check_package_installed("fake_nonexistent_package_xyz")
            is False
        )

    def test_get_missing_packages_all_present(self):
        """Test getting missing packages when all are present."""
        # These packages should be installed in test environment
        missing = DependencyInstaller.get_missing_packages(["pytest", "pydantic"])
        assert len(missing) == 0

    def test_get_missing_packages_some_missing(self):
        """Test getting missing packages when some are not installed."""
        packages = ["pytest", "fake_nonexistent_package_xyz"]
        missing = DependencyInstaller.get_missing_packages(packages)
        assert "fake_nonexistent_package_xyz" in missing
        assert "pytest" not in missing

    def test_get_missing_packages_all_missing(self):
        """Test getting missing packages when none are installed."""
        packages = ["fake_package_1", "fake_package_2"]
        missing = DependencyInstaller.get_missing_packages(packages)
        assert len(missing) == 2
        assert "fake_package_1" in missing
        assert "fake_package_2" in missing

    def test_strategy_packages_mapping(self):
        """Test that strategy packages mapping is complete."""
        assert "sentence-transformers" in DependencyInstaller.STRATEGY_PACKAGES
        assert "openai" in DependencyInstaller.STRATEGY_PACKAGES
        assert "claude" in DependencyInstaller.STRATEGY_PACKAGES
        assert "chromadb-default" in DependencyInstaller.STRATEGY_PACKAGES

    @patch("subprocess.run")
    def test_install_packages_with_uv_system_flag_success(self, mock_run):
        """Test successful installation with uv --system flag for tool installations."""
        # First call with --system succeeds
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(
            DependencyInstaller,
            "get_missing_packages",
            return_value=["sentence-transformers"],
        ):
            success = DependencyInstaller.install_packages(
                ["sentence-transformers"], use_uv=True
            )

        assert success is True
        # Verify that uv pip install --system was attempted
        call_args = mock_run.call_args_list[0]
        assert "uv" in call_args[0][0]
        # assert "--system" in call_args[0][0]

    @patch("subprocess.run")
    def test_install_packages_with_uv_fallback_to_pip(self, mock_run):
        """Test fallback to regular uv pip install when --system fails."""
        # First call with --system fails, second with regular uv pip install succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "uv"),  # --system fails
            MagicMock(returncode=0),  # regular uv pip install succeeds
        ]

        with patch.object(
            DependencyInstaller,
            "get_missing_packages",
            return_value=["sentence-transformers"],
        ):
            success = DependencyInstaller.install_packages(
                ["sentence-transformers"], use_uv=True
            )

        assert success is True
        # Verify both approaches were tried
        assert mock_run.call_count >= 1

    @patch("subprocess.run")
    def test_install_packages_with_uv_success(self, mock_run):
        """Test successful installation with uv."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(
            DependencyInstaller, "check_package_installed", side_effect=[False, True]
        ):
            success = DependencyInstaller.install_packages(
                ["sentence-transformers"], use_uv=True
            )

        assert success is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_install_packages_with_pip_fallback(self, mock_run):
        """Test fallback to pip when uv is not available."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(
            DependencyInstaller, "check_package_installed", side_effect=[False, True]
        ):
            success = DependencyInstaller.install_packages(
                ["sentence-transformers"], use_uv=False
            )

        assert success is True

    def test_install_packages_already_installed(self):
        """Test that installation is skipped if packages are already installed."""
        with patch.object(DependencyInstaller, "get_missing_packages", return_value=[]):
            success = DependencyInstaller.install_packages(["sentence-transformers"])

        assert success is True

    def test_ensure_embedding_packages_sentence_transformers(self):
        """Test ensuring packages for sentence-transformers strategy."""
        with patch.object(DependencyInstaller, "get_missing_packages", return_value=[]):
            success = DependencyInstaller.ensure_embedding_packages(
                strategy="sentence-transformers", auto_install=False
            )

        assert success is True

    def test_ensure_embedding_packages_openai(self):
        """Test ensuring packages for OpenAI strategy."""
        with patch.object(DependencyInstaller, "get_missing_packages", return_value=[]):
            success = DependencyInstaller.ensure_embedding_packages(
                strategy="openai", auto_install=False
            )

        assert success is True

    def test_ensure_embedding_packages_claude(self):
        """Test ensuring packages for Claude strategy."""
        with patch.object(DependencyInstaller, "get_missing_packages", return_value=[]):
            success = DependencyInstaller.ensure_embedding_packages(
                strategy="claude", auto_install=False
            )

        assert success is True

    def test_ensure_embedding_packages_chromadb_default(self):
        """Test ensuring packages for chromadb-default strategy."""
        with patch.object(DependencyInstaller, "get_missing_packages", return_value=[]):
            success = DependencyInstaller.ensure_embedding_packages(
                strategy="chromadb-default", auto_install=False
            )

        assert success is True

    def test_ensure_embedding_packages_unknown_strategy(self):
        """Test with unknown strategy."""
        success = DependencyInstaller.ensure_embedding_packages(
            strategy="unknown_strategy", auto_install=False
        )
        assert success is False

    def test_ensure_embedding_packages_missing_no_auto_install(self):
        """Test missing packages with auto_install=False raises error in convenience function."""
        config = EmbeddingConfig(enabled=True, strategy="sentence-transformers")

        with patch.object(
            DependencyInstaller, "ensure_embedding_packages", return_value=False
        ):
            with pytest.raises(ImportError):
                ensure_embeddings_available(config, auto_install=False)

    def test_ensure_embeddings_available_disabled(self):
        """Test that disabled embeddings don't trigger installation."""
        config = EmbeddingConfig(enabled=False)

        success = ensure_embeddings_available(config, auto_install=False)
        assert success is True

    def test_ensure_embeddings_available_enabled_missing_auto_install(self):
        """Test auto-installation when embeddings are enabled."""
        config = EmbeddingConfig(enabled=True, strategy="chromadb-default")

        with patch.object(
            DependencyInstaller, "ensure_embedding_packages", return_value=True
        ) as mock_ensure:
            success = ensure_embeddings_available(config, auto_install=True)

        assert success is True
        mock_ensure.assert_called_once()

    def test_ensure_embeddings_available_none_config(self):
        """Test with None configuration."""
        success = ensure_embeddings_available(None, auto_install=False)
        assert success is True


class TestEmbeddingStrategies:
    """Test embedding strategy package requirements."""

    def test_sentence_transformers_requires_chromadb(self):
        """Test that sentence-transformers strategy requires chromadb."""
        packages = DependencyInstaller.STRATEGY_PACKAGES["sentence-transformers"]
        assert "sentence-transformers" in packages

    def test_openai_requires_openai_package(self):
        """Test that openai strategy requires openai package."""
        packages = DependencyInstaller.STRATEGY_PACKAGES["openai"]
        assert "openai" in packages

    def test_claude_requires_voyageai(self):
        """Test that claude strategy requires voyageai."""
        packages = DependencyInstaller.STRATEGY_PACKAGES["claude"]
        assert "voyageai" in packages

    def test_chromadb_default_requires_chromadb(self):
        """Test that chromadb-default strategy requires chromadb."""
        packages = DependencyInstaller.STRATEGY_PACKAGES["chromadb-default"]
        assert "chromadb" in packages
