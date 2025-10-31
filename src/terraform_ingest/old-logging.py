#!/usr/bin/env python

"""
logging class that does general logging via loguru and prints to the console via rich.
"""

import os
import json
import logging
import sys
from typing import Any, Literal, Optional, Protocol, Union

from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr, ConfigDict
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

# Disable loguru's default handler to prevent unwanted stderr output
logger.remove()

# Global handler ID to ensure all loggers share the same handler
_global_handler_id: Optional[int] = None
_handler_initialized: bool = False


class NullStream:
    """A stream that discards all writes.

    Used when running in stdio mode and /dev/tty is not available.
    """

    def write(self, message: str) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


def get_console_stream():
    # Prefer a real terminal device if possible
    try:
        if os.name == "nt":
            return open("CON", "w")  # Windows console device
        else:
            return open("/dev/tty", "w")  # Unix-like systems
    except Exception:
        # Fallback to NullStream if no console is available (prevents stderr pollution in stdio mode)
        return NullStream()


def get_stdio_safe_stream():
    """Get a stream that won't interfere with stdio protocol.

    In stdio mode, returns NullStream to suppress all output.
    Otherwise, tries to use /dev/tty first (so output still appears on terminal).
    Falls back to a null stream if /dev/tty is not available.

    Returns:
        File object that writes to /dev/tty, NullStream, or discards output
    """
    # In stdio mode, suppress all logging
    if _is_stdio_mode():
        return NullStream()

    try:
        if os.name == "nt":
            return open("CON", "w")  # Windows console device
        else:
            # Try to open /dev/tty
            return open("/dev/tty", "w")
    except Exception:
        # Fallback to null stream (no stderr output in stdio mode)
        return NullStream()


def _initialize_global_handler(
    console_file_object: Optional[Any] = None,
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: str = "./logs/terraform-ingest.log",
    rotation: str = "500 MB",
    retention: str = "10 days",
    backtrace: bool = True,
    diagnose: bool = True,
    json_logs: bool = False,
    minimal_console: bool = False,
) -> None:
    """Initialize the global handler once to avoid duplicate handlers."""
    global _global_handler_id, _handler_initialized

    if _handler_initialized:
        return

    _handler_initialized = True

    # Choose formatting
    if json_logs or minimal_console:
        log_format = "{message}"
        serialize = json_logs
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<dim>{file}:{module}</dim> - "
            "<level>{message}</level>"
        )
        serialize = False

    # Console sink
    console_sink = (
        console_file_object
        if console_file_object is not None
        else get_stdio_safe_stream()
    )
    _global_handler_id = logger.add(
        console_sink,
        level=log_level,
        format=log_format,
        backtrace=backtrace,
        diagnose=diagnose,
        serialize=serialize,
        enqueue=True,
    )

    # Optional file sink
    if log_to_file:
        logger.add(
            log_file_path,
            level=log_level,
            format=log_format,
            rotation=rotation,
            retention=retention,
            backtrace=backtrace,
            diagnose=diagnose,
            serialize=serialize,
            enqueue=True,
        )


