"""Automatic dependency installer for optional features."""

import subprocess
import sys
import site
from typing import List

from terraform_ingest.tty_logger import setup_tty_logger

logger = setup_tty_logger()


# def _get_appropriate_logger():
#     """Get a logger appropriate for the current execution context.

#     When running in stdio mode (MCP protocol), returns a logger that outputs to /dev/tty
#     instead of stderr to avoid corrupting the JSON protocol messages. Otherwise returns
#     a regular logger that outputs to stderr.

#     Returns:
#         UnifiedLogger instance configured for the appropriate output stream
#     """
#     global _cached_logger

#     # Always check if we should update the cache based on current context
#     try:
#         from terraform_ingest.mcp_service import MCPContext

#         context = MCPContext.get_instance()
#         if context and context.stdio_mode:
#             if (
#                 _cached_logger is None
#                 or not hasattr(_cached_logger.config, "console_file_object")
#                 or _cached_logger.config.console_file_object is None
#             ):
#                 _cached_logger = get_silent_logger()
#             return _cached_logger
#     except Exception:
#         # If we can't access MCPContext, just use a regular logger
#         pass

#     if _cached_logger is None:
#         _cached_logger = get_logger(__name__)
#     return _cached_logger


class DependencyInstaller:
    """Handles automatic installation of optional dependencies."""

    # Mapping of strategies to their required packages
    STRATEGY_PACKAGES = {
        "sentence-transformers": ["sentence-transformers"],
        "openai": ["openai"],
        "claude": ["voyageai"],  # Claude uses Voyage AI for embeddings
        "chromadb-default": ["chromadb"],
    }

    # Packages needed for vector DB support
    EMBEDDING_PACKAGES = ["chromadb", "sentence-transformers", "openai", "voyageai"]

    @staticmethod
    def check_package_installed(package_name: str) -> bool:
        """Check if a package is installed.

        Uses importlib.metadata for more reliable detection, which works better
        with system-wide installations and UV tool environments.

        Args:
            package_name: Name of the package to check

        Returns:
            True if package is installed, False otherwise
        """
        try:
            # First try importlib.metadata (more reliable for system installs)
            import importlib.metadata

            try:
                importlib.metadata.version(package_name)
                return True
            except importlib.metadata.PackageNotFoundError:
                pass
        except (ImportError, Exception):
            pass

        # Fallback to __import__ for compatibility
        try:
            __import__(package_name.replace("-", "_"))
            return True
        except ImportError:
            return False

    @staticmethod
    def _refresh_sys_path():
        """Refresh sys.path to include newly installed packages.

        This is necessary after subprocess package installations to ensure
        that newly installed packages are discoverable by the current Python process.
        """
        try:
            # Re-scan site-packages directories
            site.main()

            # Also try to add site packages manually
            import sysconfig

            stdlib_packages = sysconfig.get_paths()
            for key in ["purelib", "platlib"]:
                if key in stdlib_packages:
                    path = stdlib_packages[key]
                    if path not in sys.path:
                        sys.path.insert(0, path)
        except Exception as e:
            logger.debug(f"Could not refresh sys.path: {e}")

    @staticmethod
    def get_missing_packages(packages: List[str]) -> List[str]:
        """Get list of packages that are not installed.

        Args:
            packages: List of package names to check

        Returns:
            List of package names that are missing
        """
        missing = []
        for package in packages:
            if not DependencyInstaller.check_package_installed(package):
                missing.append(package)
        return missing

    @staticmethod
    def install_packages(
        packages: List[str],
        logger=logger,
        use_uv: bool = True,
    ) -> bool:
        """Install packages using pip or uv.

        Args:
            packages: List of package names to install
            logger: Optional logger instance
            use_uv: Whether to prefer uv package manager (if available)

        Returns:
            True if installation succeeded, False otherwise
        """
        if not packages:
            return True

        # Check if packages are already installed
        still_missing = DependencyInstaller.get_missing_packages(packages)
        if not still_missing:
            logger.info("All required packages are already installed")
            return True

        logger.info(f"Installing missing packages: {', '.join(still_missing)}")

        # Try uv first if it's available
        if use_uv:
            uv_approaches = [
                # Approach 1: uv pip install without --system (for venv)
                ["uv", "pip", "install"] + still_missing,
                # Approach 2: uv pip install with --system (for uv tool installations)
                ["uv", "pip", "install", "--system"] + still_missing,
            ]

            for uv_cmd in uv_approaches:
                try:
                    logger.debug(f"Using '{' '.join(uv_cmd[:3])}' to install packages")
                    _ = subprocess.run(
                        uv_cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    logger.info("Successfully installed packages using uv")
                    DependencyInstaller._refresh_sys_path()
                    return True
                except subprocess.CalledProcessError as e:
                    logger.debug(f"uv approach failed: {e.stderr}")
                    continue
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    logger.debug("uv command not available or timed out")
                    break

            logger.debug("All uv approaches failed, falling back to pip")

        # Fall back to pip (try different approaches)
        pip_approaches = [
            # Approach 1: pip as a module via python
            [sys.executable, "-m", "pip", "install"] + still_missing,
            # Approach 2: pip command directly
            ["pip", "install"] + still_missing,
            # Approach 3: pip3 command directly
            ["pip3", "install"] + still_missing,
        ]

        for pip_cmd in pip_approaches:
            try:
                logger.debug(f"Trying: {' '.join(pip_cmd)}")
                _ = subprocess.run(
                    pip_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                logger.info("Successfully installed packages using pip")
                DependencyInstaller._refresh_sys_path()
                return True
            except subprocess.CalledProcessError as e:
                logger.debug(f"Failed: {e.stderr}")
                continue
            except (FileNotFoundError, subprocess.TimeoutExpired):
                logger.debug(f"Command not available: {pip_cmd[0]}")
                continue
            except Exception as e:
                logger.debug(f"Error with {pip_cmd[0]}: {str(e)}")
                continue

        # All approaches failed
        logger.error(
            f"Failed to install packages using any method.\n\n"
            f"Please install manually with one of these methods:\n\n"
            f"  Option 1 (pip):\n"
            f"    pip install {' '.join(still_missing)}\n\n"
            f"  Option 2 (uv with system packages):\n"
            f"    uv pip install --system {' '.join(still_missing)}\n\n"
            f"  Option 3 (uv add via pyproject):\n"
            f"    uv add {' '.join(still_missing)}\n\n"
            f"  Option 4 (reinstall tool with extras):\n"
            f"    uv tool install --force terraform-ingest[embeddings]\n\n"
            f"You may also need to upgrade pip:\n"
            f"  python -m pip install --upgrade pip"
        )
        return False

    @staticmethod
    def ensure_embedding_packages(
        logger=logger,
        strategy: str = "chromadb-default",
        auto_install: bool = True,
    ) -> bool:
        """Ensure all packages needed for embeddings are installed.

        Args:
            logger: Optional logger instance
            strategy: Embedding strategy being used
            auto_install: Whether to automatically install missing packages

        Returns:
            True if all packages are installed or successfully installed, False otherwise
        """
        # Get packages needed for the strategy
        if strategy not in DependencyInstaller.STRATEGY_PACKAGES:
            logger.warning(f"Unknown embedding strategy: {strategy}")
            return False

        required_packages = DependencyInstaller.STRATEGY_PACKAGES[strategy]

        # Check if we also need chromadb for the strategy
        if strategy != "chromadb-default":
            required_packages = list(set(required_packages + ["chromadb"]))

        missing = DependencyInstaller.get_missing_packages(required_packages)

        if not missing:
            logger.debug(f"All packages for '{strategy}' strategy are installed")
            return True

        if not auto_install:
            logger.error(
                f"Missing packages for '{strategy}' embedding strategy: {', '.join(missing)}\n"
                f"Install with:\n"
                f"  pip install terraform-ingest[embeddings]\n"
                f"Or specific packages:\n"
                f"  pip install {' '.join(missing)}"
            )
            return False

        logger.info(
            f"Missing packages for '{strategy}' embedding strategy: {', '.join(missing)}"
        )
        return DependencyInstaller.install_packages(required_packages, logger)


def ensure_embeddings_available(
    embedding_config,
    logger=logger,
    auto_install: bool = True,
) -> bool:
    """Convenience function to ensure embeddings are available.

    Args:
        embedding_config: EmbeddingConfig instance
        logger: Optional logger instance
        auto_install: Whether to automatically install missing packages

    Returns:
        True if embeddings are available or can be installed, False otherwise

    Raises:
        ImportError: If auto_install is False and packages are missing
    """

    if not embedding_config or not embedding_config.enabled:
        logger.debug("Embeddings not enabled in configuration")
        return True

    success = DependencyInstaller.ensure_embedding_packages(
        logger=logger,
        strategy=embedding_config.strategy,
        auto_install=auto_install,
    )

    if not success and not auto_install:
        raise ImportError(
            f"Missing dependencies for embedding strategy '{embedding_config.strategy}'. "
            f"Install with: pip install terraform-ingest[embeddings]"
        )

    return success
