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

        # Get default branch if ignore_default_branch is enabled
        default_branch = None
        if repo_config.ignore_default_branch:
            default_branch = self._get_default_branch(repo)
            print(f"Default branch detected: {default_branch}")

        # Process branches
        for branch in repo_config.branches:
            # Skip if this is the default branch and ignore_default_branch is True
            if repo_config.ignore_default_branch and branch == default_branch:
                print(f"Skipping default branch: {branch}")
                continue
                
            try:
                branch_summaries = self._process_ref(
                    repo, repo_config, branch, repo_path, repo_config.path
                )
                summaries.extend(branch_summaries)
            except Exception as e:
                print(f"Error processing branch {branch}: {e}")

        # Process tags if enabled
        if repo_config.include_tags:
            tags = self._get_tags(repo, repo_config.max_tags)
            for tag in tags:
                try:
                    tag_summaries = self._process_ref(
                        repo, repo_config, tag, repo_path, repo_config.path
                    )
                    summaries.extend(tag_summaries)
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
    ) -> List[TerraformModuleSummary]:
        """Process a specific git ref (branch or tag)."""
        try:
            # Checkout the ref
            repo.git.checkout(ref)

            summaries = []
            
            # Find all module paths
            module_paths = self._find_module_paths(
                repo_path, module_path, repo_config.recursive
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
            print(f"Error processing ref {ref}: {e}")
            return []

    def _find_module_paths(
        self, repo_path: Path, module_path: str, recursive: bool = False
    ) -> List[Path]:
        """Find all terraform module paths."""
        full_module_path = repo_path / module_path
        if not full_module_path.exists():
            print(f"Module path {module_path} does not exist")
            return []

        module_paths = []
        
        if recursive:
            # Recursively find all directories containing terraform files
            for root, dirs, files in os.walk(full_module_path):
                root_path = Path(root)
                # Check if this directory contains terraform files
                if self._is_terraform_module(root_path):
                    module_paths.append(root_path)
        else:
            # Only check the specified path
            if self._is_terraform_module(full_module_path):
                module_paths.append(full_module_path)

        return module_paths

    def _is_terraform_module(self, path: Path) -> bool:
        """Check if a directory contains terraform files."""
        tf_files = list(path.glob("*.tf"))
        return len(tf_files) > 0

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

    def _get_default_branch(self, repo: git.Repo) -> Optional[str]:
        """Get the default branch of the repository."""
        try:
            # Try to get the default branch from origin
            if hasattr(repo.remotes.origin, 'refs'):
                for ref in repo.remotes.origin.refs:
                    if ref.name == 'origin/HEAD':
                        # Extract branch name from origin/HEAD -> origin/main
                        return ref.ref.name.split('/')[-1]
            
            # Fallback: try common default branch names
            common_defaults = ['main', 'master', 'develop', 'dev']
            for branch_name in common_defaults:
                try:
                    if f'origin/{branch_name}' in [ref.name for ref in repo.remotes.origin.refs]:
                        return branch_name
                except:
                    continue
                    
            # If all else fails, try to get the active branch
            try:
                return repo.active_branch.name
            except:
                pass
                
            return None
        except Exception as e:
            print(f"Error getting default branch: {e}")
            return None

    def cleanup(self):
        """Clean up cloned repositories."""
        if self.clone_dir.exists():
            shutil.rmtree(self.clone_dir)