class LoggerProtocol(Protocol):
    """
    Protocol for the logger interface.
    This includes:
        Standard log methods (info, debug, error, etc.)
        Rich printing methods (print_json, print_info, print_task_status, etc.)
        Optional console formatting methods (header, footer, etc.)
        Return type of Union[None, Exception]
    Notes:
        - All the ... are placeholders for the actual methods per the Protocol definition
        - This is a workaround to allow for the logger to be injected into classes that don't inherit from LoggingModel
    """

    # === Core logging methods ===
    def debug(self, message: str) -> Union[None, Exception]: ...
    def info(self, message: str) -> Union[None, Exception]: ...
    def warning(self, message: str) -> Union[None, Exception]: ...
    def error(self, message: str) -> Union[None, Exception]: ...
    def critical(self, message: str) -> Union[None, Exception]: ...
    def exception(self, message: str) -> Union[None, Exception]: ...

    # === Print helpers ===
    def print_info(self, message: str) -> Union[None, Exception]: ...
    def print_debug(
        self, message: str, title: str = "Debug Information"
    ) -> Union[None, Exception]: ...
    def print_debug_json(
        self, data: dict[str, Any], title: str = "Debug JSON Data"
    ) -> Union[None, Exception]: ...
    def print_json(
        self, data: dict[str, Any], title: str = "JSON Data"
    ) -> Union[None, Exception]: ...
    def print_error(self, error_message: str) -> Union[None, Exception]: ...
    def print_success(self, message: str) -> Union[None, Exception]: ...
    def print_input(self, input_data: dict[str, Any]) -> Union[None, Exception]: ...
    def print_output(self, output_data: Any) -> Union[None, Exception]: ...
    def print_agent_message(
        self, agent_name: str, message: str, style: str = "agent"
    ) -> Union[None, Exception]: ...
    def print_task_status(
        self, task_name: str, status: str, details: Optional[str] = None
    ) -> Union[None, Exception]: ...
    def print_crew_status(
        self, message: str, status_type: str = "info"
    ) -> Union[None, Exception]: ...

    # === Console formatting ===
    def header(
        self, text: str, console: Optional[bool] = None
    ) -> Union[None, Exception]: ...
    def footer(self, text: str, console: bool = True) -> Union[None, Exception]: ...
    def line(self, console: bool = True) -> Union[None, Exception]: ...
    def success(self, text: str, console: bool = True) -> Union[None, Exception]: ...
    def proc_out(self, text: str, console: bool = True) -> Union[None, Exception]: ...
    def echo(
        self, text: str, color: str = "", dim: bool = False, console: bool = True
    ) -> Union[None, Exception]: ...
    def param(
        self, text: str, value: str, status: str, console: bool = True
    ) -> Union[None, Exception]: ...
    def config_element(
        self,
        name: str = "",
        value: str = "",
        separator: str = ": ",
        console: bool = True,
    ) -> Union[None, Exception]: ...

    # Add any others you rely on via injection (e.g. print_json, print_info)


# Logger configuration
class LoggerConfig(BaseModel):
    """
    Pydantic model for unified logger configuration.
    """

    # Logging configuration
    name: Optional[str] = Field(default="metagit", description="Logger name.")
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"] = (
        Field(default="INFO", description="Logging level.")
    )
    log_to_file: bool = Field(default=False, description="Whether to log to a file.")
    log_file_path: str = Field(default="app.log", description="Path to the log file.")
    json_logs: bool = Field(
        default=False, description="Whether to output logs in JSON format."
    )
    rotation: str = Field(default="10 MB", description="Log file rotation policy.")
    retention: str = Field(default="7 days", description="Log file retention policy.")
    backtrace: bool = Field(default=False, description="Enable backtrace in logs.")
    diagnose: bool = Field(default=False, description="Enable diagnose in logs.")

    # Console output configuration
    minimal_console: bool = Field(
        default=False, description="Use minimal console output format."
    )
    use_rich_console: bool = Field(
        default=True, description="Whether to use rich console formatting."
    )
    terse: bool = Field(
        default=False, description="Use terse output format (no borders or titles)."
    )
    console_stream: str = Field(
        default="/dev/tty",
        description="Custom stream for console output (defaults to /dev/tty for TTY output).",
    )
    console_file_object: Optional[Any] = Field(
        default=None,
        description="Optional file object for console output. If provided, takes precedence over console_stream path.",
    )

    model_config = ConfigDict(env_prefix="LOG_")


LOG_LEVEL_MAP: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

LOG_LEVELS: dict[int, int] = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG,
}  #: a mapping of `verbose` option counts to logging levels


