#!/usr/bin/env python
"""Example of using terraform-ingest programmatically."""

from terraform_ingest.models import IngestConfig, RepositoryConfig
from terraform_ingest.ingest import TerraformIngest

# Example 1: Create configuration programmatically
print("Example 1: Programmatic configuration")
print("=" * 50)

repo_config = RepositoryConfig(
    url="https://github.com/terraform-aws-modules/terraform-aws-vpc",
    name="terraform-aws-vpc",
    branches=["main"],
    include_tags=True,
    max_tags=3,
)

config = IngestConfig(
    repositories=[repo_config],
    output_dir="./output",
    clone_dir="./repos",
)

ingester = TerraformIngest(config)
print(f"Created ingester with {len(config.repositories)} repository configuration(s)")

# Example 2: Load from YAML file
print("\n\nExample 2: Load from YAML file")
print("=" * 50)

try:
    ingester = TerraformIngest.from_yaml("config.yaml")
    print("Loaded configuration from config.yaml")
    print(f"Will process {len(ingester.config.repositories)} repository/repositories")

    # Run ingestion
    # summaries = ingester.ingest()
    # print(f"Processed {len(summaries)} module version(s)")
except FileNotFoundError:
    print("config.yaml not found. Run 'terraform-ingest init config.yaml' first.")

# Example 3: Process a specific module and get results
print("\n\nExample 3: Access module summaries")
print("=" * 50)

# This would actually clone and process the repository
# summaries = ingester.ingest()
#
# for summary in summaries:
#     print(f"\nRepository: {summary.repository}")
#     print(f"Ref: {summary.ref}")
#     print(f"Description: {summary.description}")
#     print(f"Variables: {len(summary.variables)}")
#     print(f"Outputs: {len(summary.outputs)}")
#     print(f"Providers: {[p.name for p in summary.providers]}")

print("\nUncomment the code above to actually process repositories.")
print("Note: This requires git credentials for private repositories.")
