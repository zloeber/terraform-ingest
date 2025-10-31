"""Terraform file parser for extracting module information."""

from pathlib import Path
from typing import Any, List, Optional
import hcl2
import re
from terraform_ingest.models import (
    TerraformVariable,
    TerraformOutput,
    TerraformProvider,
    TerraformModule,
    TerraformResource,
    TerraformModuleSummary,
)
from terraform_ingest.tty_logger import get_logger


class TerraformParser:
    """Parser for Terraform configuration files."""

    def __init__(self, module_path: str, logger: Optional[Any] = None):
        """Initialize the parser with a module path.

        Args:
            module_path: Path to the Terraform module
            logger: Optional logger instance. Defaults to get_logger() if not provided.
        """
        self.module_path = Path(module_path)
        self.logger = logger or get_logger(__name__)

    def parse_module(
        self, repo_url: str, ref: str, relative_path: Optional[str] = None
    ) -> TerraformModuleSummary:
        """Parse a Terraform module and return a summary."""
        variables = self._parse_variables()
        outputs = self._parse_outputs()
        providers = self._parse_providers()
        modules = self._parse_modules()
        resources = self._parse_resources()
        description = self._extract_description()
        readme_content = self._read_readme()

        # Use relative path if provided, otherwise use the full module path
        path_for_summary = relative_path if relative_path else str(self.module_path)

        return TerraformModuleSummary(
            repository=repo_url,
            ref=ref,
            path=path_for_summary,
            description=description,
            variables=variables,
            outputs=outputs,
            providers=providers,
            modules=modules,
            resources=resources,
            readme_content=readme_content,
        )

    def _parse_variables(self) -> List[TerraformVariable]:
        """Parse variables from variables.tf files."""
        variables = []
        var_files = list(self.module_path.glob("variables.tf")) + list(
            self.module_path.glob("vars.tf")
        )

        for var_file in var_files:
            try:
                with open(var_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    parsed = hcl2.loads(content)

                    if "variable" in parsed:
                        for var_list in parsed["variable"]:
                            for var_name, var_config in var_list.items():
                                var_type = var_config.get("type")
                                if isinstance(var_type, list) and len(var_type) > 0:
                                    var_type = str(var_type[0])
                                elif var_type:
                                    var_type = str(var_type)

                                default = var_config.get("default")
                                if default and isinstance(default, list):
                                    default = default[0] if len(default) > 0 else None

                                description = var_config.get("description")
                                if description and isinstance(description, list):
                                    description = (
                                        description[0] if len(description) > 0 else None
                                    )

                                variables.append(
                                    TerraformVariable(
                                        name=var_name,
                                        type=var_type,
                                        description=description,
                                        default=default,
                                        required=default is None,
                                    )
                                )
            except Exception as e:
                self.logger.error(f"Error parsing variables from {var_file}: {e}")

        return variables

    def _parse_outputs(self) -> List[TerraformOutput]:
        """Parse outputs from outputs.tf files."""
        outputs = []
        output_files = list(self.module_path.glob("outputs.tf")) + list(
            self.module_path.glob("output.tf")
        )

        for output_file in output_files:
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    parsed = hcl2.loads(content)

                    if "output" in parsed:
                        for output_list in parsed["output"]:
                            for output_name, output_config in output_list.items():
                                description = output_config.get("description")
                                if description and isinstance(description, list):
                                    description = (
                                        description[0] if len(description) > 0 else None
                                    )

                                value = output_config.get("value")
                                if value:
                                    value = str(value)

                                sensitive = output_config.get("sensitive", False)
                                if isinstance(sensitive, list):
                                    sensitive = (
                                        sensitive[0] if len(sensitive) > 0 else False
                                    )

                                outputs.append(
                                    TerraformOutput(
                                        name=output_name,
                                        description=description,
                                        value=value,
                                        sensitive=bool(sensitive),
                                    )
                                )
            except Exception as e:
                self.logger.error(f"Error parsing outputs from {output_file}: {e}")

        return outputs

    def _parse_providers(self) -> List[TerraformProvider]:
        """Parse provider requirements from terraform configuration files."""
        providers = []
        tf_files = list(self.module_path.glob("*.tf"))

        for tf_file in tf_files:
            try:
                with open(tf_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # First, try to extract provider-related blocks using regex
                    # to avoid parsing errors on complex expressions
                    self._extract_providers_regex(content, providers)

                    # Then attempt full HCL2 parsing for structured data
                    try:
                        parsed = hcl2.loads(content)

                        # Check for required_providers in terraform block
                        if "terraform" in parsed:
                            for terraform_block in parsed["terraform"]:
                                if "required_providers" in terraform_block:
                                    req_providers = terraform_block[
                                        "required_providers"
                                    ]
                                    if isinstance(req_providers, list):
                                        req_providers = (
                                            req_providers[0] if req_providers else {}
                                        )

                                    for (
                                        provider_name,
                                        provider_config,
                                    ) in req_providers.items():
                                        source = None
                                        version = None

                                        if isinstance(provider_config, dict):
                                            source = provider_config.get("source")
                                            version = provider_config.get("version")
                                        elif isinstance(provider_config, str):
                                            version = provider_config

                                        if isinstance(source, list):
                                            source = source[0] if source else None
                                        if isinstance(version, list):
                                            version = version[0] if version else None

                                        # Only add if not already extracted via regex
                                        if not any(
                                            p.name == provider_name for p in providers
                                        ):
                                            providers.append(
                                                TerraformProvider(
                                                    name=provider_name,
                                                    source=source,
                                                    version=version,
                                                )
                                            )

                        # Also check for provider blocks
                        if "provider" in parsed:
                            for provider_list in parsed["provider"]:
                                for provider_name in provider_list.keys():
                                    # Only add if not already in the list
                                    if not any(
                                        p.name == provider_name for p in providers
                                    ):
                                        providers.append(
                                            TerraformProvider(name=provider_name)
                                        )
                    except Exception as parse_error:
                        # If full parsing fails, we still have regex-extracted providers
                        self.logger.debug(
                            f"Full HCL2 parsing failed for {tf_file}: {parse_error}"
                        )

            except Exception as e:
                self.logger.error(f"Error parsing providers from {tf_file}: {e}")

        return providers

    def _extract_providers_regex(
        self, content: str, providers: List[TerraformProvider]
    ) -> None:
        """Extract provider information using regex as a fallback for complex expressions."""
        # Match provider blocks: provider "name" { ... }
        provider_pattern = r'provider\s+"([^"]+)"\s*\{'
        for match in re.finditer(provider_pattern, content):
            provider_name = match.group(1)
            if not any(p.name == provider_name for p in providers):
                providers.append(TerraformProvider(name=provider_name))

        # Match required_providers entries
        # Pattern: "provider_name" = { source = "...", version = "..." }
        req_provider_pattern = r'"([^"]+)"\s*=\s*\{\s*(?:source\s*=\s*"([^"]+)")?\s*(?:version\s*=\s*"([^"]+)")?\s*\}'
        for match in re.finditer(req_provider_pattern, content):
            provider_name = match.group(1)
            source = match.group(2)
            version = match.group(3)
            if not any(p.name == provider_name for p in providers):
                providers.append(
                    TerraformProvider(
                        name=provider_name,
                        source=source,
                        version=version,
                    )
                )

    def _parse_modules(self) -> List[TerraformModule]:
        """Parse module references from terraform configuration files."""
        modules = []
        tf_files = list(self.module_path.glob("*.tf"))

        for tf_file in tf_files:
            try:
                with open(tf_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # First try regex-based extraction for robustness
                    self._extract_modules_regex(content, modules)

                    # Then attempt full HCL2 parsing
                    try:
                        parsed = hcl2.loads(content)

                        if "module" in parsed:
                            for module_list in parsed["module"]:
                                for module_name, module_config in module_list.items():
                                    source = module_config.get("source")
                                    version = module_config.get("version")

                                    if isinstance(source, list):
                                        source = source[0] if source else None
                                    if isinstance(version, list):
                                        version = version[0] if version else None

                                    # Only add if not already extracted via regex
                                    if source and not any(
                                        m.name == module_name and m.source == source
                                        for m in modules
                                    ):
                                        modules.append(
                                            TerraformModule(
                                                name=module_name,
                                                source=source,
                                                version=version,
                                            )
                                        )
                    except Exception as parse_error:
                        # If full parsing fails, we still have regex-extracted modules
                        self.logger.debug(
                            f"Full HCL2 parsing failed for {tf_file}: {parse_error}"
                        )
            except Exception as e:
                self.logger.error(f"Error parsing modules from {tf_file}: {e}")

        return modules

    def _extract_modules_regex(
        self, content: str, modules: List[TerraformModule]
    ) -> None:
        """Extract module information using regex as a fallback for complex expressions."""
        # Match module blocks: module "name" { source = "...", version = "..." }
        module_pattern = r'module\s+"([^"]+)"\s*\{([^}]*?)\}'
        for match in re.finditer(module_pattern, content, re.DOTALL):
            module_name = match.group(1)
            module_body = match.group(2)

            # Extract source
            source_match = re.search(r'source\s*=\s*"([^"]+)"', module_body)
            source = source_match.group(1) if source_match else None

            # Extract version
            version_match = re.search(r'version\s*=\s*"([^"]+)"', module_body)
            version = version_match.group(1) if version_match else None

            if source and not any(
                m.name == module_name and m.source == source for m in modules
            ):
                modules.append(
                    TerraformModule(
                        name=module_name,
                        source=source,
                        version=version,
                    )
                )

    def _parse_resources(self) -> List[TerraformResource]:
        """Parse resource declarations from terraform configuration files."""
        resources = []
        tf_files = list(self.module_path.glob("*.tf"))

        for tf_file in tf_files:
            try:
                with open(tf_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # First try regex-based extraction for robustness
                    self._extract_resources_regex(content, resources)

                    # Then attempt full HCL2 parsing
                    try:
                        parsed = hcl2.loads(content)

                        if "resource" in parsed:
                            for resource_list in parsed["resource"]:
                                for (
                                    resource_type,
                                    resource_instances,
                                ) in resource_list.items():
                                    # resource_instances is a dict where keys are resource names
                                    # and values are the resource configurations
                                    if isinstance(resource_instances, dict):
                                        for resource_name in resource_instances.keys():
                                            # Avoid duplicates
                                            if not any(
                                                r.type == resource_type
                                                and r.name == resource_name
                                                for r in resources
                                            ):
                                                resources.append(
                                                    TerraformResource(
                                                        type=resource_type,
                                                        name=resource_name,
                                                        description=None,
                                                    )
                                                )
                    except Exception as parse_error:
                        # If full parsing fails, we still have regex-extracted resources
                        self.logger.debug(
                            f"Full HCL2 parsing failed for {tf_file}: {parse_error}"
                        )
            except Exception as e:
                self.logger.error(f"Error parsing resources from {tf_file}: {e}")

        return resources

    def _extract_resources_regex(
        self, content: str, resources: List[TerraformResource]
    ) -> None:
        """Extract resource information using regex as a fallback for complex expressions."""
        # Match resource blocks: resource "type" "name" { ... }
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        for match in re.finditer(resource_pattern, content):
            resource_type = match.group(1)
            resource_name = match.group(2)
            if not any(
                r.type == resource_type and r.name == resource_name for r in resources
            ):
                resources.append(
                    TerraformResource(
                        type=resource_type,
                        name=resource_name,
                        description=None,
                    )
                )

    def _extract_description(self) -> Optional[str]:
        """Extract module description from comments or README."""
        # Try to find description in main.tf comments
        main_tf = Path.joinpath(self.module_path, "main.tf")
        if main_tf.exists():
            try:
                with open(main_tf, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    # Look for comment blocks at the top of the file
                    description_lines = []
                    for line in lines[:20]:  # Check first 20 lines
                        line = line.strip()
                        if line.startswith("#"):
                            description_lines.append(line[1:].strip())
                        elif line and not line.startswith("//"):
                            break
                    if description_lines:
                        return " ".join(description_lines)
            except Exception:
                pass

        # Fall back to README
        readme = self._read_readme()
        if readme:
            # Extract first paragraph as description
            lines = readme.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Find the end of the first paragraph
                    paragraph = [line]
                    for next_line in lines[i + 1 :]:
                        next_line = next_line.strip()
                        if not next_line:
                            break
                        if next_line.startswith("#"):
                            break
                        paragraph.append(next_line)
                    return " ".join(paragraph)[:500]  # Limit to 500 chars

        return None

    def _read_readme(self) -> Optional[str]:
        """Read README file if it exists."""
        readme_files = ["README.md", "README.txt", "README", "readme.md"]
        for readme_name in readme_files:
            readme_path = Path.joinpath(self.module_path, readme_name)
            if readme_path.exists():
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
        return None
