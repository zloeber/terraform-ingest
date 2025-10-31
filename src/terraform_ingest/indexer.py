"""Module indexing utilities for fast ID-based lookup of module summaries."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from terraform_ingest.models import TerraformModuleSummary


class ModuleIndexer:
    """Manages a local index file for fast module lookup by vector search ID."""

    DEFAULT_INDEX_FILENAME = "module_index.json"

    def __init__(
        self, output_dir: str = "./output", index_filename: str = DEFAULT_INDEX_FILENAME
    ):
        """Initialize the module indexer.

        Args:
            output_dir: Directory containing module summary JSON files
            index_filename: Name of the index file to maintain
        """
        self.output_dir = Path(output_dir)
        self.index_path = self.output_dir / index_filename
        self.modules: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load existing index from file if it exists."""
        if self.index_path.exists():
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.modules = data.get("modules", {})
            except (json.JSONDecodeError, IOError):
                # If index is corrupted, start fresh
                self.modules = {}

    def _save_index(self) -> None:
        """Save the index to file."""
        index_data = {
            "index_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_modules": len(self.modules),
            "modules": self.modules,
        }

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)

    def _generate_document_id(self, summary: TerraformModuleSummary) -> str:
        """Generate unique ID based on repo:ref:path (same as vector DB).

        Args:
            summary: Terraform module summary

        Returns:
            Unique document ID (SHA256 hash)
        """
        id_string = f"{summary.repository}:{summary.ref}:{summary.path}"
        return hashlib.sha256(id_string.encode()).hexdigest()

    def _get_summary_filename(self, summary: TerraformModuleSummary) -> str:
        """Generate the summary JSON filename following ingest.py's pattern.

        Args:
            summary: Terraform module summary

        Returns:
            Filename of the JSON summary file
        """
        repo_name = summary.repository.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        ref_name = summary.ref.replace("/", "_")

        # Include module path in filename if it's not the root
        if summary.path and summary.path != "." and summary.path != "/":
            path_part = summary.path.replace("/", "_").replace("\\", "_")
            filename = f"{repo_name}_{ref_name}_{path_part}.json"
        else:
            filename = f"{repo_name}_{ref_name}.json"

        return filename

    def add_module(self, summary: TerraformModuleSummary) -> str:
        """Add or update a module in the index.

        Args:
            summary: Terraform module summary

        Returns:
            The document ID for the module
        """
        doc_id = self._generate_document_id(summary)
        filename = self._get_summary_filename(summary)

        self.modules[doc_id] = {
            "id": doc_id,
            "repository": summary.repository,
            "ref": summary.ref,
            "path": summary.path,
            "summary_file": f"output/{filename}",
            "provider": (summary.providers[0].name if summary.providers else "unknown"),
            "providers": (
                ",".join([p.name for p in summary.providers])
                if summary.providers
                else ""
            ),
            "tags": self._extract_tags(summary),
            "last_indexed": datetime.now(timezone.utc).isoformat(),
        }

        return doc_id

    def _extract_tags(self, summary: TerraformModuleSummary) -> List[str]:
        """Extract tags from module metadata.

        Args:
            summary: Terraform module summary

        Returns:
            List of tag strings
        """
        tags = []

        # Add path components as tags
        if summary.path and summary.path != "." and summary.path != "/":
            path_parts = summary.path.replace("\\", "/").split("/")
            tags.extend([p for p in path_parts if p and p != "."])

        # Add provider names as tags
        for provider in summary.providers:
            if provider.name:
                tags.append(provider.name)

        return tags

    def remove_module(self, doc_id: str) -> bool:
        """Remove a module from the index by ID.

        Args:
            doc_id: The document ID to remove

        Returns:
            True if module was removed, False if not found
        """
        if doc_id in self.modules:
            del self.modules[doc_id]
            return True
        return False

    def get_module(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get module index entry by ID.

        Args:
            doc_id: The document ID to lookup

        Returns:
            Module index entry or None if not found
        """
        return self.modules.get(doc_id)

    def get_module_summary_path(self, doc_id: str) -> Optional[Path]:
        """Get the full path to a module's summary JSON file.

        Args:
            doc_id: The document ID to lookup

        Returns:
            Full path to the summary file or None if not found
        """
        entry = self.get_module(doc_id)
        if entry:
            return self.output_dir / entry["summary_file"].replace("output/", "")
        return None

    def search_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Search modules by provider.

        Args:
            provider: Provider name to search for

        Returns:
            List of matching module entries
        """
        results = []
        for module in self.modules.values():
            if provider.lower() in module["provider"].lower():
                results.append(module)
            elif provider.lower() in module["providers"].lower():
                results.append(module)
        return results

    def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Search modules by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching module entries
        """
        results = []
        for module in self.modules.values():
            if tag.lower() in module["tags"]:
                results.append(module)
        return results

    def search_by_repository(self, repository: str) -> List[Dict[str, Any]]:
        """Search modules by repository URL.

        Args:
            repository: Repository URL to search for

        Returns:
            List of matching module entries
        """
        return [
            module
            for module in self.modules.values()
            if repository.lower() in module["repository"].lower()
        ]

    def list_all(self) -> List[Dict[str, Any]]:
        """Get all modules in the index.

        Returns:
            List of all module entries
        """
        return list(self.modules.values())

    def clear(self) -> None:
        """Clear all entries from the index."""
        self.modules.clear()

    def rebuild_from_files(self) -> int:
        """Rebuild the index from all JSON summary files in output directory.

        Returns:
            Number of modules indexed
        """
        self.clear()

        if not self.output_dir.exists():
            return 0

        count = 0
        for json_file in self.output_dir.glob("*.json"):
            # Skip the index file itself
            if json_file.name == self.index_path.name:
                continue

            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    summary = TerraformModuleSummary(**data)
                    self.add_module(summary)
                    count += 1
            except (json.JSONDecodeError, ValueError):
                # Skip files that don't match the summary schema
                continue

        self.save()
        return count

    def save(self) -> None:
        """Save the index to file."""
        self._save_index()

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics.

        Returns:
            Dictionary with index statistics
        """
        providers = set()
        all_tags = set()

        for module in self.modules.values():
            if module["provider"] != "unknown":
                providers.add(module["provider"])
            all_tags.update(module["tags"])

        return {
            "total_modules": len(self.modules),
            "unique_providers": len(providers),
            "providers": sorted(list(providers)),
            "unique_tags": len(all_tags),
            "index_file": str(self.index_path),
        }
