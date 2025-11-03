"""Tests for CLI config commands."""

import pytest
import yaml
from click.testing import CliRunner
from terraform_ingest.cli import cli


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_config(tmp_path):
    """Create a sample configuration file."""
    config_path = tmp_path / "test-config.yaml"
    config_data = {
        "repositories": [
            {
                "url": "https://github.com/test-org/repo1.git",
                "name": "repo1",
                "branches": ["main"],
                "include_tags": True,
                "max_tags": 1,
                "path": ".",
                "recursive": False,
                "exclude_paths": [],
            }
        ],
        "output_dir": "./output",
        "clone_dir": "./repos",
        "embedding": {
            "enabled": False,
            "strategy": "chromadb-default",
        },
        "mcp": {
            "port": 3000,
            "auto_ingest": False,
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)

    return config_path


class TestConfigCommand:
    """Tests for config command group."""

    def test_config_help(self, runner):
        """Test config command help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage configuration file settings" in result.output

    def test_set_subcommand_help(self, runner):
        """Test set subcommand help."""
        result = runner.invoke(cli, ["config", "set", "--help"])
        assert result.exit_code == 0
        assert "Set a configuration value" in result.output
        assert "--target" in result.output
        assert "--value" in result.output

    def test_get_subcommand_help(self, runner):
        """Test get subcommand help."""
        result = runner.invoke(cli, ["config", "get", "--help"])
        assert result.exit_code == 0
        assert "Get a configuration value" in result.output
        assert "--target" in result.output

    def test_add_repo_subcommand_help(self, runner):
        """Test add-repo subcommand help."""
        result = runner.invoke(cli, ["config", "add-repo", "--help"])
        assert result.exit_code == 0
        assert "Add a repository to the configuration" in result.output
        assert "--url" in result.output

    def test_remove_repo_subcommand_help(self, runner):
        """Test remove-repo subcommand help."""
        result = runner.invoke(cli, ["config", "remove-repo", "--help"])
        assert result.exit_code == 0
        assert "Remove a repository from the configuration" in result.output
        assert "--url" in result.output


class TestConfigSet:
    """Tests for config set command."""

    def test_set_simple_value(self, runner, sample_config):
        """Test setting a simple configuration value."""
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(sample_config),
                "--target",
                "output_dir",
                "--value",
                "./new-output",
            ],
        )
        assert result.exit_code == 0
        assert "Set output_dir = ./new-output" in result.output

        # Verify the value was set
        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert config["output_dir"] == "./new-output"

    def test_set_nested_value(self, runner, sample_config):
        """Test setting a nested configuration value."""
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(sample_config),
                "--target",
                "embedding.enabled",
                "--value",
                "true",
            ],
        )
        assert result.exit_code == 0
        assert "Set embedding.enabled = True" in result.output

        # Verify the value was set
        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert config["embedding"]["enabled"] is True

    def test_set_boolean_true(self, runner, sample_config):
        """Test setting a boolean value (true)."""
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(sample_config),
                "--target",
                "mcp.auto_ingest",
                "--value",
                "true",
            ],
        )
        assert result.exit_code == 0

        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert config["mcp"]["auto_ingest"] is True

    def test_set_boolean_false(self, runner, sample_config):
        """Test setting a boolean value (false)."""
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(sample_config),
                "--target",
                "mcp.auto_ingest",
                "--value",
                "false",
            ],
        )
        assert result.exit_code == 0

        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert config["mcp"]["auto_ingest"] is False

    def test_set_integer_value(self, runner, sample_config):
        """Test setting an integer value."""
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(sample_config),
                "--target",
                "mcp.port",
                "--value",
                "8080",
            ],
        )
        assert result.exit_code == 0
        assert "Set mcp.port = 8080" in result.output

        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert config["mcp"]["port"] == 8080

    def test_set_string_value(self, runner, sample_config):
        """Test setting a string value."""
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(sample_config),
                "--target",
                "embedding.strategy",
                "--value",
                "openai",
            ],
        )
        assert result.exit_code == 0

        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert config["embedding"]["strategy"] == "openai"

    def test_set_creates_nested_path(self, runner, sample_config):
        """Test that set creates nested paths if they don't exist."""
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(sample_config),
                "--target",
                "new.nested.value",
                "--value",
                "test",
            ],
        )
        assert result.exit_code == 0

        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert config["new"]["nested"]["value"] == "test"

    def test_set_nonexistent_config_file(self, runner, tmp_path):
        """Test setting value in nonexistent config file."""
        config_path = tmp_path / "nonexistent.yaml"
        result = runner.invoke(
            cli,
            [
                "config",
                "set",
                "--config",
                str(config_path),
                "--target",
                "test",
                "--value",
                "value",
            ],
        )
        assert result.exit_code != 0
        assert "Configuration file not found" in result.output


