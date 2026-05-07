"""Centralized logging configuration for Camera Follower Bot.

This module provides a consistent logging setup across the application.
It supports:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Configuration via environment variables
- Output to stdout and/or file
"""

import logging
import os
import sys
from typing import Optional


# Default configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_ENV_VAR = "LOG_LEVEL"
LOG_FILE_ENV_VAR = "LOG_FILE"
LOG_FORMAT_ENV_VAR = "LOG_FORMAT"
LOG_DATE_FORMAT_ENV_VAR = "LOG_DATE_FORMAT"

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

def get_log_level_from_env(default: int = DEFAULT_LOG_LEVEL) -> int:
    """Return the configured log level from the environment."""
    level_name = os.getenv(LOG_LEVEL_ENV_VAR, "").strip().upper()
    if not level_name:
        return default
    return LOG_LEVELS.get(level_name, default)


def setup_logging(
    name: Optional[str] = None,
    level: Optional[int] = None,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
) -> logging.Logger:
    """Setup and configure logging for the application.
    
    Args:
        name: Logger name (typically __name__). If None, returns root logger.
        level: Log level (e.g., logging.INFO). If None, uses environment variable or default.
        log_file: Path to log file. If None, uses LOG_FILE env var. If still None, logs to stdout only.
        format_string: Custom log format string. If None, uses default format.
        date_format: Custom date format string. If None, uses default format.
        
    Returns:
        Configured logger instance
    """
    # Get logger
    logger = logging.getLogger(name) if name else logging.getLogger()
    
    # Only configure if not already configured
    if logger.handlers:
        return logger
    
    # Determine log level
    if level is None:
        level = get_log_level_from_env()
    logger.setLevel(level)
    
    # Create formatter
    if log_file is None:
        log_file = os.getenv(LOG_FILE_ENV_VAR)
    fmt = format_string or os.getenv(LOG_FORMAT_ENV_VAR, DEFAULT_LOG_FORMAT)
    datefmt = date_format or os.getenv(LOG_DATE_FORMAT_ENV_VAR, DEFAULT_DATE_FORMAT)
    formatter = logging.Formatter(fmt, datefmt=datefmt)
    
    # Add stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    
    # Add file handler if log file specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning("Failed to setup file logging to %s: %s", log_file, e)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    This is a convenience function that ensures logging is configured.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return setup_logging(name)
