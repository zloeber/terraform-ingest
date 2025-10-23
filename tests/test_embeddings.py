"""Tests for vector database embeddings."""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Mock openai module if not installed to prevent import errors during test collection
try:
    import openai  # noqa: F401

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    sys.modules["openai"] = MagicMock()

# Mock chromadb module if not installed
try:
    import chromadb  # noqa: F401

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    sys.modules["chromadb"] = MagicMock()

from terraform_ingest.models import (
    EmbeddingConfig,
    TerraformModuleSummary,
    TerraformVariable,
    TerraformOutput,
    TerraformProvider,
)
from terraform_ingest.embeddings import (
    VectorDBManager,
    ChromaDBDefaultStrategy,
    OpenAIEmbeddingStrategy,
    SentenceTransformersStrategy,
)


def test_embedding_config_defaults():
    """Test EmbeddingConfig with default values."""
    config = EmbeddingConfig()
    assert config.enabled is False
    assert config.strategy == "chromadb-default"
    assert config.chromadb_path == "./chromadb"
    assert config.collection_name == "terraform_modules"
    assert config.include_description is True
    assert config.include_readme is True
    assert config.include_variables is True
    assert config.include_outputs is True
    assert config.include_resource_types is True


def test_embedding_config_custom():
    """Test EmbeddingConfig with custom values."""
    config = EmbeddingConfig(
        enabled=True,
        strategy="sentence-transformers",
        sentence_transformers_model="all-mpnet-base-v2",
        collection_name="custom_collection",
        include_readme=False,
    )
    assert config.enabled is True
    assert config.strategy == "sentence-transformers"
    assert config.sentence_transformers_model == "all-mpnet-base-v2"
    assert config.collection_name == "custom_collection"
    assert config.include_readme is False


def test_chromadb_default_strategy():
    """Test ChromaDB default embedding strategy."""
    strategy = ChromaDBDefaultStrategy()
    embeddings = strategy.embed_text("test text")
    # ChromaDB default returns empty list (ChromaDB handles it internally)
    assert embeddings == []


def test_sentence_transformers_strategy_initialization():
    """Test SentenceTransformers strategy initialization."""
    strategy = SentenceTransformersStrategy(model_name="all-MiniLM-L6-v2")
    assert strategy.model_name == "all-MiniLM-L6-v2"
    assert strategy._model is None  # Lazy loading


@pytest.mark.skipif(not HAS_OPENAI, reason="openai package not installed")
@patch("openai.OpenAI")
def test_openai_embedding_strategy(mock_openai_client):
    """Test OpenAI embedding strategy."""
    # Mock OpenAI response
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
    mock_client_instance = Mock()
    mock_client_instance.embeddings.create.return_value = mock_response
    mock_openai_client.return_value = mock_client_instance

    strategy = OpenAIEmbeddingStrategy(
        api_key="test-key", model="text-embedding-3-small"
    )
    embeddings = strategy.embed_text("test text")

    assert embeddings == [0.1, 0.2, 0.3]
    mock_client_instance.embeddings.create.assert_called_once()


def test_vector_db_manager_initialization_disabled():
    """Test VectorDBManager when embeddings are disabled."""
    config = EmbeddingConfig(enabled=False)
    manager = VectorDBManager(config)

    assert manager.config.enabled is False
    assert manager.embedding_strategy is None


def test_vector_db_manager_initialization_chromadb_default():
    """Test VectorDBManager with ChromaDB default strategy."""
    config = EmbeddingConfig(enabled=True, strategy="chromadb-default")
    manager = VectorDBManager(config)

    assert isinstance(manager.embedding_strategy, ChromaDBDefaultStrategy)


def test_vector_db_manager_initialization_sentence_transformers():
    """Test VectorDBManager with sentence-transformers strategy."""
    config = EmbeddingConfig(
        enabled=True,
        strategy="sentence-transformers",
        sentence_transformers_model="all-MiniLM-L6-v2",
    )
    manager = VectorDBManager(config)

    assert isinstance(manager.embedding_strategy, SentenceTransformersStrategy)
    assert manager.embedding_strategy.model_name == "all-MiniLM-L6-v2"


def test_vector_db_manager_invalid_strategy():
    """Test VectorDBManager with invalid strategy."""
    from pydantic_core import ValidationError

    with pytest.raises(ValidationError):
        _ = EmbeddingConfig(enabled=True, strategy="invalid-strategy")


def test_vector_db_manager_openai_missing_key():
    """Test VectorDBManager with OpenAI strategy but missing API key."""
    config = EmbeddingConfig(enabled=True, strategy="openai")

    with pytest.raises(ValueError, match="OpenAI API key is required"):
        VectorDBManager(config)


