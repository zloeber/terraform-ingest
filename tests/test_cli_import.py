"""Tests for CLI import commands."""

import pytest
import yaml
from click.testing import CliRunner
from unittest.mock import patch, Mock
from terraform_ingest.cli import cli
from terraform_ingest.models import RepositoryConfig


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_github_repos():
    """Mock list of GitHub repositories."""
    return [
        RepositoryConfig(
            url="https://github.com/test-org/repo1.git",
            name="repo1",
            branches=[],
            include_tags=True,
            max_tags=1,
            path="./src",
            recursive=False,
            exclude_paths=[],
        ),
        RepositoryConfig(
            url="https://github.com/test-org/repo2.git",
            name="repo2",
            branches=[],
            include_tags=True,
            max_tags=1,
            path="./src",
            recursive=False,
            exclude_paths=[],
        ),
    ]


class TestImportCommand:
    """Tests for import command group."""

    def test_import_help(self, runner):
        """Test import command help."""
        result = runner.invoke(cli, ["import", "--help"])
        assert result.exit_code == 0
        assert "Import repositories from external sources" in result.output

    def test_github_subcommand_help(self, runner):
        """Test github subcommand help."""
        result = runner.invoke(cli, ["import", "github", "--help"])
        assert result.exit_code == 0
        assert "Import repositories from a GitHub organization" in result.output
        assert "--org" in result.output
        assert "--token" in result.output
        assert "--replace" in result.output

    def test_gitlab_subcommand_help(self, runner):
        """Test gitlab subcommand help."""
        result = runner.invoke(cli, ["import", "gitlab", "--help"])
        assert result.exit_code == 0
        assert "Import repositories from a GitLab group" in result.output
        assert "--group" in result.output
        assert "--token" in result.output
        assert "--replace" in result.output
        assert "--recursive" in result.output


class TestGitHubImportCommand:
    """Tests for github import subcommand."""

    @patch("terraform_ingest.cli.GitHubImporter")
    def test_github_import_basic(
        self, mock_importer_class, runner, tmp_path, mock_github_repos
    ):
        """Test basic GitHub import."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_github_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "github",
                "--org",
                "test-org",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert "Merged 2 repositories" in result.output
        assert config_file.exists()

        # Verify the config file was created correctly
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        assert len(config["repositories"]) == 2
        assert config["repositories"][0]["name"] == "repo1"

    @patch("terraform_ingest.cli.GitHubImporter")
    def test_github_import_with_token(
        self, mock_importer_class, runner, tmp_path, mock_github_repos
    ):
        """Test GitHub import with authentication token."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_github_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "github",
                "--org",
                "test-org",
                "--token",
                "test-token",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        # Verify importer was initialized with token
        mock_importer_class.assert_called_once()
        call_kwargs = mock_importer_class.call_args[1]
        assert call_kwargs["token"] == "test-token"

    @patch("terraform_ingest.cli.GitHubImporter")
    def test_github_import_merge(
        self, mock_importer_class, runner, tmp_path, mock_github_repos
    ):
        """Test GitHub import with merge (default behavior)."""
        config_file = tmp_path / "test-config.yaml"

        # Create initial config with one repository
        initial_config = {
            "repositories": [
                {
                    "url": "https://github.com/existing/repo.git",
                    "name": "existing-repo",
                    "branches": ["main"],
                    "include_tags": True,
                    "max_tags": 10,
                    "path": ".",
                    "recursive": False,
                    "exclude_paths": [],
                }
            ],
            "output_dir": "./output",
            "clone_dir": "./repos",
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_github_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "github",
                "--org",
                "test-org",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert "Merged" in result.output

        # Verify repositories were merged
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Should have 3 repos: 1 existing + 2 new
        assert len(config["repositories"]) == 3

    @patch("terraform_ingest.cli.GitHubImporter")
    def test_github_import_replace(
        self, mock_importer_class, runner, tmp_path, mock_github_repos
    ):
        """Test GitHub import with replace flag."""
        config_file = tmp_path / "test-config.yaml"

        # Create initial config with one repository
        initial_config = {
            "repositories": [
                {
                    "url": "https://github.com/existing/repo.git",
                    "name": "existing-repo",
                    "branches": ["main"],
                    "include_tags": True,
                    "max_tags": 10,
                    "path": ".",
                    "recursive": False,
                    "exclude_paths": [],
                }
            ],
            "output_dir": "./output",
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_github_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "github",
                "--org",
                "test-org",
                "--config",
                str(config_file),
                "--replace",
            ],
        )

        assert result.exit_code == 0
        assert "Replaced 2 repositories" in result.output

        # Verify repositories were replaced
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Should have only 2 new repos
        assert len(config["repositories"]) == 2
        assert config["repositories"][0]["name"] == "repo1"

    @patch("terraform_ingest.cli.GitHubImporter")
    def test_github_import_with_options(
        self, mock_importer_class, runner, tmp_path, mock_github_repos
    ):
        """Test GitHub import with various options."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_github_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "github",
                "--org",
                "test-org",
                "--config",
                str(config_file),
                "--include-private",
                "--terraform-only",
                "--base-path",
                "/custom/path",
            ],
        )

        assert result.exit_code == 0

        # Verify importer was initialized with correct options
        mock_importer_class.assert_called_once()
        call_kwargs = mock_importer_class.call_args[1]
        assert call_kwargs["org"] == "test-org"
        assert call_kwargs["include_private"] is True
        assert call_kwargs["terraform_only"] is True
        assert call_kwargs["base_path"] == "/custom/path"

    @patch("terraform_ingest.cli.GitHubImporter")
    def test_github_import_no_repos(self, mock_importer_class, runner, tmp_path):
        """Test GitHub import when no repositories are found."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer to return empty list
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = []
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "github",
                "--org",
                "test-org",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert "No repositories found" in result.output

    def test_github_import_missing_org(self, runner):
        """Test GitHub import without required --org option."""
        result = runner.invoke(
            cli,
            ["import", "github"],
        )

        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output


