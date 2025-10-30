"""Tests for repository importers."""

import pytest
import yaml
from unittest.mock import Mock, patch
from terraform_ingest.importers import (
    GitHubImporter,
    merge_repositories,
    update_config_file,
)
from terraform_ingest.models import RepositoryConfig


@pytest.fixture
def mock_github_response():
    """Mock GitHub API response for repositories."""
    return [
        {
            "name": "terraform-aws-vpc",
            "full_name": "test-org/terraform-aws-vpc",
            "clone_url": "https://github.com/test-org/terraform-aws-vpc.git",
            "default_branch": "main",
            "private": False,
            "archived": False,
            "description": "AWS VPC module",
        },
        {
            "name": "terraform-aws-ec2",
            "full_name": "test-org/terraform-aws-ec2",
            "clone_url": "https://github.com/test-org/terraform-aws-ec2.git",
            "default_branch": "main",
            "private": False,
            "archived": False,
            "description": "AWS EC2 module",
        },
        {
            "name": "archived-repo",
            "full_name": "test-org/archived-repo",
            "clone_url": "https://github.com/test-org/archived-repo.git",
            "default_branch": "main",
            "private": False,
            "archived": True,
            "description": "Archived repository",
        },
    ]


class TestGitHubImporter:
    """Tests for GitHubImporter class."""

    def test_init(self):
        """Test GitHubImporter initialization."""
        importer = GitHubImporter(
            org="test-org",
            token="test-token",
            include_private=True,
            terraform_only=True,
            base_path="/custom/path",
        )

        assert importer.org == "test-org"
        assert importer.token == "test-token"
        assert importer.include_private is True
        assert importer.terraform_only is True
        assert importer.base_path == "/custom/path"
        assert importer.headers["Authorization"] == "token test-token"

    def test_init_without_token(self):
        """Test GitHubImporter initialization without token."""
        importer = GitHubImporter(org="test-org")

        assert importer.org == "test-org"
        assert importer.token is None
        assert importer.headers == {}

    def test_get_provider_name(self):
        """Test get_provider_name method."""
        importer = GitHubImporter(org="test-org")
        assert importer.get_provider_name() == "github"

    @patch("terraform_ingest.importers.requests.get")
    def test_fetch_repositories(self, mock_get, mock_github_response):
        """Test fetching repositories from GitHub."""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            mock_github_response,  # First page
            [],  # Second page (empty to stop pagination)
        ]
        mock_get.return_value = mock_response

        importer = GitHubImporter(org="test-org", terraform_only=False)
        repos = importer.fetch_repositories()

        # Should skip archived repo
        assert len(repos) == 2
        assert all(isinstance(repo, RepositoryConfig) for repo in repos)
        assert repos[0].name == "terraform-aws-vpc"
        assert repos[0].url == "https://github.com/test-org/terraform-aws-vpc.git"
        assert repos[1].name == "terraform-aws-ec2"

    @patch("terraform_ingest.importers.requests.get")
    def test_fetch_repositories_with_error(self, mock_get):
        """Test error handling when fetching repositories."""
        mock_get.side_effect = Exception("Network error")

        importer = GitHubImporter(org="test-org")

        with pytest.raises(Exception):
            importer.fetch_repositories()

    @patch("terraform_ingest.importers.requests.get")
    def test_has_terraform_files_found(self, mock_get):
        """Test _has_terraform_files when Terraform files are found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_count": 5}
        mock_get.return_value = mock_response

        importer = GitHubImporter(org="test-org")
        repo = {"full_name": "test-org/terraform-repo"}

        assert importer._has_terraform_files(repo) is True

    @patch("terraform_ingest.importers.requests.get")
    def test_has_terraform_files_not_found(self, mock_get):
        """Test _has_terraform_files when no Terraform files are found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_count": 0}
        mock_get.return_value = mock_response

        importer = GitHubImporter(org="test-org")
        repo = {"full_name": "test-org/non-terraform-repo"}

        assert importer._has_terraform_files(repo) is False

    @patch("terraform_ingest.importers.requests.get")
    def test_has_terraform_files_rate_limited(self, mock_get):
        """Test _has_terraform_files when rate limited."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1234567890",
        }
        mock_get.return_value = mock_response

        importer = GitHubImporter(org="test-org")
        repo = {"full_name": "test-org/some-repo"}

        # Should return True by default when rate limited
        assert importer._has_terraform_files(repo) is True


class TestMergeRepositories:
    """Tests for merge_repositories function."""

    def test_merge_repositories_replace(self):
        """Test merging repositories with replace=True."""
        existing = [
            RepositoryConfig(url="https://github.com/org/repo1.git", name="repo1"),
            RepositoryConfig(url="https://github.com/org/repo2.git", name="repo2"),
        ]
        new = [
            RepositoryConfig(url="https://github.com/org/repo3.git", name="repo3"),
        ]

        result = merge_repositories(existing, new, replace=True)

        assert len(result) == 1
        assert result[0].name == "repo3"

    def test_merge_repositories_merge(self):
        """Test merging repositories with replace=False."""
        existing = [
            RepositoryConfig(url="https://github.com/org/repo1.git", name="repo1"),
            RepositoryConfig(url="https://github.com/org/repo2.git", name="repo2"),
        ]
        new = [
            RepositoryConfig(url="https://github.com/org/repo3.git", name="repo3"),
            RepositoryConfig(
                url="https://github.com/org/repo1.git", name="repo1"
            ),  # Duplicate
        ]

        result = merge_repositories(existing, new, replace=False)

        # Should have repo1, repo2, and repo3 (no duplicates)
        assert len(result) == 3
        urls = [repo.url for repo in result]
        assert "https://github.com/org/repo1.git" in urls
        assert "https://github.com/org/repo2.git" in urls
        assert "https://github.com/org/repo3.git" in urls

    def test_merge_repositories_empty_existing(self):
        """Test merging when existing list is empty."""
        existing = []
        new = [
            RepositoryConfig(url="https://github.com/org/repo1.git", name="repo1"),
        ]

        result = merge_repositories(existing, new, replace=False)

        assert len(result) == 1
        assert result[0].name == "repo1"


class TestUpdateConfigFile:
    """Tests for update_config_file function."""

    def test_update_config_file_new_file(self, tmp_path):
        """Test updating a non-existent config file."""
        config_path = tmp_path / "config.yaml"
        new_repos = [
            RepositoryConfig(url="https://github.com/org/repo1.git", name="repo1"),
        ]

        update_config_file(config_path, new_repos, replace=False)

        assert config_path.exists()

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        assert "repositories" in config
        assert len(config["repositories"]) == 1
        assert config["repositories"][0]["name"] == "repo1"
        assert config["output_dir"] == "./output"
        assert config["clone_dir"] == "./repos"

    def test_update_config_file_existing_merge(self, tmp_path):
        """Test updating an existing config file with merge."""
        config_path = tmp_path / "config.yaml"

        # Create initial config
        initial_config = {
            "repositories": [
                {
                    "url": "https://github.com/org/repo1.git",
                    "name": "repo1",
                    "branches": ["main"],
                    "include_tags": True,
                    "max_tags": 10,
                    "path": ".",
                    "recursive": False,
                    "exclude_paths": [],
                }
            ],
            "output_dir": "./custom-output",
            "clone_dir": "./custom-repos",
        }

        with open(config_path, "w") as f:
            yaml.dump(initial_config, f)

        new_repos = [
            RepositoryConfig(url="https://github.com/org/repo2.git", name="repo2"),
        ]

        update_config_file(config_path, new_repos, replace=False)

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        assert len(config["repositories"]) == 2
        assert config["output_dir"] == "./custom-output"
        assert config["clone_dir"] == "./custom-repos"

    def test_update_config_file_existing_replace(self, tmp_path):
        """Test updating an existing config file with replace."""
        config_path = tmp_path / "config.yaml"

        # Create initial config
        initial_config = {
            "repositories": [
                {
                    "url": "https://github.com/org/repo1.git",
                    "name": "repo1",
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

        with open(config_path, "w") as f:
            yaml.dump(initial_config, f)

        new_repos = [
            RepositoryConfig(url="https://github.com/org/repo2.git", name="repo2"),
        ]

        update_config_file(config_path, new_repos, replace=True)

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Should have only the new repo
        assert len(config["repositories"]) == 1
        assert config["repositories"][0]["name"] == "repo2"