def test_generate_document_id():
    """Test unique document ID generation."""
    config = EmbeddingConfig(enabled=True)
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo", ref="main", path="modules/vpc"
    )

    doc_id = manager._generate_document_id(summary)

    # Should be a SHA256 hash (64 hex characters)
    assert len(doc_id) == 64
    assert all(c in "0123456789abcdef" for c in doc_id)

    # Same input should produce same ID
    doc_id2 = manager._generate_document_id(summary)
    assert doc_id == doc_id2

    # Different input should produce different ID
    summary2 = TerraformModuleSummary(
        repository="https://github.com/test/repo",
        ref="develop",  # Different ref
        path="modules/vpc",
    )
    doc_id3 = manager._generate_document_id(summary2)
    assert doc_id != doc_id3


def test_prepare_document_text_full():
    """Test document text preparation with all content types."""
    config = EmbeddingConfig(
        enabled=True,
        include_description=True,
        include_readme=True,
        include_variables=True,
        include_outputs=True,
        include_resource_types=True,
    )
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo",
        ref="main",
        path=".",
        description="Test VPC module",
        readme_content="# VPC Module\nThis module creates a VPC.",
        variables=[
            TerraformVariable(
                name="vpc_cidr",
                type="string",
                description="CIDR block for VPC",
                default="10.0.0.0/16",
            ),
            TerraformVariable(
                name="enable_nat", type="bool", description="Enable NAT gateway"
            ),
        ],
        outputs=[
            TerraformOutput(name="vpc_id", description="ID of the VPC"),
        ],
        providers=[
            TerraformProvider(name="aws", source="hashicorp/aws", version=">= 4.0"),
        ],
    )

    text = manager._prepare_document_text(summary)

    # Check that all parts are included
    assert "Description: Test VPC module" in text
    assert "README: # VPC Module" in text
    assert "Variables:" in text
    assert "vpc_cidr: CIDR block for VPC (type: string)" in text
    assert "enable_nat: Enable NAT gateway (type: bool)" in text
    assert "Outputs:" in text
    assert "vpc_id: ID of the VPC" in text
    assert "Resources:" in text
    assert "aws provider" in text


def test_prepare_document_text_partial():
    """Test document text preparation with selective content."""
    config = EmbeddingConfig(
        enabled=True,
        include_description=True,
        include_readme=False,
        include_variables=True,
        include_outputs=False,
        include_resource_types=False,
    )
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo",
        ref="main",
        path=".",
        description="Test module",
        readme_content="# README",
        variables=[
            TerraformVariable(name="test_var", description="Test variable"),
        ],
        outputs=[
            TerraformOutput(name="test_output", description="Test output"),
        ],
        providers=[
            TerraformProvider(name="aws"),
        ],
    )

    text = manager._prepare_document_text(summary)

    # Should include description and variables
    assert "Description: Test module" in text
    assert "Variables:" in text
    assert "test_var: Test variable" in text

    # Should NOT include README, outputs, or resources
    assert "README:" not in text
    assert "Outputs:" not in text
    assert "Resources:" not in text


def test_prepare_metadata():
    """Test metadata preparation."""
    config = EmbeddingConfig(enabled=True)
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo",
        ref="main",
        path="modules/vpc",
        providers=[
            TerraformProvider(name="aws"),
            TerraformProvider(name="random"),
        ],
    )

    metadata = manager._prepare_metadata(summary)

    # Check required fields
    assert metadata["repository"] == "https://github.com/test/repo"
    assert metadata["ref"] == "main"
    assert metadata["path"] == "modules/vpc"
    assert metadata["provider"] == "aws"  # First provider
    assert metadata["providers"] == "aws,random"
    assert "last_updated" in metadata

    # Tags should include path components and provider names
    assert "modules" in metadata["tags"]
    assert "vpc" in metadata["tags"]
    assert "aws" in metadata["tags"]


def test_prepare_metadata_no_providers():
    """Test metadata preparation when no providers are specified."""
    config = EmbeddingConfig(enabled=True)
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo",
        ref="main",
        path=".",
    )

    metadata = manager._prepare_metadata(summary)

    assert metadata["provider"] == "unknown"
    assert metadata["providers"] == ""


def test_upsert_module_disabled():
    """Test upsert when embeddings are disabled."""
    config = EmbeddingConfig(enabled=False)
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo", ref="main", path="."
    )

    doc_id = manager.upsert_module(summary)
    assert doc_id == ""


@pytest.mark.skipif(not HAS_CHROMADB, reason="chromadb package not installed")
@patch("chromadb.PersistentClient")
def test_upsert_module_new_document(mock_chromadb_client):
    """Test upserting a new document."""
    # Mock ChromaDB collection
    mock_collection = Mock()
    mock_collection.get.return_value = {"ids": []}  # No existing documents
    mock_collection.add = Mock()

    mock_client_instance = Mock()
    mock_client_instance.get_or_create_collection.return_value = mock_collection
    mock_chromadb_client.return_value = mock_client_instance

    config = EmbeddingConfig(enabled=True, strategy="chromadb-default")
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo",
        ref="main",
        path=".",
        description="Test module",
    )

    doc_id = manager.upsert_module(summary)

    # Should return a valid ID
    assert len(doc_id) == 64

    # Should call add (not update)
    mock_collection.add.assert_called_once()
    mock_collection.update.assert_not_called()