class UnifiedLogger(LoggerProtocol):
    def __init__(self, config: LoggerConfig):
        self.config = config
        self.debug_mode = config.log_level in ("DEBUG", "TRACE")

        # Initialize rich console if enabled
        self.console = None
        if config.use_rich_console:
            theme = Theme(
                {
                    "info": "cyan",
                    "success": "green",
                    "warning": "yellow",
                    "error": "red",
                    "debug": "dim cyan",
                    "agent": "magenta",
                    "task": "blue",
                    "crew": "bold green",
                    "input": "bold yellow",
                    "output": "bold white",
                    "json": "bold cyan",
                }
            )
            # Use provided file object if available, otherwise try to open console_stream path
            console_file = None
            try:
                if config.console_file_object is not None:
                    console_file = config.console_file_object
                else:
                    console_file = open(config.console_stream, "w")
                self._console_file = console_file  # Store reference for flushing
                self.console = Console(file=console_file, theme=theme)
            except (OSError, IOError):
                # Fallback to stdout if console stream fails
                self.console = Console(theme=theme)

        # Console sink - use configured stream (e.g., /dev/tty or NullStream)
        console_sink = (
            config.console_file_object
            if config.console_file_object is not None
            else sys.stdout
        )

        # Initialize global handler (only happens on first call)
        _initialize_global_handler(
            console_file_object=console_sink,
            log_level=config.log_level,
            log_to_file=config.log_to_file,
            log_file_path=config.log_file_path,
            rotation=config.rotation,
            retention=config.retention,
            backtrace=config.backtrace,
            diagnose=config.diagnose,
            json_logs=config.json_logs,
            minimal_console=config.minimal_console,
        )

        self._intercept_std_logging()

    def set_level(
        self, level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]
    ) -> Union[None, Exception]:
        """
        Set the logging level for all handlers.
        Args:
            level: The new logging level to set
        """
        try:
            self.config.log_level = level
            self.debug_mode = level == "DEBUG" or level == "TRACE"
            # Note: Global handler level is already managed by _initialize_global_handler
            # Changing log level here would affect all loggers, so we just update the config
            return None
        except Exception as e:
            return e

    def _intercept_std_logging(self) -> Union[None, Exception]:
        """Intercept standard logging module output to loguru."""
        try:

            class InterceptHandler(logging.Handler):
                def emit(self, record: logging.LogRecord) -> None:
                    try:
                        level = logger.level(record.levelname).name
                    except ValueError:
                        level = record.levelno
                    frame, depth = logging.currentframe(), 2
                    while frame and frame.f_code.co_filename == logging.__file__:
                        frame = frame.f_back
                        depth += 1
                    logger.opt(depth=depth, exception=record.exc_info).log(
                        level, record.getMessage()
                    )

            logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
            return None
        except Exception as e:
            return e

    def get_logger(self) -> Union[Any, Exception]:
        """Get the underlying loguru logger instance."""
        try:
            return logger
        except Exception as e:
            return e

    def flush_logs(self) -> Union[None, Exception]:
        """
        Flush all logs immediately to avoid buffering issues.
        Flushes both loguru handlers and the console file object.
        """
        try:
            # Flush loguru logger
            logger.complete()

            # Flush console file if it exists and is not stdout/stderr
            if self._console_file is not None and hasattr(self._console_file, "flush"):
                try:
                    self._console_file.flush()
                except (OSError, ValueError):
                    # File might be closed or not flushable
                    pass

            return None
        except Exception as e:
            return e

    def print_debug(
        self, message: str, title: str = "Debug Information"
    ) -> Union[None, Exception]:
        """Print debug messages with rich formatting."""
        try:
            if self.debug_mode:
                self._format_output(message, "debug", title)
                logger.debug(message)
            return None
        except Exception as e:
            return e

    def print_agent_message(
        self, agent_name: str, message: str, style: str = "agent"
    ) -> Union[None, Exception]:
        """Print a message from an agent with rich formatting."""
        try:
            self._format_output(message, style, agent_name)
            logger.info(f"Agent {agent_name}: {message}")
            return None
        except Exception as e:
            return e

    def print_task_status(
        self, task_name: str, status: str, details: Union[str, None] = None
    ) -> Union[None, Exception]:
        """Print task status information with rich formatting."""
        try:
            content = f"{task_name}\nStatus: {status}"
            if details:
                content += f"\n\n{details}"
            self._format_output(content, "task", "Task Update")
            logger.info(
                f"Task {task_name} - Status: {status}"
                + (f" - {details}" if details else "")
            )
            return None
        except Exception as e:
            return e

    def print_crew_status(
        self, message: str, status_type: str = "info"
    ) -> Union[None, Exception]:
        """Print crew status messages with rich formatting."""
        try:
            self._format_output(message, status_type, "Crew Status")
            logger.info(f"Crew Status: {message}")
            return None
        except Exception as e:
            return e

    def print_input(self, input_data: dict[str, Any]) -> Union[None, Exception]:
        """Print input data with rich formatting."""
        try:
            self._format_output(str(input_data), "input", "Input Data")
            logger.info(f"Input: {input_data}")
            return None
        except Exception as e:
            return e

    def print_output(self, output_data: Any) -> Union[None, Exception]:
        """Print output data with rich formatting."""
        try:
            self._format_output(str(output_data), "output", "Output Data")
            logger.info(f"Output: {output_data}")
            return None
        except Exception as e:
            return e

    def print_error(self, error_message: str) -> Union[None, Exception]:
        """Print error messages with rich formatting."""
        try:
            self._format_output(error_message, "error", "Error")
            logger.error(error_message)
            return None
        except Exception as e:
            return e

    def print_success(self, message: str) -> Union[None, Exception]:
        """Print success messages with rich formatting."""
        try:
            self._format_output(message, "success", "Success")
            logger.info(message)
            return None
        except Exception as e:
            return e

    def print_info(self, message: str) -> Union[None, Exception]:
        """Print informational messages with rich formatting."""
        try:
            self._format_output(message, "info", "Info")
            logger.info(message)
            return None
        except Exception as e:
            return e

    def print_json(
        self, data: dict[str, Any], title: str = "JSON Data"
    ) -> Union[None, Exception]:
        """Print JSON data with rich formatting and syntax highlighting."""
        try:
            json_str = json.dumps(data, indent=2)
            self._format_output(json_str, "json", title)
            logger.info(json_str)
            return None
        except Exception as e:
            return e

    def print_debug_json(
        self, data: dict[str, Any], title: str = "Debug JSON Data"
    ) -> Union[None, Exception]:
        """Print JSON data only if in debug mode."""
        try:
            if self.debug_mode:
                self.print_json(data, title)
            return None
        except Exception as e:
            return e

    # Direct loguru methods
    def debug(self, message: str) -> Union[None, Exception]:
        """Log a debug message."""
        try:
            logger.opt(depth=2).debug(message)
            return None
        except Exception as e:
            return e

    def info(self, message: str) -> Union[None, Exception]:
        """Log an info message."""
        try:
            logger.opt(depth=2).info(message)
            return None
        except Exception as e:
            return e

    def warning(self, message: str) -> Union[None, Exception]:
        """Log a warning message."""
        try:
            logger.opt(depth=2).warning(message)
            return None
        except Exception as e:
            return e

    def error(self, message: str) -> Union[None, Exception]:
        """Log an error message."""
        try:
            logger.opt(depth=2).error(message)
            return None
        except Exception as e:
            return e

    def critical(self, message: str) -> Union[None, Exception]:
        """Log a critical message."""
        try:
            logger.opt(depth=2).critical(message)
            return None
        except Exception as e:
            return e

    def exception(self, message: str) -> Union[None, Exception]:
        """Log an exception with traceback."""
        try:
            logger.opt(depth=2).exception(message)
            return None
        except Exception as e:
            return e

    def _format_output(
        self, message: str, style: str, title: Union[str, None] = None
    ) -> Union[None, Exception]:
        """
        Helper to format and print output using rich console.
        Args:
            message (str): The message to print.
            style (str): The rich style to use.
            title (str, optional): The panel title. Defaults to None.
        """
        try:
            if self.console and not self.config.minimal_console:
                if self.config.terse:
                    self.console.print(f"[{style}]{message}[/{style}]")
                else:
                    panel_title = f"[{style}]{title}[/{style}]" if title else None
                    self.console.print(
                        Panel(
                            f"[{style}]{message}[/{style}]",
                            title=panel_title,
                            expand=False,
                        )
                    )
            elif not self.config.json_logs:
                # Fallback for non-rich, non-json logging
                print(f"{title}: {message}" if title else message)
            return None
        except Exception as e:
            return e

    def header(self, text: str, console: bool = None) -> Union[None, Exception]:
        """Prints a header"""
        try:
            if console is None:
                console = self.config.use_rich_console
            if console:
                self.console.rule(f"[bold green]{text}")
            else:
                print(f"### {text} ###")
            return None
        except Exception as e:
            return e

    def param(
        self, text: str, value: str, status: str, console: bool = True
    ) -> Union[None, Exception]:
        """Prints a parameter line"""
        try:
            if console:
                self.console.print(
                    f"[dim] {text} [/dim][bold cyan]{value}[/bold cyan] [bold green]({status})[/bold green]"
                )
            else:
                print(f"{text} {value} ({status})")
            return None
        except Exception as e:
            return e

    def config_element(
        self,
        name: str = "",
        value: str = "",
        separator: str = ": ",
        console: bool = True,
    ) -> Union[None, Exception]:
        """Prints a config element"""
        try:
            if console:
                self.console.print(
                    f"[bold white]  {name}[/bold white]{separator}{value}"
                )
            else:
                print(f"  {name}{separator}{value}")
            return None
        except Exception as e:
            return e

    def footer(self, text: str, console: bool = True) -> Union[None, Exception]:
        """Prints a footer"""
        try:
            if console:
                self.console.rule(f"[bold green]{text}")
            else:
                print(f"### {text} ###")
            return None
        except Exception as e:
            return e

    def proc_out(self, text: str, console: bool = True) -> Union[None, Exception]:
        """Prints a process output"""
        try:
            if console:
                self.console.print(f"[dim]{text}[/dim]")
            else:
                print(text)
            return None
        except Exception as e:
            return e

    def line(self, console: bool = True) -> Union[None, Exception]:
        """Prints a line"""
        try:
            if console:
                self.console.print("")
            else:
                print("")
            return None
        except Exception as e:
            return e

    def success(self, text: str, console: bool = True) -> Union[None, Exception]:
        """Prints a success message"""
        try:
            if console:
                self.console.print(f"[bold green]{text}[/bold green]")
            return None
        except Exception as e:
            return e

    def echo(
        self, text: str, color: str = "", dim: bool = False, console: bool = True
    ) -> Union[None, Exception]:
        """
        Echo text to console with optional color and dimming.
        Args:
            text: Text to echo
            color: Color to use
            dim: Whether to dim the text
            console: Whether to output to console
        """
        try:
            if console and self.console:
                style = f"{color} dim" if dim else color
                self.console.print(text, style=style)
            return None
        except Exception as e:
            return e


