"""Repository management for cloning and analyzing terraform repositories."""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import git
from .models import RepositoryConfig, TerraformModuleSummary
from .parser import TerraformParser


class RepositoryManager:
    """Manager for cloning and analyzing git repositories."""

    def __init__(self, clone_dir: str = "./repos"):
        """Initialize the repository manager."""
        self.clone_dir = Path(clone_dir)
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    def process_repository(
        self, repo_config: RepositoryConfig
    ) -> List[TerraformModuleSummary]:
        """Process a repository and return summaries for all refs."""
        summaries = []

        # Determine repository name
        repo_name = repo_config.name
        if not repo_name:
            repo_name = repo_config.url.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]

        repo_path = self.clone_dir / repo_name

        # Clone or update repository
        repo = self._clone_or_update(repo_config.url, repo_path)

        # Process branches
        for branch in repo_config.branches:
            try:
                summary = self._process_ref(
                    repo, repo_config, branch, repo_path, repo_config.path
                )
                if summary:
                    summaries.append(summary)
            except Exception as e:
                print(f"Error processing branch {branch}: {e}")

        # Process tags if enabled
        if repo_config.include_tags:
            tags = self._get_tags(repo, repo_config.max_tags)
            for tag in tags:
                try:
                    summary = self._process_ref(
                        repo, repo_config, tag, repo_path, repo_config.path
                    )
                    if summary:
                        summaries.append(summary)
                except Exception as e:
                    print(f"Error processing tag {tag}: {e}")

        return summaries

    def _clone_or_update(self, url: str, path: Path) -> git.Repo:
        """Clone a repository or update if it already exists."""
        if path.exists():
            try:
                repo = git.Repo(path)
                # Fetch latest changes
                repo.remotes.origin.fetch()
                return repo
            except Exception as e:
                print(f"Error updating repository, re-cloning: {e}")
                shutil.rmtree(path)

        # Clone the repository
        print(f"Cloning repository from {url}...")
        repo = git.Repo.clone_from(url, path)
        return repo

    def _process_ref(
        self,
        repo: git.Repo,
        repo_config: RepositoryConfig,
        ref: str,
        repo_path: Path,
        module_path: str = ".",
    ) -> Optional[TerraformModuleSummary]:
        """Process a specific git ref (branch or tag)."""
        try:
            # Checkout the ref
            repo.git.checkout(ref)

            # Parse the module
            full_module_path = repo_path / module_path
            if not full_module_path.exists():
                print(f"Module path {module_path} does not exist in ref {ref}")
                return None

            parser = TerraformParser(str(full_module_path))
            summary = parser.parse_module(repo_config.url, ref)

            return summary
        except Exception as e:
            print(f"Error processing ref {ref}: {e}")
            return None

    def _get_tags(self, repo: git.Repo, max_tags: Optional[int] = None) -> List[str]:
        """Get a list of tags from the repository."""
        try:
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime, reverse=True)
            tag_names = [tag.name for tag in tags]

            if max_tags:
                tag_names = tag_names[:max_tags]

            return tag_names
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []

    def cleanup(self):
        """Clean up cloned repositories."""
        if self.clone_dir.exists():
            shutil.rmtree(self.clone_dir)
