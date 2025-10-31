"""Main ingestion logic for processing terraform repositories."""

import os
import json
from pathlib import Path
from typing import Any, List, Optional
import yaml
from terraform_ingest.models import IngestConfig, TerraformModuleSummary
from terraform_ingest.repository import RepositoryManager
from terraform_ingest.embeddings import VectorDBManager
from terraform_ingest.indexer import ModuleIndexer
from terraform_ingest.tty_logger import get_logger
from terraform_ingest.dependency_installer import ensure_embeddings_available


class TerraformIngest:
    """Main class for ingesting terraform repositories."""

    def __init__(
        self,
        config: IngestConfig,
        logger: Optional[Any] = None,
        auto_install_deps: bool = True,
        skip_existing: bool = False,
    ):
        """Initialize the ingestion process.

        Args:
            config: IngestConfig instance with repository and embedding settings
            logger: Optional logger instance. Defaults to get_logger() if not provided.
            auto_install_deps: Whether to automatically install missing embedding dependencies
            skip_existing: If True, skip cloning repositories that already exist locally
        """
        self.config = config
        self.logger = logger or get_logger(__name__)
        self.repo_manager = RepositoryManager(
            config.clone_dir, logger=self.logger, skip_existing=skip_existing
        )
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure embedding dependencies are available if embeddings are enabled
        if config.embedding and config.embedding.enabled:
            ensure_embeddings_available(
                config.embedding,
                logger=self.logger,
                auto_install=auto_install_deps,
            )

        # Initialize vector database manager if enabled
        self.vector_db = None
        if config.embedding and config.embedding.enabled:
            try:
                self.vector_db = VectorDBManager(config.embedding)
            except Exception as e:
                self.logger.warning(
                    f"Failed to initialize vector database: {e}. "
                    f"Embeddings will be disabled for this run."
                )

        # Initialize module indexer for fast lookups
        self.indexer = ModuleIndexer(config.output_dir)

    @classmethod
    def from_yaml(
        cls,
        yaml_path: str,
        logger: Optional[Any] = None,
        auto_install_deps: bool = True,
        skip_existing: bool = False,
    ) -> "TerraformIngest":
        """Create an instance from a YAML configuration file.

        Args:
            yaml_path: Path to the YAML configuration file
            logger: Optional logger instance
            auto_install_deps: Whether to automatically install missing embedding dependencies
            skip_existing: If True, skip cloning repositories that already exist locally

        Returns:
            TerraformIngest instance
        """
        with open(yaml_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        config = IngestConfig(**config_dict)
        return cls(
            config,
            logger=logger,
            auto_install_deps=auto_install_deps,
            skip_existing=skip_existing,
        )

    def ingest(self) -> List[TerraformModuleSummary]:
        """Process all repositories and generate summaries.

        Returns:
            List of TerraformModuleSummary instances for all processed modules
        """
        os.environ["TOKENIZERS_PARALLELISM"] = "true"

        all_summaries = []

        for repo_config in self.config.repositories:
            self.logger.info(f"Processing repository: {repo_config.url}")
            summaries = self.repo_manager.process_repository(repo_config)
            all_summaries.extend(summaries)

            # Save summaries for this repository
            for summary in summaries:
                self._save_summary(summary)

        # Save the module index after all modules are processed
        self.finalize_index()

        return all_summaries

    def _save_summary(self, summary: TerraformModuleSummary):
        """Save a summary to a JSON file.

        Args:
            summary: TerraformModuleSummary instance to save
        """
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
        self.logger.info(f"Saved summary to {output_path}")

        # Add to module index
        try:
            doc_id = self.indexer.add_module(summary)
            self.logger.debug(f"Added module to index with ID: {doc_id}")
        except Exception as e:
            self.logger.warning(f"Failed to add module to index: {e}")

        # Upsert to vector database if enabled
        if self.vector_db:
            try:
                doc_id = self.vector_db.upsert_module(summary)
                self.logger.info(f"Upserted to vector database with ID: {doc_id}")
            except Exception as e:
                self.logger.warning(f"Failed to upsert to vector database: {e}")

    def finalize_index(self) -> None:
        """Save the module index after ingestion is complete."""
        try:
            self.indexer.save()
            stats = self.indexer.get_stats()
            self.logger.info(
                f"Module index saved with {stats['total_modules']} modules "
                f"across {stats['unique_providers']} providers"
            )
        except Exception as e:
            self.logger.warning(f"Failed to save module index: {e}")

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
