"""Tests for module indexer functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from terraform_ingest.indexer import ModuleIndexer
from terraform_ingest.models import (
    TerraformModuleSummary,
    TerraformProvider,
    TerraformVariable,
    TerraformOutput,
)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_module_summary():
    """Create a sample TerraformModuleSummary for testing."""
    return TerraformModuleSummary(
        repository="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        ref="v5.0.0",
        path=".",
        description="AWS VPC module for network infrastructure",
        readme_content="# AWS VPC Module\n\nA Terraform module for creating VPCs",
        variables=[
            TerraformVariable(
                name="cidr_block",
                type="string",
                description="CIDR block for VPC",
                required=True,
            ),
            TerraformVariable(
                name="enable_dns_hostnames",
                type="bool",
                description="Enable DNS hostnames",
                default="true",
                required=False,
            ),
        ],
        outputs=[
            TerraformOutput(
                name="vpc_id",
                description="The ID of the VPC",
                sensitive=False,
            ),
        ],
        providers=[
            TerraformProvider(
                name="aws",
                source="hashicorp/aws",
                version=">= 4.0",
            ),
        ],
        modules=[],
        resources=[],
    )


@pytest.fixture
def nested_module_summary():
    """Create a sample nested TerraformModuleSummary for testing."""
    return TerraformModuleSummary(
        repository="https://github.com/terraform-aws-modules/terraform-aws-security-group",
        ref="v4.9.0",
        path="modules/sg",
        description="Security group module",
        readme_content="# AWS Security Group Module",
        variables=[],
        outputs=[],
        providers=[
            TerraformProvider(
                name="aws",
                source="hashicorp/aws",
                version=">= 4.0",
            ),
        ],
        modules=[],
        resources=[],
    )


class TestModuleIndexer:
    """Test suite for ModuleIndexer class."""

    def test_indexer_initialization(self, temp_output_dir):
        """Test ModuleIndexer initialization."""
        indexer = ModuleIndexer(temp_output_dir)
        assert indexer.output_dir == Path(temp_output_dir)
        assert indexer.modules == {}

    def test_add_module(self, temp_output_dir, sample_module_summary):
        """Test adding a module to the index."""
        indexer = ModuleIndexer(temp_output_dir)
        doc_id = indexer.add_module(sample_module_summary)

        assert doc_id is not None
        assert len(doc_id) == 64  # SHA256 hex is 64 characters
        assert doc_id in indexer.modules

    def test_add_module_creates_consistent_id(
        self, temp_output_dir, sample_module_summary
    ):
        """Test that adding the same module produces consistent IDs."""
        indexer1 = ModuleIndexer(temp_output_dir)
        id1 = indexer1.add_module(sample_module_summary)

        indexer2 = ModuleIndexer(temp_output_dir)
        id2 = indexer2.add_module(sample_module_summary)

        assert id1 == id2

    def test_get_module(self, temp_output_dir, sample_module_summary):
        """Test retrieving a module from the index."""
        indexer = ModuleIndexer(temp_output_dir)
        doc_id = indexer.add_module(sample_module_summary)

        module = indexer.get_module(doc_id)
        assert module is not None
        assert module["repository"] == sample_module_summary.repository
        assert module["ref"] == sample_module_summary.ref
        assert module["path"] == sample_module_summary.path

    def test_get_nonexistent_module(self, temp_output_dir):
        """Test retrieving a nonexistent module returns None."""
        indexer = ModuleIndexer(temp_output_dir)
        module = indexer.get_module("nonexistent_id")
        assert module is None

    def test_remove_module(self, temp_output_dir, sample_module_summary):
        """Test removing a module from the index."""
        indexer = ModuleIndexer(temp_output_dir)
        doc_id = indexer.add_module(sample_module_summary)

        assert doc_id in indexer.modules
        removed = indexer.remove_module(doc_id)
        assert removed is True
        assert doc_id not in indexer.modules

    def test_remove_nonexistent_module(self, temp_output_dir):
        """Test removing a nonexistent module returns False."""
        indexer = ModuleIndexer(temp_output_dir)
        removed = indexer.remove_module("nonexistent_id")
        assert removed is False

    def test_search_by_provider(
        self, temp_output_dir, sample_module_summary, nested_module_summary
    ):
        """Test searching modules by provider."""
        indexer = ModuleIndexer(temp_output_dir)
        indexer.add_module(sample_module_summary)
        indexer.add_module(nested_module_summary)

        results = indexer.search_by_provider("aws")
        assert len(results) == 2

    def test_search_by_provider_case_insensitive(
        self, temp_output_dir, sample_module_summary
    ):
        """Test provider search is case insensitive."""
        indexer = ModuleIndexer(temp_output_dir)
        indexer.add_module(sample_module_summary)

        results = indexer.search_by_provider("AWS")
        assert len(results) == 1

    def test_search_by_tag(self, temp_output_dir, nested_module_summary):
        """Test searching modules by tag."""
        indexer = ModuleIndexer(temp_output_dir)
        indexer.add_module(nested_module_summary)

        results = indexer.search_by_tag("sg")
        assert len(results) == 1
        assert results[0]["id"] == indexer._generate_document_id(nested_module_summary)

    def test_search_by_repository(self, temp_output_dir, sample_module_summary):
        """Test searching modules by repository."""
        indexer = ModuleIndexer(temp_output_dir)
        indexer.add_module(sample_module_summary)

        results = indexer.search_by_repository("terraform-aws-vpc")
        assert len(results) == 1

    def test_list_all(
        self, temp_output_dir, sample_module_summary, nested_module_summary
    ):
        """Test listing all modules."""
        indexer = ModuleIndexer(temp_output_dir)
        indexer.add_module(sample_module_summary)
        indexer.add_module(nested_module_summary)

        all_modules = indexer.list_all()
        assert len(all_modules) == 2

    def test_get_stats(
        self, temp_output_dir, sample_module_summary, nested_module_summary
    ):
        """Test getting index statistics."""
        indexer = ModuleIndexer(temp_output_dir)
        indexer.add_module(sample_module_summary)
        indexer.add_module(nested_module_summary)

        stats = indexer.get_stats()
        assert stats["total_modules"] == 2
        assert stats["unique_providers"] == 1
        assert "aws" in stats["providers"]

    def test_save_and_load_index(self, temp_output_dir, sample_module_summary):
        """Test saving and loading the index."""
        # Add and save
        indexer1 = ModuleIndexer(temp_output_dir)
        doc_id = indexer1.add_module(sample_module_summary)
        indexer1.save()

        # Load in new instance
        indexer2 = ModuleIndexer(temp_output_dir)
        assert doc_id in indexer2.modules
        module = indexer2.get_module(doc_id)
        assert module["repository"] == sample_module_summary.repository

    def test_get_module_summary_path(self, temp_output_dir, sample_module_summary):
        """Test getting the path to a module's summary file."""
        indexer = ModuleIndexer(temp_output_dir)
        doc_id = indexer.add_module(sample_module_summary)

        path = indexer.get_module_summary_path(doc_id)
        assert path is not None
        assert "terraform-aws-vpc" in str(path)

    def test_clear_index(self, temp_output_dir, sample_module_summary):
        """Test clearing the index."""
        indexer = ModuleIndexer(temp_output_dir)
        indexer.add_module(sample_module_summary)

        assert len(indexer.modules) > 0
        indexer.clear()
        assert len(indexer.modules) == 0

    def test_rebuild_from_files(self, temp_output_dir, sample_module_summary):
        """Test rebuilding index from JSON files."""
        # Create a JSON file manually
        summary_data = sample_module_summary.model_dump()
        json_file = Path(temp_output_dir) / "terraform-aws-vpc_v5.0.0.json"
        with open(json_file, "w") as f:
            json.dump(summary_data, f)

        # Rebuild index
        indexer = ModuleIndexer(temp_output_dir)
        count = indexer.rebuild_from_files()

        assert count == 1
        assert len(indexer.modules) == 1

    def test_generate_document_id_format(self, sample_module_summary):
        """Test document ID generation format."""
        indexer = ModuleIndexer("./output")
        doc_id = indexer._generate_document_id(sample_module_summary)

        # Should be SHA256 hex
        assert len(doc_id) == 64
        assert all(c in "0123456789abcdef" for c in doc_id)

    def test_get_summary_filename_root_path(self, sample_module_summary):
        """Test filename generation for root module."""
        indexer = ModuleIndexer("./output")
        filename = indexer._get_summary_filename(sample_module_summary)

        assert filename == "terraform-aws-vpc_v5.0.0.json"

    def test_get_summary_filename_nested_path(self, nested_module_summary):
        """Test filename generation for nested module."""
        indexer = ModuleIndexer("./output")
        filename = indexer._get_summary_filename(nested_module_summary)

        assert "modules_sg" in filename
        assert filename == "terraform-aws-security-group_v4.9.0_modules_sg.json"

    def test_extract_tags(self, nested_module_summary):
        """Test tag extraction from module."""
        indexer = ModuleIndexer("./output")
        tags = indexer._extract_tags(nested_module_summary)

        assert "modules" in tags
        assert "sg" in tags
        assert "aws" in tags  # From provider

    def test_module_entry_has_required_fields(
        self, temp_output_dir, sample_module_summary
    ):
        """Test that module entries contain required fields."""
        indexer = ModuleIndexer(temp_output_dir)
        doc_id = indexer.add_module(sample_module_summary)

        module = indexer.get_module(doc_id)
        required_fields = [
            "id",
            "repository",
            "ref",
            "path",
            "summary_file",
            "provider",
            "tags",
        ]
        for field in required_fields:
            assert field in module, f"Missing required field: {field}"
