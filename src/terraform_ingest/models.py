"""Data models for terraform-ingest."""

from typing import List, Optional, Any, Literal, Dict
from pydantic import BaseModel, Field

_SENTINEL = object()  # Used internally to distinguish "no default" from "default=None"


class TerraformVariable(BaseModel):
    """Model for a Terraform variable.

    Key semantics (mirrors Terraform language spec):
    - ``required`` is ``True`` iff the ``default`` *attribute* is entirely absent
      from the variable block.  A variable with ``default = null`` is optional.
    - ``has_default`` makes that distinction explicit for downstream consumers
      (MCP agents, RAG systems) that cannot distinguish a missing JSON key from
      a JSON ``null`` value.
    - ``nullable`` reflects the Terraform ``nullable`` argument (default ``True``).
      When ``False`` the module will reject an explicit ``null`` from callers.
    - ``default_semantics`` is an optional hint:
        - ``"sentinel_null"``  – ``default = null`` is used as a sentinel so the
          module can compute a real default inside ``locals``.
        - ``"literal"``        – the default is a concrete, non-null value.
    """

    name: str
    type: Optional[str] = None
    description: Optional[str] = None

    # --- default tracking ---
    has_default: bool = False
    """True if the variable block contains a ``default`` attribute (even null)."""

    default: Optional[Any] = Field(default=None)
    """Present (possibly null) only when ``has_default`` is True.
    Omitted entirely from serialised output when ``has_default`` is False."""

    default_semantics: Optional[Literal["sentinel_null", "literal"]] = None
    """Hint for agents: how to interpret the default value."""

    # --- optionality / nullability ---
    required: bool = True
    """True iff the variable has no ``default`` attribute."""

    nullable: bool = True
    """Reflects the Terraform ``nullable`` argument (defaults to ``True``)."""

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN001
        """Ensure ``required`` and ``default_semantics`` are consistent."""
        # required is always derived from has_default
        object.__setattr__(self, "required", not self.has_default)

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Omit the ``default`` field entirely when there is no default."""
        data = super().model_dump(**kwargs)
        if not self.has_default:
            data.pop("default", None)
            data.pop("default_semantics", None)
        return data

    def model_dump_json(self, **kwargs: Any) -> str:
        """JSON serialisation that omits ``default`` when there is no default."""
        import json

        return json.dumps(self.model_dump(**kwargs))


class TerraformOutput(BaseModel):
    """Model for a Terraform output."""

    name: str
    description: Optional[str] = None
    value: Optional[str] = None
    sensitive: bool = False


class TerraformProvider(BaseModel):
    """Model for a Terraform provider."""

    name: str
    source: Optional[str] = None
    version: Optional[str] = None


class TerraformModule(BaseModel):
    """Model for a Terraform module."""

    name: str
    source: str
    version: Optional[str] = None


class TerraformResource(BaseModel):
    """Model for a Terraform resource."""

    type: str
    name: str
    description: Optional[str] = None


class TerraformModuleSummary(BaseModel):
    """Summary of a Terraform module."""

    repository: str
    ref: str  # branch or tag
    path: str = "."
    description: Optional[str] = None
    variables: List[TerraformVariable] = Field(default_factory=list)
    outputs: List[TerraformOutput] = Field(default_factory=list)
    providers: List[TerraformProvider] = Field(default_factory=list)
    modules: List[TerraformModule] = Field(default_factory=list)
    resources: List[TerraformResource] = Field(default_factory=list)
    readme_content: Optional[str] = None


class RepositoryConfig(BaseModel):
    """Configuration for a repository to ingest."""

    url: str
    name: Optional[str] = None
    branches: List[str] = Field(default_factory=list)
    include_tags: bool = True
    max_tags: Optional[int] = 1
    path: str = "."
    recursive: bool = False
    exclude_paths: List[str] = Field(
        default_factory=list,
        description="List of glob patterns to exclude from ingestion (e.g., 'examples/*', 'test/*')",
    )


class McpConfig(BaseModel):
    """Configuration for the MCP (Model Context Protocol) service."""

    auto_ingest: bool = False
    ingest_on_startup: bool = False
    refresh_interval_hours: Optional[int] = None

    # Transport configuration
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 3000

    instructions: str = """
    You are a Terraform module assistant that helps users find and use infrastructure modules.

    CRITICAL RULES:
    1. ALWAYS prefer tagged release versions (e.g., v1.2.3, 1.2.3) over branch references
    2. When multiple versions exist, recommend the latest stable release
    3. Include warning comments above code blocks that use branch references instead of tags
    4. If `search_modules_vector` tool is available, use it for searching modules first

    Search Strategy:
    - Search for modules matching the user's requirements
    - Filter results to prioritize tagged releases
    - If only branch versions exist, explicitly mention this as a risk in a comment within the code you generate
    """

    # Custom prompt overrides
    prompts: Optional[Dict[str, str]] = None


class EmbeddingConfig(BaseModel):
    """Configuration for vector database embeddings."""

    enabled: bool = False
    strategy: Literal[
        "openai", "claude", "sentence-transformers", "chromadb-default"
    ] = "chromadb-default"

    # API keys for cloud embeddings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Model selection
    openai_model: str = "text-embedding-3-small"
    anthropic_model: str = "claude-3-haiku-20240307"
    sentence_transformers_model: str = "all-MiniLM-L6-v2"

    # ChromaDB configuration
    chromadb_host: Optional[str] = None  # For client/server mode
    chromadb_port: int = 8000
    chromadb_path: str = "./chromadb"  # For persistent mode
    collection_name: str = "terraform_modules"

    # Embedding content configuration
    include_description: bool = True
    include_readme: bool = True
    include_variables: bool = True
    include_outputs: bool = True
    include_resource_types: bool = True

    # Hybrid search configuration
    enable_hybrid_search: bool = True
    keyword_weight: float = 0.3  # Weight for keyword search (0.0 to 1.0)
    vector_weight: float = 0.7  # Weight for vector search (0.0 to 1.0)


class IngestConfig(BaseModel):
    """Configuration for the ingestion process."""

    repositories: List[RepositoryConfig]
    output_dir: str = "./output"
    clone_dir: str = "./repos"
    mcp: Optional[McpConfig] = None
    embedding: Optional[EmbeddingConfig] = None