class TestConfigGet:
    """Tests for config get command."""

    def test_get_simple_value(self, runner, sample_config):
        """Test getting a simple configuration value."""
        result = runner.invoke(
            cli,
            ["config", "get", "--config", str(sample_config), "--target", "output_dir"],
        )
        assert result.exit_code == 0
        assert "./output" in result.output

    def test_get_nested_value(self, runner, sample_config):
        """Test getting a nested configuration value."""
        result = runner.invoke(
            cli,
            [
                "config",
                "get",
                "--config",
                str(sample_config),
                "--target",
                "embedding.enabled",
            ],
        )
        assert result.exit_code == 0
        assert "False" in result.output or "false" in result.output

    def test_get_boolean_value(self, runner, sample_config):
        """Test getting a boolean value."""
        result = runner.invoke(
            cli,
            [
                "config",
                "get",
                "--config",
                str(sample_config),
                "--target",
                "mcp.auto_ingest",
            ],
        )
        assert result.exit_code == 0
        assert "False" in result.output or "false" in result.output

    def test_get_integer_value(self, runner, sample_config):
        """Test getting an integer value."""
        result = runner.invoke(
            cli,
            ["config", "get", "--config", str(sample_config), "--target", "mcp.port"],
        )
        assert result.exit_code == 0
        assert "3000" in result.output

    def test_get_object_as_yaml(self, runner, sample_config):
        """Test getting an object outputs YAML."""
        result = runner.invoke(
            cli,
            ["config", "get", "--config", str(sample_config), "--target", "embedding"],
        )
        assert result.exit_code == 0
        assert "enabled:" in result.output
        assert "strategy:" in result.output

    def test_get_object_as_json(self, runner, sample_config):
        """Test getting an object with JSON output."""
        result = runner.invoke(
            cli,
            [
                "config",
                "get",
                "--config",
                str(sample_config),
                "--target",
                "embedding",
                "--json",
            ],
        )
        assert result.exit_code == 0
        assert '"enabled"' in result.output
        assert '"strategy"' in result.output

    def test_get_nonexistent_key(self, runner, sample_config):
        """Test getting a nonexistent key."""
        result = runner.invoke(
            cli,
            [
                "config",
                "get",
                "--config",
                str(sample_config),
                "--target",
                "nonexistent",
            ],
        )
        assert result.exit_code != 0
        assert "Configuration key not found" in result.output

    def test_get_entire_config_as_yaml(self, runner, sample_config):
        """Test getting entire configuration without target (YAML output)."""
        result = runner.invoke(
            cli,
            ["config", "get", "--config", str(sample_config)],
        )
        assert result.exit_code == 0
        # Check that entire config is shown
        assert "repositories:" in result.output
        assert "output_dir:" in result.output
        assert "clone_dir:" in result.output
        assert "embedding:" in result.output
        assert "mcp:" in result.output

    def test_get_entire_config_as_json(self, runner, sample_config):
        """Test getting entire configuration without target (JSON output)."""
        result = runner.invoke(
            cli,
            ["config", "get", "--config", str(sample_config), "--json"],
        )
        assert result.exit_code == 0
        # Check that entire config is shown as JSON
        assert '"repositories"' in result.output
        assert '"output_dir"' in result.output
        assert '"clone_dir"' in result.output
        assert '"embedding"' in result.output
        assert '"mcp"' in result.output