@pytest.mark.skipif(not HAS_CHROMADB, reason="chromadb package not installed")
@patch("chromadb.PersistentClient")
def test_upsert_module_update_existing(mock_chromadb_client):
    """Test upserting an existing document (update)."""
    # Mock ChromaDB collection
    mock_collection = Mock()
    mock_collection.get.return_value = {"ids": ["existing_id"]}  # Document exists
    mock_collection.update = Mock()

    mock_client_instance = Mock()
    mock_client_instance.get_or_create_collection.return_value = mock_collection
    mock_chromadb_client.return_value = mock_client_instance

    config = EmbeddingConfig(enabled=True, strategy="chromadb-default")
    manager = VectorDBManager(config)

    summary = TerraformModuleSummary(
        repository="https://github.com/test/repo",
        ref="main",
        path=".",
        description="Updated module",
    )

    doc_id = manager.upsert_module(summary)

    # Should return a valid ID
    assert len(doc_id) == 64

    # Should call update (not add)
    mock_collection.update.assert_called_once()
    mock_collection.add.assert_not_called()


@pytest.mark.skipif(not HAS_CHROMADB, reason="chromadb package not installed")
@patch("chromadb.PersistentClient")
def test_search_modules(mock_chromadb_client):
    """Test searching modules."""
    # Mock ChromaDB collection
    mock_collection = Mock()
    mock_collection.query.return_value = {
        "ids": [["id1", "id2"]],
        "documents": [["doc1", "doc2"]],
        "metadatas": [
            [
                {"repository": "repo1", "provider": "aws"},
                {"repository": "repo2", "provider": "azure"},
            ]
        ],
        "distances": [[0.1, 0.2]],
    }

    mock_client_instance = Mock()
    mock_client_instance.get_or_create_collection.return_value = mock_collection
    mock_chromadb_client.return_value = mock_client_instance

    config = EmbeddingConfig(enabled=True, strategy="chromadb-default")
    manager = VectorDBManager(config)

    results = manager.search_modules("test query", n_results=5)

    assert len(results) == 2
    assert results[0]["id"] == "id1"
    assert results[0]["document"] == "doc1"
    assert results[0]["metadata"]["provider"] == "aws"
    assert results[0]["distance"] == 0.1

    mock_collection.query.assert_called_once()


@pytest.mark.skipif(not HAS_CHROMADB, reason="chromadb package not installed")
@patch("chromadb.PersistentClient")
def test_search_modules_with_filters(mock_chromadb_client):
    """Test searching modules with metadata filters."""
    # Mock ChromaDB collection
    mock_collection = Mock()
    mock_collection.query.return_value = {
        "ids": [["id1"]],
        "documents": [["doc1"]],
        "metadatas": [[{"repository": "repo1", "provider": "aws"}]],
        "distances": [[0.1]],
    }

    mock_client_instance = Mock()
    mock_client_instance.get_or_create_collection.return_value = mock_collection
    mock_chromadb_client.return_value = mock_client_instance

    config = EmbeddingConfig(enabled=True, strategy="chromadb-default")
    manager = VectorDBManager(config)

    filters = {"provider": "aws", "repository": "https://github.com/test/repo"}
    _ = manager.search_modules("test query", filters=filters, n_results=5)

    # Verify filters were passed to query
    call_args = mock_collection.query.call_args
    assert call_args[1]["where"] == filters


@pytest.mark.skipif(not HAS_CHROMADB, reason="chromadb package not installed")
@patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction")
@patch("chromadb.PersistentClient")
def test_get_collection_stats(mock_chromadb_client, mock_embedding_func):
    """Test getting collection statistics."""
    # Mock ChromaDB collection
    mock_collection = Mock()
    mock_collection.count.return_value = 42

    mock_client_instance = Mock()
    mock_client_instance.get_or_create_collection.return_value = mock_collection
    mock_chromadb_client.return_value = mock_client_instance

    # Mock the embedding function
    mock_embedding_func.return_value = Mock()

    config = EmbeddingConfig(
        enabled=True,
        strategy="sentence-transformers",
        collection_name="test_collection",
    )
    manager = VectorDBManager(config)

    stats = manager.get_collection_stats()

    assert stats["enabled"] is True
    assert stats["collection_name"] == "test_collection"
    assert stats["document_count"] == 42
    assert stats["embedding_strategy"] == "sentence-transformers"


def test_get_collection_stats_disabled():
    """Test getting stats when embeddings are disabled."""
    config = EmbeddingConfig(enabled=False)
    manager = VectorDBManager(config)

    stats = manager.get_collection_stats()

    assert stats["enabled"] is False
    assert "document_count" not in stats


def test_search_modules_disabled():
    """Test searching when embeddings are disabled."""
    config = EmbeddingConfig(enabled=False)
    manager = VectorDBManager(config)

    results = manager.search_modules("test query")

    assert results == []
