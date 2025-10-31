#!/usr/bin/env python

"""
logging class that does general logging via loguru and prints to the console via /dev/tty or equivalent
"""

import os
import sys
from loguru import logger


def get_console_sink():
    """Return a writable stream to /dev/tty (or equivalent), with fallback."""
    try:
        if os.name == "nt":
            return open("CON", "w", buffering=1)
        elif os.path.exists("/dev/tty"):
            return open("/dev/tty", "w", buffering=1)
    except Exception:
        pass
    return sys.stderr


def setup_tty_logger(level="INFO"):
    """Configure a unified Loguru logger to use /dev/tty or fallback."""
    # Remove any default loggers (stdout-based)
    logger.remove()

    # Add the /dev/tty (or fallback) sink
    logger.add(
        get_console_sink(),
        level=level,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>",
    )

    return logger


def get_logger(name: str):
    """Get a logger instance with the specified name."""
    return setup_tty_logger().bind(name=name)