@pytest.fixture
def mock_gitlab_repos():
    """Mock list of GitLab repositories."""
    return [
        RepositoryConfig(
            url="https://gitlab.com/test-group/repo1.git",
            name="repo1",
            branches=[],
            include_tags=True,
            max_tags=1,
            path=".",
            recursive=False,
            exclude_paths=[],
        ),
        RepositoryConfig(
            url="https://gitlab.com/test-group/repo2.git",
            name="repo2",
            branches=[],
            include_tags=True,
            max_tags=1,
            path=".",
            recursive=False,
            exclude_paths=[],
        ),
    ]


class TestGitLabImportCommand:
    """Tests for gitlab import subcommand."""

    @patch("terraform_ingest.cli.GitLabImporter")
    def test_gitlab_import_basic(
        self, mock_importer_class, runner, tmp_path, mock_gitlab_repos
    ):
        """Test basic GitLab import."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_gitlab_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "gitlab",
                "--group",
                "test-group",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert "Merged 2 repositories" in result.output
        assert config_file.exists()

        # Verify the config file was created correctly
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        assert len(config["repositories"]) == 2
        assert config["repositories"][0]["name"] == "repo1"

    @patch("terraform_ingest.cli.GitLabImporter")
    def test_gitlab_import_with_token(
        self, mock_importer_class, runner, tmp_path, mock_gitlab_repos
    ):
        """Test GitLab import with authentication token."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_gitlab_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "gitlab",
                "--group",
                "test-group",
                "--token",
                "test-token",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        # Verify importer was initialized with token
        mock_importer_class.assert_called_once()
        call_kwargs = mock_importer_class.call_args[1]
        assert call_kwargs["token"] == "test-token"

    @patch("terraform_ingest.cli.GitLabImporter")
    def test_gitlab_import_merge(
        self, mock_importer_class, runner, tmp_path, mock_gitlab_repos
    ):
        """Test GitLab import with merge (default behavior)."""
        config_file = tmp_path / "test-config.yaml"

        # Create initial config with one repository
        initial_config = {
            "repositories": [
                {
                    "url": "https://gitlab.com/existing/repo.git",
                    "name": "existing-repo",
                    "branches": ["main"],
                    "include_tags": True,
                    "max_tags": 10,
                    "path": ".",
                    "recursive": False,
                    "exclude_paths": [],
                }
            ],
            "output_dir": "./output",
            "clone_dir": "./repos",
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_gitlab_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "gitlab",
                "--group",
                "test-group",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert "Merged" in result.output

        # Verify repositories were merged
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Should have 3 repos: 1 existing + 2 new
        assert len(config["repositories"]) == 3

    @patch("terraform_ingest.cli.GitLabImporter")
    def test_gitlab_import_replace(
        self, mock_importer_class, runner, tmp_path, mock_gitlab_repos
    ):
        """Test GitLab import with replace flag."""
        config_file = tmp_path / "test-config.yaml"

        # Create initial config with one repository
        initial_config = {
            "repositories": [
                {
                    "url": "https://gitlab.com/existing/repo.git",
                    "name": "existing-repo",
                    "branches": ["main"],
                    "include_tags": True,
                    "max_tags": 10,
                    "path": ".",
                    "recursive": False,
                    "exclude_paths": [],
                }
            ],
            "output_dir": "./output",
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_gitlab_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "gitlab",
                "--group",
                "test-group",
                "--config",
                str(config_file),
                "--replace",
            ],
        )

        assert result.exit_code == 0
        assert "Replaced 2 repositories" in result.output

        # Verify repositories were replaced
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Should have only 2 new repos
        assert len(config["repositories"]) == 2
        assert config["repositories"][0]["name"] == "repo1"

    @patch("terraform_ingest.cli.GitLabImporter")
    def test_gitlab_import_with_options(
        self, mock_importer_class, runner, tmp_path, mock_gitlab_repos
    ):
        """Test GitLab import with various options."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_gitlab_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "gitlab",
                "--group",
                "test-group",
                "--config",
                str(config_file),
                "--include-private",
                "--terraform-only",
                "--base-path",
                "/custom/path",
                "--recursive",
                "--gitlab-url",
                "https://gitlab.example.com",
            ],
        )

        assert result.exit_code == 0

        # Verify importer was initialized with correct options
        mock_importer_class.assert_called_once()
        call_kwargs = mock_importer_class.call_args[1]
        assert call_kwargs["group"] == "test-group"
        assert call_kwargs["include_private"] is True
        assert call_kwargs["terraform_only"] is True
        assert call_kwargs["base_path"] == "/custom/path"
        assert call_kwargs["recursive"] is True
        assert call_kwargs["gitlab_url"] == "https://gitlab.example.com"

    @patch("terraform_ingest.cli.GitLabImporter")
    def test_gitlab_import_no_repos(self, mock_importer_class, runner, tmp_path):
        """Test GitLab import when no repositories are found."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer to return empty list
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = []
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "gitlab",
                "--group",
                "test-group",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert "No repositories found" in result.output

    def test_gitlab_import_missing_group(self, runner):
        """Test GitLab import without required --group option."""
        result = runner.invoke(
            cli,
            ["import", "gitlab"],
        )

        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

    @patch("terraform_ingest.cli.GitLabImporter")
    def test_gitlab_import_with_branches_and_tags(
        self, mock_importer_class, runner, tmp_path, mock_gitlab_repos
    ):
        """Test GitLab import with branches and max_tags options."""
        config_file = tmp_path / "test-config.yaml"

        # Mock the importer
        mock_importer = Mock()
        mock_importer.fetch_repositories.return_value = mock_gitlab_repos
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            cli,
            [
                "import",
                "gitlab",
                "--group",
                "test-group",
                "--config",
                str(config_file),
                "--branches",
                "main,develop,staging",
                "--max-tags",
                "5",
            ],
        )

        assert result.exit_code == 0
        assert "Merged 2 repositories" in result.output

        # Verify the config file has the correct branches and max_tags
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        assert len(config["repositories"]) == 2
        assert config["repositories"][0]["branches"] == ["main", "develop", "staging"]
        assert config["repositories"][0]["max_tags"] == 5
