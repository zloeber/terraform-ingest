import click
import yaml
import requests
from typing import Dict, Any
from pathlib import Path

#!/usr/bin/env python3
"""
GitHub Organization Repository Fetcher

A CLI tool to fetch all repositories from a GitHub organization and output them as YAML.
"""


@click.command()
@click.option("--org", required=True, help="GitHub organization name")
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub personal access token (or set GITHUB_TOKEN env var)",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path (default: stdout)"
)
@click.option(
    "--include-private",
    is_flag=True,
    help="Include private repositories (requires authentication)",
)
@click.option(
    "--terraform-only",
    is_flag=True,
    help="Only include repositories that contain Terraform files",
)
@click.option("--base-path", default="./src")
def get_github_repos(
    org: str,
    token: str,
    output: str,
    include_private: bool,
    terraform_only: bool,
    base_path: str,
) -> None:
    """
    Fetch all repositories from a GitHub organization and output as YAML.

    Example:
        python get-github-repos.py --org hashicorp --terraform-only
        python get-github-repos.py --org myorg --token ghp_xxx --output repos.yaml
    """
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"

    repositories = []
    page = 1
    per_page = 100

    click.echo(f"Fetching repositories from GitHub organization: {org}", err=True)

    while True:
        url = f"https://api.github.com/orgs/{org}/repos"
        params = {
            "page": page,
            "per_page": per_page,
            "type": "all" if include_private else "public",
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            click.echo(f"Error fetching repositories: {e}", err=True)
            raise click.Abort()

        repos = response.json()
        if not repos:
            break

        for repo in repos:
            # Skip if filtering for Terraform repos only
            if terraform_only and not _has_terraform_files(repo, headers):
                continue

            repo_config = {
                "url": repo["clone_url"],
                "name": repo["name"],
                "description": repo["description"],
                "default_branch": repo["default_branch"],
                "private": repo["private"],
                "archived": repo["archived"],
            }
            repositories.append(repo_config)

        page += 1
        click.echo(f"Processed page {page - 1} ({len(repos)} repos)", err=True)

    # Format as terraform-ingest compatible YAML
    output_data = {
        "repositories": [
            {
                "name": repo["name"],
                "url": repo["url"],
                "recursive": False,
                "branches": [],
                "include_tags": True,
                "max_tags": 1,
                "path": base_path,
                "exclude_paths": [],
            }
            for repo in repositories
            if not repo["archived"]  # Skip archived repos
        ]
    }

    yaml_output = yaml.dump(output_data, default_flow_style=False, sort_keys=False)

    if output:
        output_path = Path(output)
        output_path.write_text(yaml_output)
        click.echo(
            f"Wrote {len(output_data['repositories'])} repositories to {output_path}",
            err=True,
        )
    else:
        click.echo(yaml_output)


def _has_terraform_files(repo: Dict[str, Any], headers: Dict[str, str]) -> bool:
    """
    Check if a repository contains Terraform files by searching for .tf files.
    """
    try:
        # Search for .tf files in the repository
        search_url = "https://api.github.com/search/code"
        params = {"q": f"extension:tf repo:{repo['full_name']}", "per_page": 1}

        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code == 200:
            result = response.json()
            return result.get("total_count", 0) > 0
        elif response.status_code == 403:
            # Rate limited or search API not available without auth
            click.echo(
                f"Warning: Cannot check Terraform files for {repo['name']} (rate limited)",
                err=True,
            )
            return True  # Include by default if we can't check
        else:
            return False
    except Exception:
        return True  # Include by default if check fails


if __name__ == "__main__":
    get_github_repos()
