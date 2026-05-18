"""Tests for data models."""

from terraform_ingest.models import (
    TerraformVariable,
    TerraformOutput,
    TerraformProvider,
    TerraformModule,
    TerraformResource,
    TerraformModuleSummary,
    RepositoryConfig,
    IngestConfig,
    EmbeddingConfig,
)


def test_terraform_variable():
    """Test TerraformVariable model."""
    # Required variable (no default)
    var_required = TerraformVariable(
        name="required_var",
        type="string",
        description="A required variable",
        has_default=False,
        required=True,
        nullable=True,
    )
    assert var_required.required is True
    assert var_required.has_default is False
    assert not hasattr(var_required, "default") or var_required.default is None
    dump = var_required.model_dump()
    assert "default" not in dump

    # Variable with default = null (sentinel)
    var_null_default = TerraformVariable(
        name="sentinel_null_var",
        type="any",
        description="A variable with null default",
        has_default=True,
        default=None,
        default_semantics="sentinel_null",
        required=False,
        nullable=True,
    )
    assert var_null_default.required is False
    assert var_null_default.has_default is True
    assert var_null_default.default is None
    assert var_null_default.default_semantics == "sentinel_null"
    dump = var_null_default.model_dump()
    assert "default" in dump and dump["default"] is None
    assert dump["default_semantics"] == "sentinel_null"

    # Variable with literal default
    var_literal = TerraformVariable(
        name="literal_var",
        type="number",
        description="A variable with a literal default",
        has_default=True,
        default=42,
        default_semantics="literal",
        required=False,
        nullable=True,
    )
    assert var_literal.required is False
    assert var_literal.default == 42
    assert var_literal.default_semantics == "literal"
    dump = var_literal.model_dump()
    assert dump["default"] == 42
    assert dump["default_semantics"] == "literal"

    # Variable with nullable = False
    var_not_nullable = TerraformVariable(
        name="not_nullable_var",
        type="string",
        description="A not-nullable variable",
        has_default=True,
        default="foo",
        default_semantics="literal",
        required=False,
        nullable=False,
    )
    assert var_not_nullable.nullable is False

    # Test omitted default in serialization
    var_no_default = TerraformVariable(
        name="no_default_var",
        type="string",
        description="No default",
        has_default=False,
        required=True,
    )
    dump2 = var_no_default.model_dump()
    assert "default" not in dump2 and "default_semantics" not in dump2


def test_terraform_output():
    """Test TerraformOutput model."""
    output = TerraformOutput(
        name="vpc_id",
        description="VPC ID",
        sensitive=False,
    )
    assert output.name == "vpc_id"
    assert output.sensitive is False


def test_terraform_provider():
    """Test TerraformProvider model."""
    provider = TerraformProvider(
        name="aws",
        source="hashicorp/aws",
        version=">= 4.0",
    )
    assert provider.name == "aws"
    assert provider.source == "hashicorp/aws"


def test_terraform_module():
    """Test TerraformModule model."""
    module = TerraformModule(
        name="vpc",
        source="terraform-aws-modules/vpc/aws",
        version="3.0.0",
    )
    assert module.name == "vpc"
    assert module.source == "terraform-aws-modules/vpc/aws"


def test_terraform_resource():
    """Test TerraformResource model."""
    resource = TerraformResource(
        type="aws_vpc",
        name="main",
        description="Main VPC",
    )
    assert resource.type == "aws_vpc"
    assert resource.name == "main"
    assert resource.description == "Main VPC"


def test_terraform_module_summary():
    """Test TerraformModuleSummary model."""
    summary = TerraformModuleSummary(
        repository="https://github.com/user/terraform-module",
        ref="main",
        path=".",
        description="Test module",
    )
    assert summary.repository == "https://github.com/user/terraform-module"
    assert summary.ref == "main"
    assert len(summary.variables) == 0
    assert len(summary.outputs) == 0
    assert len(summary.resources) == 0

    # Test with resources
    resource = TerraformResource(type="aws_vpc", name="main")
    summary_with_resources = TerraformModuleSummary(
        repository="https://github.com/user/terraform-module",
        ref="main",
        resources=[resource],
    )
    assert len(summary_with_resources.resources) == 1
    assert summary_with_resources.resources[0].type == "aws_vpc"


def test_repository_config():
    """Test RepositoryConfig model."""
    config = RepositoryConfig(
        url="https://github.com/user/terraform-module",
        branches=["main", "develop"],
        include_tags=True,
        max_tags=5,
    )
    assert config.url == "https://github.com/user/terraform-module"
    assert len(config.branches) == 2
    assert config.include_tags is True


def test_ingest_config():
    """Test IngestConfig model."""
    repo_config = RepositoryConfig(
        url="https://github.com/user/terraform-module",
    )
    config = IngestConfig(
        repositories=[repo_config],
        output_dir="./test_output",
        clone_dir="./test_repos",
    )
    assert len(config.repositories) == 1
    assert config.output_dir == "./test_output"


def test_embedding_config():
    """Test EmbeddingConfig model."""
    config = EmbeddingConfig(
        enabled=True,
        strategy="sentence-transformers",
        chromadb_path="./test_chromadb",
        collection_name="test_modules",
    )
    assert config.enabled is True
    assert config.strategy == "sentence-transformers"
    assert config.chromadb_path == "./test_chromadb"
    assert config.collection_name == "test_modules"


def test_ingest_config_with_embedding():
    """Test IngestConfig with embedding configuration."""
    repo_config = RepositoryConfig(
        url="https://github.com/user/terraform-module",
    )
    embedding_config = EmbeddingConfig(
        enabled=True,
        strategy="chromadb-default",
    )
    config = IngestConfig(
        repositories=[repo_config],
        output_dir="./test_output",
        clone_dir="./test_repos",
        embedding=embedding_config,
    )
    assert len(config.repositories) == 1
    assert config.embedding is not None
    assert config.embedding.enabled is True
    assert config.embedding.strategy == "chromadb-default"
