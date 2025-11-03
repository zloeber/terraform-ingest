"""Vector database embeddings for Terraform modules."""

import hashlib
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from terraform_ingest.models import EmbeddingConfig, TerraformModuleSummary


class EmbeddingStrategy(ABC):
    """Abstract base class for embedding strategies."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for the given text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector
        """
        pass


class OpenAIEmbeddingStrategy(EmbeddingStrategy):
    """OpenAI embeddings via API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """Initialize OpenAI embedding strategy.

        Args:
            api_key: OpenAI API key
            model: Model to use for embeddings
        """
        self.api_key = api_key
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI API."""
        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)
            response = client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except ImportError:
            raise ImportError(
                "openai package is required for OpenAI embeddings. Install with: pip install openai"
            )


class ClaudeEmbeddingStrategy(EmbeddingStrategy):
    """Claude embeddings via Anthropic API (uses voyage AI embeddings)."""

    def __init__(self, api_key: str):
        """Initialize Claude/Voyage embedding strategy.

        Args:
            api_key: Voyage AI API key (Anthropic partners with Voyage for embeddings)
        """
        self.api_key = api_key

    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings using Voyage AI."""
        try:
            import voyageai

            vo = voyageai.Client(api_key=self.api_key)
            result = vo.embed([text], model="voyage-2")
            return result.embeddings[0]
        except ImportError:
            raise ImportError(
                "voyageai package is required for Claude/Voyage embeddings. Install with: pip install voyageai"
            )


class SentenceTransformersStrategy(EmbeddingStrategy):
    """Local embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize sentence-transformers strategy.

        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers package is required for local embeddings. "
                    "Install with: pip install sentence-transformers"
                )

    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings using sentence-transformers."""
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


class ChromaDBDefaultStrategy(EmbeddingStrategy):
    """ChromaDB's default embedding function."""

    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings using ChromaDB's default function.

        Note: This is a placeholder - ChromaDB will handle embeddings internally.
        """
        # ChromaDB will use its own default embedding function
        # We return an empty list as a signal to use ChromaDB's default
        return []


class VectorDBManager:
    """Manager for vector database operations with ChromaDB."""

    def __init__(self, config: EmbeddingConfig):
        """Initialize the vector database manager.

        Args:
            config: Embedding configuration
        """
        self.config = config
        self.client = None
        self.collection = None
        self.embedding_strategy = self._initialize_embedding_strategy()

    def _initialize_embedding_strategy(self) -> Optional[EmbeddingStrategy]:
        """Initialize the appropriate embedding strategy based on config."""
        if not self.config.enabled:
            return None

        if self.config.strategy == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI embeddings")
            return OpenAIEmbeddingStrategy(
                api_key=self.config.openai_api_key, model=self.config.openai_model
            )
        elif self.config.strategy == "claude":
            if not self.config.anthropic_api_key:
                raise ValueError(
                    "Anthropic/Voyage API key is required for Claude embeddings"
                )
            return ClaudeEmbeddingStrategy(api_key=self.config.anthropic_api_key)
        elif self.config.strategy == "sentence-transformers":
            return SentenceTransformersStrategy(
                model_name=self.config.sentence_transformers_model
            )
        elif self.config.strategy == "chromadb-default":
            return ChromaDBDefaultStrategy()
        else:
            raise ValueError(f"Unknown embedding strategy: {self.config.strategy}")

    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection.

        Raises:
            ImportError: If chromadb package is not available
            RuntimeError: If ChromaDB initialization fails
        """
        if self.client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as e:
            raise ImportError(
                "chromadb package is required for vector embeddings. "
                "Install with: pip install chromadb or use: terraform-ingest install-deps"
            ) from e

        try:
            # Determine chromadb path with precedence: env var > config
            chromadb_path = os.getenv(
                "TERRAFORM_INGEST_CHROMADB_PATH", self.config.chromadb_path
            )

            # Initialize client
            if self.config.chromadb_host:
                # Client/server mode
                self.client = chromadb.HttpClient(
                    host=self.config.chromadb_host, port=self.config.chromadb_port
                )
            else:
                # Persistent local mode
                Path(chromadb_path).mkdir(parents=True, exist_ok=True)
                self.client = chromadb.PersistentClient(
                    path=chromadb_path,
                    settings=Settings(anonymized_telemetry=False),
                )

            # Get or create collection
            if self.config.strategy == "chromadb-default":
                # Use ChromaDB's default embedding function
                self.collection = self.client.get_or_create_collection(
                    name=self.config.collection_name,
                    metadata={"description": "Terraform module embeddings"},
                )
            else:
                # Use custom embedding function
                from chromadb.utils import embedding_functions

                if self.config.strategy == "openai":
                    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                        api_key=self.config.openai_api_key,
                        model_name=self.config.openai_model,
                    )
                elif self.config.strategy == "sentence-transformers":
                    embedding_function = (
                        embedding_functions.SentenceTransformerEmbeddingFunction(
                            model_name=self.config.sentence_transformers_model
                        )
                    )
                else:
                    # For Claude/Voyage, we'll need to create custom embeddings
                    embedding_function = None

                if embedding_function:
                    self.collection = self.client.get_or_create_collection(
                        name=self.config.collection_name,
                        embedding_function=embedding_function,
                        metadata={"description": "Terraform module embeddings"},
                    )
                else:
                    # Fallback to default
                    self.collection = self.client.get_or_create_collection(
                        name=self.config.collection_name,
                        metadata={"description": "Terraform module embeddings"},
                    )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize ChromaDB: {e}. "
                "Check your chromadb configuration and ensure the package is properly installed."
            ) from e

    def _generate_document_id(self, summary: TerraformModuleSummary) -> str:
        """Generate unique ID based on repo:ref:path.

        Args:
            summary: Terraform module summary

        Returns:
            Unique document ID
        """
        id_string = f"{summary.repository}:{summary.ref}:{summary.path}"
        # Use hash to ensure valid ID format
        return hashlib.sha256(id_string.encode()).hexdigest()

    def _prepare_document_text(self, summary: TerraformModuleSummary) -> str:
        """Prepare text content for embedding.

        Args:
            summary: Terraform module summary

        Returns:
            Combined text for embedding
        """
        parts = []

        # Module description
        if self.config.include_description and summary.description:
            parts.append(f"Description: {summary.description}")

        # README content
        if self.config.include_readme and summary.readme_content:
            # Limit README to first 2000 characters to avoid token limits
            readme_excerpt = summary.readme_content[:2000]
            parts.append(f"README: {readme_excerpt}")

        # Variables
        if self.config.include_variables and summary.variables:
            var_texts = []
            for var in summary.variables:
                var_text = f"{var.name}"
                if var.description:
                    var_text += f": {var.description}"
                if var.type:
                    var_text += f" (type: {var.type})"
                var_texts.append(var_text)
            parts.append(f"Variables: {', '.join(var_texts)}")

        # Outputs
        if self.config.include_outputs and summary.outputs:
            output_texts = []
            for output in summary.outputs:
                output_text = f"{output.name}"
                if output.description:
                    output_text += f": {output.description}"
                output_texts.append(output_text)
            parts.append(f"Outputs: {', '.join(output_texts)}")

        # Resource types (from providers and modules)
        if self.config.include_resource_types:
            resource_types = []
            for provider in summary.providers:
                resource_types.append(f"{provider.name} provider")
            for module in summary.modules:
                resource_types.append(f"module: {module.source}")
            if resource_types:
                parts.append(f"Resources: {', '.join(resource_types)}")

        return "\n\n".join(parts)

    def _prepare_metadata(self, summary: TerraformModuleSummary) -> Dict[str, Any]:
        """Prepare metadata for filtering.

        Args:
            summary: Terraform module summary

        Returns:
            Metadata dictionary
        """
        metadata = {
            "repository": summary.repository,
            "ref": summary.ref,
            "path": summary.path,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        # Provider (normalized - take first one if multiple)
        if summary.providers:
            metadata["provider"] = summary.providers[0].name
            # Store all providers as a comma-separated string
            metadata["providers"] = ",".join([p.name for p in summary.providers])
        else:
            metadata["provider"] = "unknown"
            metadata["providers"] = ""

        # Extract tags from module path or description
        tags = []
        if summary.path and summary.path != ".":
            # Use path components as tags
            path_parts = summary.path.replace("\\", "/").split("/")
            tags.extend([p for p in path_parts if p and p != "."])

        # Add provider names as tags
        for provider in summary.providers:
            if provider.name:
                tags.append(provider.name)

        metadata["tags"] = ",".join(tags) if tags else ""

        return metadata

    def upsert_module(self, summary: TerraformModuleSummary) -> str:
        """Insert or update a module in the vector database.

        Args:
            summary: Terraform module summary

        Returns:
            Document ID
        """
        if not self.config.enabled:
            return ""

        self._initialize_chromadb()

        doc_id = self._generate_document_id(summary)
        document_text = self._prepare_document_text(summary)
        metadata = self._prepare_metadata(summary)

        # Check if document already exists
        try:
            existing = self.collection.get(ids=[doc_id])
            exists = len(existing["ids"]) > 0
        except Exception:
            exists = False

        if exists:
            # Update existing document
            self.collection.update(
                ids=[doc_id], documents=[document_text], metadatas=[metadata]
            )
        else:
            # Add new document
            self.collection.add(
                ids=[doc_id], documents=[document_text], metadatas=[metadata]
            )

        return doc_id

    def search_modules(
        self, query: str, filters: Optional[Dict[str, Any]] = None, n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for modules using hybrid search.

        Args:
            query: Search query
            filters: Optional metadata filters
            n_results: Number of results to return

        Returns:
            List of matching modules with scores
        """
        if not self.config.enabled:
            return []

        self._initialize_chromadb()

        # Prepare where clause for metadata filtering
        where_clause = None
        if filters:
            where_clause = {}
            for key, value in filters.items():
                if key in ["repository", "ref", "path", "provider"]:
                    where_clause[key] = value

        # Perform vector search
        results = self.collection.query(
            query_texts=[query], n_results=n_results, where=where_clause
        )

        # Format results
        formatted_results = []
        if results and results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                formatted_results.append(
                    {
                        "id": results["ids"][0][i],
                        "document": (
                            results["documents"][0][i] if results["documents"] else None
                        ),
                        "metadata": (
                            results["metadatas"][0][i] if results["metadatas"] else {}
                        ),
                        "distance": (
                            results["distances"][0][i] if results["distances"] else None
                        ),
                    }
                )

        return formatted_results

    def delete_module(self, summary: TerraformModuleSummary) -> bool:
        """Delete a module from the vector database.

        Args:
            summary: Terraform module summary

        Returns:
            True if deleted, False otherwise
        """
        if not self.config.enabled:
            return False

        self._initialize_chromadb()

        doc_id = self._generate_document_id(summary)

        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        if not self.config.enabled:
            return {"enabled": False}

        self._initialize_chromadb()

        count = self.collection.count()

        return {
            "enabled": True,
            "collection_name": self.config.collection_name,
            "document_count": count,
            "embedding_strategy": self.config.strategy,
        }