# Logger instance caches to prevent duplicate handlers
_silent_logger_cache: Optional[Any] = None
_mcp_logger_cache: Optional[Any] = None
_default_loggers_cache: dict[str, Any] = {}


def _is_stdio_mode() -> bool:
    """Check if running in stdio mode.

    When the MCP server runs in stdio mode, we should suppress logs
    to avoid corrupting the JSON protocol.

    Returns:
        True if running in stdio mode, False otherwise
    """
    try:
        from terraform_ingest.mcp_service import MCPContext

        return MCPContext.get_instance().stdio_mode
    except Exception:
        # If we can't access MCPContext, assume we're not in stdio mode
        return False


def get_null_logger(name: str = "null") -> Any:
    """Get a logger that discards all output (for stdio mode).

    Returns:
        UnifiedLogger instance that outputs to NullStream
    """
    config = LoggerConfig(name=name, console_file_object=NullStream())
    return UnifiedLogger(config)


class StdioAwareLoggerProxy:
    """Proxy logger that checks stdio mode on each call.

    When in stdio mode, all logging is suppressed to protect the JSON protocol.
    Otherwise, logs are passed to the actual logger.

    This proxy is created at module-import time, but defers checking stdio_mode
    until each logging call, allowing the MCPContext to be initialized after
    module import.
    """

    def __init__(self, actual_logger: Any, null_logger: Any):
        self._actual_logger = actual_logger
        self._null_logger = null_logger

    def _get_active_logger(self) -> Any:
        """Get the appropriate logger based on current stdio mode."""
        if _is_stdio_mode():
            return self._null_logger
        return self._actual_logger

    def debug(self, message: str) -> Any:
        return self._get_active_logger().debug(message)

    def info(self, message: str) -> Any:
        return self._get_active_logger().info(message)

    def warning(self, message: str) -> Any:
        return self._get_active_logger().warning(message)

    def error(self, message: str) -> Any:
        return self._get_active_logger().error(message)

    def critical(self, message: str) -> Any:
        return self._get_active_logger().critical(message)

    def exception(self, message: str) -> Any:
        return self._get_active_logger().exception(message)

    def flush_logs(self) -> Any:
        return self._get_active_logger().flush_logs()

    # Forward other attributes to the actual logger
    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_active_logger(), name)


