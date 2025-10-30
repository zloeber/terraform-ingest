"""Repository importers for updating configuration files."""

import yaml
import requests
import click
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional
from terraform_ingest.models import RepositoryConfig


class RepositoryImporter(ABC):
    """Base class for repository importers."""

    @abstractmethod
    def fetch_repositories(self, **kwargs) -> List[RepositoryConfig]:
        """Fetch repositories from the source.

        Returns:
            List of RepositoryConfig objects.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider.

        Returns:
            Provider name (e.g., 'github', 'gitlab').
        """
        pass


class GitHubImporter(RepositoryImporter):
    """Importer for GitHub repositories."""

    def __init__(
        self,
        org: str,
        token: Optional[str] = None,
        include_private: bool = False,
        terraform_only: bool = False,
        base_path: str = "./src",
    ):
        """Initialize GitHub importer.

        Args:
            org: GitHub organization name
            token: GitHub personal access token
            include_private: Include private repositories
            terraform_only: Only include repositories with Terraform files
            base_path: Base path for module scanning
        """
        self.org = org
        self.token = token
        self.include_private = include_private
        self.terraform_only = terraform_only
        self.base_path = base_path
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"token {token}"

    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "github"

    def fetch_repositories(self, **kwargs) -> List[RepositoryConfig]:
        """Fetch repositories from GitHub organization.

        Returns:
            List of RepositoryConfig objects.

        Raises:
            click.ClickException: If there's an error fetching repositories.
        """
        repositories = []
        page = 1
        per_page = 100

        click.echo(
            f"Fetching repositories from GitHub organization: {self.org}", err=True
        )

        while True:
            url = f"https://api.github.com/orgs/{self.org}/repos"
            params = {
                "page": page,
                "per_page": per_page,
                "type": "all" if self.include_private else "public",
            }

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise click.ClickException(f"Error fetching repositories: {e}")

            repos = response.json()
            if not repos:
                break

            for repo in repos:
                # Skip archived repositories
                if repo.get("archived", False):
                    continue

                # Skip if filtering for Terraform repos only
                if self.terraform_only and not self._has_terraform_files(repo):
                    continue

                repo_config = RepositoryConfig(
                    name=repo["name"],
                    url=repo["clone_url"],
                    branches=[],
                    include_tags=True,
                    max_tags=1,
                    path=self.base_path,
                    recursive=False,
                    exclude_paths=[],
                )
                repositories.append(repo_config)

            page += 1
            click.echo(f"Processed page {page - 1} ({len(repos)} repos)", err=True)

        click.echo(f"Found {len(repositories)} repositories", err=True)
        return repositories

    def _has_terraform_files(self, repo: Dict[str, Any]) -> bool:
        """Check if a repository contains Terraform files.

        Args:
            repo: Repository data from GitHub API

        Returns:
            True if repository contains .tf files, False otherwise.
        """
        repo_name = repo.get("name", repo.get("full_name", "unknown"))

        try:
            # Search for .tf files in the repository
            search_url = "https://api.github.com/search/code"
            params = {"q": f"extension:tf repo:{repo['full_name']}", "per_page": 1}

            response = requests.get(search_url, headers=self.headers, params=params)

            if response.status_code == 200:
                result = response.json()
                return result.get("total_count", 0) > 0
            elif response.status_code == 403:
                # Check rate limit headers to distinguish between rate limiting and auth issues
                remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
                reset_time = response.headers.get("X-RateLimit-Reset", "unknown")

                # Check if it's actually a rate limit issue vs auth/permissions issue
                try:
                    remaining_int = int(remaining)
                    if remaining_int == 0:
                        click.echo(
                            f"Warning: Cannot check Terraform files for {repo_name} "
                            f"(GitHub API rate limited - reset at {reset_time})",
                            err=True,
                        )
                        return True  # Include by default if we can't check due to rate limit
                except (ValueError, TypeError):
                    pass

                # If remaining is not 0, it's likely a permissions or token scope issue
                if not self.token:
                    click.echo(
                        f"Warning: Cannot check Terraform files for {repo_name} "
                        f"(GitHub search API requires authentication - use --token or set GITHUB_TOKEN)",
                        err=True,
                    )
                else:
                    click.echo(
                        f"Warning: Cannot check Terraform files for {repo_name} "
                        f"(GitHub search API returned 403 - verify token has required scopes)",
                        err=True,
                    )
                return True  # Include by default if we can't check
            else:
                return False
        except Exception as e:
            # Log the exception for debugging but don't fail the whole operation
            click.echo(
                f"Warning: Error checking Terraform files for {repo_name}: {e}",
                err=True,
            )
            return True  # Include by default if check fails


def merge_repositories(
    existing_repos: List[RepositoryConfig],
    new_repos: List[RepositoryConfig],
    replace: bool = False,
) -> List[RepositoryConfig]:
    """Merge new repositories with existing ones.

    Args:
        existing_repos: Existing repository configurations
        new_repos: New repository configurations to add
        replace: If True, replace all existing repos. If False, merge.

    Returns:
        Merged list of RepositoryConfig objects.
    """
    if replace:
        return new_repos

    # Create a dictionary of existing repos by URL for fast lookup
    existing_by_url = {repo.url: repo for repo in existing_repos}

    # Start with existing repos
    merged = list(existing_repos)

    # Add new repos that don't already exist
    for new_repo in new_repos:
        if new_repo.url not in existing_by_url:
            merged.append(new_repo)

    return merged


def update_config_file(
    config_path: Path,
    new_repos: List[RepositoryConfig],
    replace: bool = False,
) -> None:
    """Update a configuration file with new repositories.

    Args:
        config_path: Path to the configuration file
        new_repos: New repository configurations to add
        replace: If True, replace all existing repos. If False, merge.
    """
    # Load existing configuration if file exists
    existing_config = {}
    existing_repos = []

    if config_path.exists():
        with open(config_path, "r") as f:
            existing_config = yaml.safe_load(f) or {}
            existing_repo_data = existing_config.get("repositories", [])
            existing_repos = [RepositoryConfig(**repo) for repo in existing_repo_data]

    # Merge repositories
    merged_repos = merge_repositories(existing_repos, new_repos, replace=replace)

    # Update the configuration
    existing_config["repositories"] = [repo.model_dump() for repo in merged_repos]

    # Ensure other required keys exist with defaults if not present
    if "output_dir" not in existing_config:
        existing_config["output_dir"] = "./output"
    if "clone_dir" not in existing_config:
        existing_config["clone_dir"] = "./repos"

    # Write back to file
    with open(config_path, "w") as f:
        yaml.dump(existing_config, f, default_flow_style=False, sort_keys=False)

    click.echo(f"Updated {config_path} with {len(merged_repos)} repositories")
