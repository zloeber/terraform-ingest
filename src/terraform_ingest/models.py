"""Data models for terraform-ingest."""

from typing import List, Optional, Any, Literal, Dict
from pydantic import BaseModel, Field


class TerraformVariable(BaseModel):
    """Model for a Terraform variable."""

    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    default: Optional[Any] = None
    required: bool = True


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
