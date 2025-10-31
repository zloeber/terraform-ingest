"""Repository management for cloning and analyzing terraform repositories."""

import fnmatch
import os
import shutil
from pathlib import Path
from typing import Any, List, Optional
import git
from packaging.version import parse as parse_version, InvalidVersion
from terraform_ingest.models import RepositoryConfig, TerraformModuleSummary
from terraform_ingest.parser import TerraformParser
from terraform_ingest.tty_logger import get_logger


class RepositoryManager:
    """Manager for cloning and analyzing git repositories."""

    def __init__(
        self,
        clone_dir: str = "./repos",
        logger: Optional[Any] = None,
        skip_existing: bool = False,
    ):
        """Initialize the repository manager.

        Args:
            clone_dir: Directory to clone repositories into
            logger: Optional logger instance. Defaults to get_logger() if not provided.
            skip_existing: If True, skip cloning repositories that already exist locally
        """
        self.clone_dir = Path(clone_dir)
        self.clone_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or get_logger(__name__)
        self.skip_existing = skip_existing

    def process_repository(
        self, repo_config: RepositoryConfig
    ) -> List[TerraformModuleSummary]:
        """Process a repository and return summaries for all refs.

        Args:
            repo_config: RepositoryConfig instance with URL and processing options

        Returns:
            List of TerraformModuleSummary instances for all modules in the repository
        """
        summaries = []

        if len(repo_config.branches) == 0 and not repo_config.include_tags:
            self.logger.info("No branches or tags specified to process.")
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
                )
                summaries.extend(branch_summaries)
            except Exception as e:
                self.logger.error(f"Error processing branch {branch}: {e}")

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
                    )
                    summaries.extend(tag_summaries)
                except Exception as e:
                    self.logger.error(f"Error processing tag {tag}: {e}")

        return summaries

    def _clone_or_update(self, url: str, path: Path) -> git.Repo:
        """Clone a repository or update if it already exists.

        Args:
            url: Repository URL
            path: Path to clone repository to

        Returns:
            GitPython Repo instance
        """
        if path.exists():
            try:
                repo = git.Repo(path)
                # If skip_existing is True, skip updating
                if self.skip_existing:
                    self.logger.info(
                        f"Repository already exists at {path}, skipping clone/update"
                    )
                    return repo
                # Otherwise fetch latest changes
                self.logger.info(f"Updating repository from {url}...")
                repo.remotes.origin.fetch()
                return repo
            except Exception as e:
                self.logger.error(f"Error updating repository, re-cloning: {e}")
                shutil.rmtree(path)

        # Clone the repository
        self.logger.info(f"Cloning repository from {url}...")
        repo = git.Repo.clone_from(url, path)
        return repo

    def _process_ref(
        self,
        repo: git.Repo,
        repo_config: RepositoryConfig,
        ref: str,
        repo_path: Path,
        module_path: str = ".",
    ) -> List[TerraformModuleSummary]:
        """Process a specific git ref (branch or tag).

        Args:
            repo: GitPython Repo instance
            repo_config: RepositoryConfig with processing options
            ref: Branch or tag name to process
            repo_path: Path to the repository
            module_path: Path within repository to scan for modules

        Returns:
            List of TerraformModuleSummary instances
        """

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
                    self.logger.debug(f"Ref '{ref}' does not exist in repository")
                    return []

            self.logger.info(f"Processing ref: {ref}")
        except Exception as e:
            self.logger.error(f"Error validating ref {ref}: {e}")
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
                    parser = TerraformParser(str(mod_path), logger=self.logger)
                    # Calculate relative path from repo root
                    relative_path = str(mod_path.relative_to(repo_path))
                    summary = parser.parse_module(repo_config.url, ref, relative_path)
                    if summary:
                        summaries.append(summary)
                except Exception as e:
                    self.logger.error(f"Error parsing module at {mod_path}: {e}")

            return summaries
        except Exception as e:
            self.logger.error(f"Error processing ref {ref}: {e}")
            return []

    def _find_module_paths(
        self,
        repo_path: Path,
        module_path: str,
        recursive: bool = False,
        exclude_paths: Optional[List[str]] = None,
    ) -> List[Path]:
        """Find all terraform module paths, excluding patterns in exclude_paths.

        Args:
            repo_path: Root path of the repository
            module_path: Starting module path within repository
            recursive: Whether to recursively find modules in subdirectories
            exclude_paths: List of path patterns to exclude

        Returns:
            List of Path instances for each found module
        """
        full_module_path = Path.joinpath(repo_path, module_path)
        if not full_module_path.exists():
            self.logger.debug(f"Module path {module_path} does not exist")
            return []

        if exclude_paths is None:
            exclude_paths = []

        module_paths = []

        if recursive:
            # Recursively find all directories containing terraform files
            for root, _, _ in os.walk(full_module_path):
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
        """Get a list of tags from the repository, sorted by semantic version.

        Tags are sorted using semantic versioning (like git tag -l | sort -r -V).
        Tags that don't parse as valid semantic versions are included at the end,
        sorted alphabetically in reverse order.

        Args:
            repo: GitPython Repo instance
            max_tags: Maximum number of tags to return

        Returns:
            List of tag names sorted by semantic version in descending order
        """
        try:
            tag_names = [tag.name for tag in repo.tags]

            if not tag_names:
                return []

            # Separate valid semantic versions from non-versions
            valid_versions = []
            non_versions = []

            for tag_name in tag_names:
                try:
                    version = parse_version(tag_name)
                    # Skip pre-release and dev versions if desired, or include them
                    valid_versions.append((tag_name, version))
                except InvalidVersion:
                    # Tags that don't parse as versions
                    non_versions.append(tag_name)

            # Sort valid versions in descending order
            valid_versions.sort(key=lambda x: x[1], reverse=True)
            sorted_tag_names = [tag_name for tag_name, _ in valid_versions]

            # Add non-version tags at the end, sorted reverse alphabetically
            sorted_tag_names.extend(sorted(non_versions, reverse=True))

            if max_tags:
                sorted_tag_names = sorted_tag_names[:max_tags]

            return sorted_tag_names
        except Exception as e:
            self.logger.error(f"Error getting tags: {e}")
            return []

    def _get_default_branch(self, repo: git.Repo) -> Optional[str]:
        """Get the default branch of the repository.

        Args:
            repo: GitPython Repo instance

        Returns:
            Default branch name or None
        """
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
            self.logger.error(f"Error getting default branch: {e}")
            return None

    def cleanup(self):
        """Clean up cloned repositories."""
        if self.clone_dir.exists():
            shutil.rmtree(self.clone_dir)