def get_silent_logger() -> Any:
    """Get a logger that won't interfere with stdio protocol in MCP mode.

    This logger outputs to /dev/tty if available (so terminal users see logs),
    or to a null stream if /dev/tty is not available (e.g., in containers).
    This ensures logs never interfere with the JSON protocol on stdio.

    Returns:
        UnifiedLogger instance configured to output safely in stdio mode
    """
    global _silent_logger_cache
    if _silent_logger_cache is not None:
        return _silent_logger_cache

    console_file_object = get_stdio_safe_stream()
    config = LoggerConfig(name="silent", console_file_object=console_file_object)
    _silent_logger_cache = UnifiedLogger(config)
    return _silent_logger_cache


def get_logger(name: str = __name__) -> Any:
    """
    Get a logger instance with dynamic stdio mode awareness.

    When in stdio mode, this logger will suppress all output to prevent
    corrupting the JSON protocol. The mode is checked on each call, allowing
    MCPContext to be initialized after module import.

    Args:
        name: Logger name

    Returns:
        StdioAwareLoggerProxy that wraps the actual logger
    """
    global _default_loggers_cache
    if name not in _default_loggers_cache:
        config = LoggerConfig(name=name)
        actual_logger = UnifiedLogger(config)
        null_logger = get_null_logger(name)
        proxy_logger = StdioAwareLoggerProxy(actual_logger, null_logger)
        _default_loggers_cache[name] = proxy_logger

    return _default_loggers_cache[name]


