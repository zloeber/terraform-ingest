"""Main ingestion logic for processing terraform repositories."""

import json
from pathlib import Path
from typing import List, Optional
import yaml
from .models import IngestConfig, TerraformModuleSummary
from .repository import RepositoryManager
from .embeddings import VectorDBManager


class TerraformIngest:
    """Main class for ingesting terraform repositories."""

    def __init__(self, config: IngestConfig):
        """Initialize the ingestion process."""
        self.config = config
        self.repo_manager = RepositoryManager(config.clone_dir)
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize vector database manager if enabled
        self.vector_db = None
        if config.embedding and config.embedding.enabled:
            self.vector_db = VectorDBManager(config.embedding)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "TerraformIngest":
        """Create an instance from a YAML configuration file."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        config = IngestConfig(**config_dict)
        return cls(config)

    def ingest(self, silent: bool = False) -> List[TerraformModuleSummary]:
        """Process all repositories and generate summaries."""
        all_summaries = []

        for repo_config in self.config.repositories:
            if not silent:
                print(f"Processing repository: {repo_config.url}")
            summaries = self.repo_manager.process_repository(repo_config, silent=silent)
            all_summaries.extend(summaries)

            # Save summaries for this repository
            for summary in summaries:
                self._save_summary(summary, silent=silent)

        return all_summaries

    def _save_summary(self, summary: TerraformModuleSummary, silent: bool = False):
        """Save a summary to a JSON file."""
        # Create a safe filename from repository, ref, and path
        repo_name = summary.repository.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        ref_name = summary.ref.replace("/", "_")

        # Include module path in filename if it's not the root
        if summary.path and summary.path != "." and summary.path != "/":
            # Clean up the path for filename use
            path_part = summary.path.replace("/", "_").replace("\\", "_")
            filename = f"{repo_name}_{ref_name}_{path_part}.json"
        else:
            filename = f"{repo_name}_{ref_name}.json"

        output_path = Path.joinpath(self.output_dir, filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2, default=str)
        if not silent:
            print(f"Saved summary to {output_path}")

        # Upsert to vector database if enabled
        if self.vector_db:
            try:
                doc_id = self.vector_db.upsert_module(summary)
                if not silent:
                    print(f"Upserted to vector database with ID: {doc_id}")
            except Exception as e:
                if not silent:
                    print(f"Warning: Failed to upsert to vector database: {e}")

    def get_all_summaries_json(self) -> str:
        """Get all summaries as a single JSON string."""
        summaries = self.ingest()
        return json.dumps([s.model_dump() for s in summaries], indent=2, default=str)

    def cleanup(self):
        """Clean up temporary files."""
        self.repo_manager.cleanup()

    def get_vector_db_stats(self):
        """Get vector database statistics."""
        if self.vector_db:
            return self.vector_db.get_collection_stats()
        return {"enabled": False}

    def search_vector_db(
        self, query: str, filters: Optional[dict] = None, n_results: int = 10
    ):
        """Search the vector database.

        Args:
            query: Search query
            filters: Optional metadata filters
            n_results: Number of results to return

        Returns:
            List of matching modules
        """
        if self.vector_db:
            return self.vector_db.search_modules(query, filters, n_results)
        return []