class TestConfigAddRepo:
    """Tests for config add-repo command."""

    def test_add_repo_basic(self, runner, sample_config):
        """Test adding a basic repository."""
        result = runner.invoke(
            cli,
            [
                "config",
                "add-repo",
                "--config",
                str(sample_config),
                "--url",
                "https://github.com/test-org/repo2.git",
            ],
        )
        assert result.exit_code == 0
        assert (
            "Added repository: https://github.com/test-org/repo2.git" in result.output
        )

        # Verify repository was added
        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert len(config["repositories"]) == 2
        assert (
            config["repositories"][1]["url"] == "https://github.com/test-org/repo2.git"
        )

    def test_add_repo_with_options(self, runner, sample_config):
        """Test adding a repository with various options."""
        result = runner.invoke(
            cli,
            [
                "config",
                "add-repo",
                "--config",
                str(sample_config),
                "--url",
                "https://github.com/test-org/repo2.git",
                "--name",
                "repo2",
                "--branches",
                "main,develop",
                "--max-tags",
                "5",
                "--recursive",
                "--path",
                "./modules",
            ],
        )
        assert result.exit_code == 0
        assert "Added repository" in result.output

        # Verify repository was added with options
        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        new_repo = config["repositories"][1]
        assert new_repo["url"] == "https://github.com/test-org/repo2.git"
        assert new_repo["name"] == "repo2"
        assert new_repo["branches"] == ["main", "develop"]
        assert new_repo["max_tags"] == 5
        assert new_repo["recursive"] is True
        assert new_repo["path"] == "./modules"

    def test_add_repo_duplicate_url(self, runner, sample_config):
        """Test adding a repository with duplicate URL."""
        result = runner.invoke(
            cli,
            [
                "config",
                "add-repo",
                "--config",
                str(sample_config),
                "--url",
                "https://github.com/test-org/repo1.git",
            ],
        )
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_add_repo_no_include_tags(self, runner, sample_config):
        """Test adding a repository with tags disabled."""
        result = runner.invoke(
            cli,
            [
                "config",
                "add-repo",
                "--config",
                str(sample_config),
                "--url",
                "https://github.com/test-org/repo2.git",
                "--no-include-tags",
            ],
        )
        assert result.exit_code == 0

        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        new_repo = config["repositories"][1]
        assert new_repo["include_tags"] is False

    def test_add_repo_nonexistent_config_file(self, runner, tmp_path):
        """Test adding repo to nonexistent config file."""
        config_path = tmp_path / "nonexistent.yaml"
        result = runner.invoke(
            cli,
            [
                "config",
                "add-repo",
                "--config",
                str(config_path),
                "--url",
                "https://github.com/test-org/repo.git",
            ],
        )
        assert result.exit_code != 0
        assert "Configuration file not found" in result.output


class TestConfigRemoveRepo:
    """Tests for config remove-repo command."""

    def test_remove_repo_by_url(self, runner, sample_config):
        """Test removing a repository by URL."""
        result = runner.invoke(
            cli,
            [
                "config",
                "remove-repo",
                "--config",
                str(sample_config),
                "--url",
                "https://github.com/test-org/repo1.git",
            ],
        )
        assert result.exit_code == 0
        assert "Removed repository" in result.output

        # Verify repository was removed
        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert len(config["repositories"]) == 0

    def test_remove_repo_by_name(self, runner, sample_config):
        """Test removing a repository by name."""
        result = runner.invoke(
            cli,
            [
                "config",
                "remove-repo",
                "--config",
                str(sample_config),
                "--name",
                "repo1",
            ],
        )
        assert result.exit_code == 0
        assert "Removed repository" in result.output

        # Verify repository was removed
        with open(sample_config, "r") as f:
            config = yaml.safe_load(f)
        assert len(config["repositories"]) == 0

    def test_remove_repo_nonexistent_url(self, runner, sample_config):
        """Test removing a repository with nonexistent URL."""
        result = runner.invoke(
            cli,
            [
                "config",
                "remove-repo",
                "--config",
                str(sample_config),
                "--url",
                "https://github.com/test-org/nonexistent.git",
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_remove_repo_nonexistent_name(self, runner, sample_config):
        """Test removing a repository with nonexistent name."""
        result = runner.invoke(
            cli,
            [
                "config",
                "remove-repo",
                "--config",
                str(sample_config),
                "--name",
                "nonexistent",
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_remove_repo_no_identifier(self, runner, sample_config):
        """Test removing repository without URL or name."""
        result = runner.invoke(
            cli,
            ["config", "remove-repo", "--config", str(sample_config)],
        )
        assert result.exit_code != 0
        assert "Must specify either --url or --name" in result.output

    def test_remove_repo_from_empty_config(self, runner, tmp_path):
        """Test removing repository from config with no repositories."""
        config_path = tmp_path / "empty-config.yaml"
        config_data = {"repositories": [], "output_dir": "./output"}
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        result = runner.invoke(
            cli,
            [
                "config",
                "remove-repo",
                "--config",
                str(config_path),
                "--url",
                "https://github.com/test/repo.git",
            ],
        )
        # Should not error but inform user
        assert "No repositories found" in result.output or "not found" in result.output
