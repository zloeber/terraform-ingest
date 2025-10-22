"""Data models for terraform-ingest."""

from typing import List, Optional, Dict, Any
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
    readme_content: Optional[str] = None


class RepositoryConfig(BaseModel):
    """Configuration for a repository to ingest."""
    url: str
    name: Optional[str] = None
    branches: List[str] = Field(default_factory=lambda: ["main"])
    include_tags: bool = True
    max_tags: Optional[int] = 10
    path: str = "."
    recursive: bool = False
    ignore_default_branch: bool = False


class McpConfig(BaseModel):
    """Configuration for the MCP (Model Context Protocol) service."""
    auto_ingest: bool = False
    ingest_on_startup: bool = False
    refresh_interval_hours: Optional[int] = None
    config_file: str = "config.yaml"


class IngestConfig(BaseModel):
    """Configuration for the ingestion process."""
    repositories: List[RepositoryConfig]
    output_dir: str = "./output"
    clone_dir: str = "./repos"
    mcp: Optional[McpConfig] = None