def get_mcp_logger(name: str = "mcp") -> Any:
    """
    Get a logger instance configured for MCP service with dynamic stdio mode awareness.

    When in stdio mode, this logger will suppress all output to prevent
    corrupting the JSON protocol. Otherwise, outputs are directed to
    /dev/tty or a safe fallback stream.

    This logger is optimized for MCP services and includes:
    - Console output directed to the appropriate terminal device (/dev/tty on Unix, CON on Windows)
    - Immediate log flushing via flush_logs() method to avoid buffering issues
    - In stdio mode, all output is discarded (checked dynamically on each call)

    Args:
        name: Logger name (defaults to "mcp")

    Returns:
        StdioAwareLoggerProxy that wraps the actual logger

    Example:
        >>> mcp_logger = get_mcp_logger()
        >>> mcp_logger.info("MCP service started")
        >>> mcp_logger.flush_logs()  # Ensure logs are written immediately
    """
    global _mcp_logger_cache
    if _mcp_logger_cache is not None:
        return _mcp_logger_cache

    console_file_object = get_console_stream()
    config = LoggerConfig(name=name, console_file_object=console_file_object)
    actual_logger = UnifiedLogger(config)
    null_logger = get_null_logger(name)
    proxy_logger = StdioAwareLoggerProxy(actual_logger, null_logger)
    _mcp_logger_cache = proxy_logger
    return _mcp_logger_cache


class LoggingModel(BaseModel):
    _logger: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = getattr(self, "logger", None) or logger

    @property
    def logger(self):
        return self._logger

    def set_logger(self, logger):
        self._logger = logger
