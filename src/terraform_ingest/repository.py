"""Repository management for cloning and analyzing terraform repositories."""

import fnmatch
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
        self, repo_config: RepositoryConfig, silent: bool = False
    ) -> List[TerraformModuleSummary]:
        """Process a repository and return summaries for all refs."""
        summaries = []

        if len(repo_config.branches) == 0 and not repo_config.include_tags:
            if not silent:
                print("No branches or tags specified to process.")
            return summaries

        # Determine repository name
        repo_name = repo_config.name
        if not repo_name:
            repo_name = repo_config.url.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]

        repo_path = Path.joinpath(self.clone_dir, repo_name)

        # Clone or update repository
        repo = self._clone_or_update(repo_config.url, repo_path)

        # Process branches
        for branch in repo_config.branches:
            try:
                branch_summaries = self._process_ref(
                    repo,
                    repo_config,
                    branch,
                    repo_path,
                    repo_config.path,
                    silent=silent,
                )
                summaries.extend(branch_summaries)
            except Exception as e:
                if not silent:
                    print(f"Error processing branch {branch}: {e}")

        # Process tags if enabled
        if repo_config.include_tags:
            tags = self._get_tags(repo, repo_config.max_tags)
            for tag in tags:
                try:
                    tag_summaries = self._process_ref(
                        repo,
                        repo_config,
                        tag,
                        repo_path,
                        repo_config.path,
                        silent=silent,
                    )
                    summaries.extend(tag_summaries)
                except Exception as e:
                    if not silent:
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
        silent: bool = False,
    ) -> List[TerraformModuleSummary]:
        """Process a specific git ref (branch or tag)."""

        summaries = []

        # Validate that the ref exists in the repository
        try:
            # Check if ref exists in remote branches
            remote_refs = [ref.name for ref in repo.remotes.origin.refs]
            local_refs = [ref.name for ref in repo.refs]

            # For branches, check if origin/{ref} exists
            if f"origin/{ref}" not in remote_refs and ref not in local_refs:
                # For tags, check if ref exists in tags
                tag_names = [tag.name for tag in repo.tags]
                if ref not in tag_names:
                    if not silent:
                        print(f"Ref '{ref}' does not exist in repository")
                    return []

            if not silent:
                print(f"Processing ref: {ref}")
        except Exception as e:
            if not silent:
                print(f"Error validating ref {ref}: {e}")
            return summaries
        try:
            # Checkout the ref
            repo.git.checkout(ref)

            # Find all module paths
            module_paths = self._find_module_paths(
                repo_path, module_path, repo_config.recursive, repo_config.exclude_paths
            )

            for mod_path in module_paths:
                try:
                    parser = TerraformParser(str(mod_path))
                    # Calculate relative path from repo root
                    relative_path = str(mod_path.relative_to(repo_path))
                    summary = parser.parse_module(repo_config.url, ref, relative_path)
                    if summary:
                        summaries.append(summary)
                except Exception as e:
                    print(f"Error parsing module at {mod_path}: {e}")

            return summaries
        except Exception as e:
            if not silent:
                print(f"Error processing ref {ref}: {e}")
            return []

    def _find_module_paths(
        self,
        repo_path: Path,
        module_path: str,
        recursive: bool = False,
        exclude_paths: Optional[List[str]] = None,
    ) -> List[Path]:
        """Find all terraform module paths, excluding patterns in exclude_paths."""
        full_module_path = Path.joinpath(repo_path, module_path)
        if not full_module_path.exists():
            print(f"Module path {module_path} does not exist")
            return []

        if exclude_paths is None:
            exclude_paths = []

        module_paths = []

        if recursive:
            # Recursively find all directories containing terraform files
            for root, dirs, files in os.walk(full_module_path):
                root_path = Path(root)
                # Get relative path from repo root for exclusion matching
                try:
                    relative_path = root_path.relative_to(repo_path)
                except ValueError:
                    relative_path = root_path

                # Check if path should be excluded
                if self._is_path_excluded(str(relative_path), exclude_paths):
                    continue

                # Check if this directory contains terraform files
                if self._is_terraform_module(root_path):
                    module_paths.append(root_path)
        else:
            # Only check the specified path
            if self._is_terraform_module(full_module_path):
                module_paths.append(full_module_path)

        return module_paths

    def _is_path_excluded(
        self, relative_path: str, exclude_patterns: List[str]
    ) -> bool:
        """Check if a path matches any of the exclude patterns."""
        # Normalize path separators for cross-platform compatibility
        normalized_path = relative_path.replace(os.sep, "/")

        for pattern in exclude_patterns:
            # Normalize pattern separators
            normalized_pattern = pattern.replace(os.sep, "/")

            # Check if the path matches the pattern (supporting both exact and wildcard matches)
            if fnmatch.fnmatch(normalized_path, normalized_pattern):
                return True
            # Also check if any parent directory matches (for patterns like 'examples/*')
            if fnmatch.fnmatch(normalized_path + "/", normalized_pattern):
                return True
            # Check if pattern matches any component of the path
            parts = normalized_path.split("/")
            for i in range(len(parts)):
                partial_path = "/".join(parts[: i + 1])
                if fnmatch.fnmatch(partial_path, normalized_pattern):
                    return True

        return False

    def _is_terraform_module(self, path: Path) -> bool:
        """Check if a directory contains terraform files."""
        tf_files = list(path.glob("*.tf"))
        return len(tf_files) > 0

    def _get_tags(self, repo: git.Repo, max_tags: Optional[int] = None) -> List[str]:
        """Get a list of tags from the repository."""
        try:
            tags = sorted(
                repo.tags, key=lambda t: t.commit.committed_datetime, reverse=True
            )
            tag_names = [tag.name for tag in tags]

            if max_tags:
                tag_names = tag_names[:max_tags]

            return tag_names
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []

    def _get_default_branch(self, repo: git.Repo) -> Optional[str]:
        """Get the default branch of the repository."""
        try:
            # Try to get the default branch from origin
            if hasattr(repo.remotes.origin, "refs"):
                for ref in repo.remotes.origin.refs:
                    if ref.name == "origin/HEAD":
                        # Extract branch name from origin/HEAD -> origin/main
                        return ref.ref.name.split("/")[-1]

            # Fallback: try common default branch names
            common_defaults = ["main", "master"]
            for branch_name in common_defaults:
                try:
                    if f"origin/{branch_name}" in [
                        ref.name for ref in repo.remotes.origin.refs
                    ]:
                        return branch_name
                except Exception as _:
                    continue

            # If all else fails, try to get the active branch
            try:
                return repo.active_branch.name
            except Exception as _:
                pass

            return None
        except Exception as e:
            print(f"Error getting default branch: {e}")
            return None

    def cleanup(self):
        """Clean up cloned repositories."""
        if self.clone_dir.exists():
            shutil.rmtree(self.clone_dir)
