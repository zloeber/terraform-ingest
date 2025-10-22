"""Tests for Terraform parser."""

import tempfile
from pathlib import Path
from terraform_ingest.parser import TerraformParser


def test_parser_initialization():
    """Test parser initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        parser = TerraformParser(tmpdir)
        assert parser.module_path == Path(tmpdir)


def test_parse_variables():
    """Test parsing variables from variables.tf."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample variables.tf
        variables_tf = Path(tmpdir) / "variables.tf"
        variables_tf.write_text(
            """
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_dns" {
  description = "Enable DNS support"
  type        = bool
}
"""
        )

        parser = TerraformParser(tmpdir)
        variables = parser._parse_variables()

        assert len(variables) == 2
        assert variables[0].name == "vpc_cidr"
        assert variables[0].default == "10.0.0.0/16"
        assert variables[1].name == "enable_dns"
        assert variables[1].required is True


def test_parse_outputs():
    """Test parsing outputs from outputs.tf."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample outputs.tf
        outputs_tf = Path(tmpdir) / "outputs.tf"
        outputs_tf.write_text(
            """
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_arn" {
  value = aws_vpc.main.arn
}
"""
        )

        parser = TerraformParser(tmpdir)
        outputs = parser._parse_outputs()

        assert len(outputs) == 2
        assert outputs[0].name == "vpc_id"
        assert outputs[0].description == "ID of the VPC"
        assert outputs[1].name == "vpc_arn"


def test_parse_providers():
    """Test parsing providers from terraform files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample main.tf with provider requirements
        main_tf = Path(tmpdir) / "main.tf"
        main_tf.write_text(
            """
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}
"""
        )

        parser = TerraformParser(tmpdir)
        providers = parser._parse_providers()

        assert len(providers) >= 1
        aws_provider = next((p for p in providers if p.name == "aws"), None)
        assert aws_provider is not None
        assert aws_provider.source == "hashicorp/aws"


def test_parse_modules():
    """Test parsing module references."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample main.tf with module references
        main_tf = Path(tmpdir) / "main.tf"
        main_tf.write_text(
            """
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "3.0.0"
  
  name = "my-vpc"
}
"""
        )

        parser = TerraformParser(tmpdir)
        modules = parser._parse_modules()

        assert len(modules) == 1
        assert modules[0].name == "vpc"
        assert modules[0].source == "terraform-aws-modules/vpc/aws"
        assert modules[0].version == "3.0.0"


def test_read_readme():
    """Test reading README file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample README
        readme = Path(tmpdir) / "README.md"
        readme.write_text("# Test Module\n\nThis is a test module.")

        parser = TerraformParser(tmpdir)
        content = parser._read_readme()

        assert content is not None
        assert "Test Module" in content


def test_extract_description():
    """Test extracting description from README."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample README
        readme = Path(tmpdir) / "README.md"
        readme.write_text("# Test Module\n\nThis module creates AWS VPC resources.")

        parser = TerraformParser(tmpdir)
        description = parser._extract_description()

        assert description is not None
        assert "VPC" in description


def test_parse_module_complete():
    """Test complete module parsing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample terraform files
        (Path(tmpdir) / "main.tf").write_text(
            """
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}
"""
        )

        (Path(tmpdir) / "variables.tf").write_text(
            """
variable "name" {
  description = "Name of the resource"
  type        = string
}
"""
        )

        (Path(tmpdir) / "outputs.tf").write_text(
            """
output "id" {
  description = "Resource ID"
  value       = aws_resource.main.id
}
"""
        )

        parser = TerraformParser(tmpdir)
        summary = parser.parse_module("https://github.com/test/repo", "main")

        assert summary.repository == "https://github.com/test/repo"
        assert summary.ref == "main"
        assert len(summary.variables) == 1
        assert len(summary.outputs) == 1
        assert len(summary.providers) >= 1
