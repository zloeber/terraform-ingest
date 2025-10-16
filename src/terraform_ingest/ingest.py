"""Main ingestion logic for processing terraform repositories."""

import json
from pathlib import Path
from typing import List
import yaml
from .models import IngestConfig, TerraformModuleSummary
from .repository import RepositoryManager


class TerraformIngest:
    """Main class for ingesting terraform repositories."""

    def __init__(self, config: IngestConfig):
        """Initialize the ingestion process."""
        self.config = config
        self.repo_manager = RepositoryManager(config.clone_dir)
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "TerraformIngest":
        """Create an instance from a YAML configuration file."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        config = IngestConfig(**config_dict)
        return cls(config)

    def ingest(self) -> List[TerraformModuleSummary]:
        """Process all repositories and generate summaries."""
        all_summaries = []

        for repo_config in self.config.repositories:
            print(f"Processing repository: {repo_config.url}")
            summaries = self.repo_manager.process_repository(repo_config)
            all_summaries.extend(summaries)

            # Save summaries for this repository
            for summary in summaries:
                self._save_summary(summary)

        return all_summaries

    def _save_summary(self, summary: TerraformModuleSummary):
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

        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2, default=str)

        print(f"Saved summary to {output_path}")

    def get_all_summaries_json(self) -> str:
        """Get all summaries as a single JSON string."""
        summaries = self.ingest()
        return json.dumps(
            [s.model_dump() for s in summaries], indent=2, default=str
        )

    def cleanup(self):
        """Clean up temporary files."""
        self.repo_manager.cleanup()
