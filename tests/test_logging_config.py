"""Tests for logging configuration module."""
import logging
import os
import tempfile
import pytest

from camera_follower_bot import logging_config


def test_get_log_level_from_env_default(monkeypatch):
    """Test that default log level is INFO when LOG_LEVEL is not set."""
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    level = logging_config.get_log_level_from_env()
    assert level == logging.INFO


def test_get_log_level_from_env_debug(monkeypatch):
    """Test that LOG_LEVEL=DEBUG returns logging.DEBUG."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    level = logging_config.get_log_level_from_env()
    assert level == logging.DEBUG


def test_get_log_level_from_env_warning(monkeypatch):
    """Test that LOG_LEVEL=WARNING returns logging.WARNING."""
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    level = logging_config.get_log_level_from_env()
    assert level == logging.WARNING


def test_get_log_level_from_env_error(monkeypatch):
    """Test that LOG_LEVEL=ERROR returns logging.ERROR."""
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    level = logging_config.get_log_level_from_env()
    assert level == logging.ERROR


def test_get_log_level_from_env_critical(monkeypatch):
    """Test that LOG_LEVEL=CRITICAL returns logging.CRITICAL."""
    monkeypatch.setenv("LOG_LEVEL", "CRITICAL")
    level = logging_config.get_log_level_from_env()
    assert level == logging.CRITICAL


def test_get_log_level_from_env_case_insensitive(monkeypatch):
    """Test that log level is case insensitive."""
    monkeypatch.setenv("LOG_LEVEL", "debug")
    level = logging_config.get_log_level_from_env()
    assert level == logging.DEBUG


def test_get_log_level_from_env_invalid(monkeypatch):
    """Test that invalid log level defaults to INFO."""
    monkeypatch.setenv("LOG_LEVEL", "INVALID")
    level = logging_config.get_log_level_from_env()
    assert level == logging.INFO


def test_setup_logging_creates_logger():
    """Test that setup_logging creates a logger."""
    logger = logging_config.setup_logging("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    # Clean up
    logger.handlers.clear()


def test_setup_logging_with_custom_level():
    """Test that setup_logging respects custom log level."""
    logger = logging_config.setup_logging("test_logger_level", level=logging.WARNING)
    assert logger.level == logging.WARNING
    # Clean up
    logger.handlers.clear()


def test_setup_logging_adds_stdout_handler():
    """Test that setup_logging adds a stdout handler."""
    logger = logging_config.setup_logging("test_logger_stdout")
    assert len(logger.handlers) >= 1
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    # Clean up
    logger.handlers.clear()


def test_setup_logging_with_file(monkeypatch):
    """Test that setup_logging adds a file handler when log_file is provided."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = logging_config.setup_logging("test_logger_file", log_file=log_file)
        assert len(logger.handlers) >= 2
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        
        # Clean up
        logger.handlers.clear()
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


def test_setup_logging_with_log_file_env(monkeypatch):
    """Test that setup_logging uses LOG_FILE environment variable."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        monkeypatch.setenv("LOG_FILE", log_file)
        logger = logging_config.setup_logging("test_logger_env_file")
        assert len(logger.handlers) >= 2
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        
        # Clean up
        logger.handlers.clear()
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


def test_setup_logging_file_handler_failure(monkeypatch):
    """Test that setup_logging handles file handler creation failure gracefully."""
    # Use an invalid path that will fail
    invalid_path = "/nonexistent/directory/test.log"
    logger = logging_config.setup_logging("test_logger_fail", log_file=invalid_path)
    
    # Should still have stdout handler
    assert len(logger.handlers) >= 1
    # Should not have file handler
    assert not any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    
    # Clean up
    logger.handlers.clear()


def test_setup_logging_does_not_reconfigure():
    """Test that setup_logging doesn't add duplicate handlers."""
    logger1 = logging_config.setup_logging("test_logger_dup")
    initial_handlers = len(logger1.handlers)
    
    logger2 = logging_config.setup_logging("test_logger_dup")
    assert len(logger2.handlers) == initial_handlers
    assert logger1 is logger2
    
    # Clean up
    logger1.handlers.clear()


def test_get_logger():
    """Test that get_logger returns a configured logger."""
    logger = logging_config.get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"
    assert len(logger.handlers) >= 1
    
    # Clean up
    logger.handlers.clear()


def test_setup_logging_custom_format():
    """Test that setup_logging respects custom format string."""
    import io
    custom_format = "%(levelname)s - %(message)s"
    logger = logging_config.setup_logging("test_logger_fmt", format_string=custom_format)
    
    # Capture log output to verify format
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            # Replace stream with a StringIO to capture output
            string_stream = io.StringIO()
            handler.stream = string_stream
            logger.info("Test message")
            output = string_stream.getvalue()
            # Verify the output matches the custom format (no timestamp, just level and message)
            assert "INFO - Test message" in output
            assert output.count(" - ") == 1  # Only one dash separator (levelname - message)
            break
    
    # Clean up
    logger.handlers.clear()


def test_setup_logging_custom_date_format():
    """Test that setup_logging respects custom date format string."""
    import io
    import re
    custom_date_format = "%H:%M:%S"
    logger = logging_config.setup_logging("test_logger_datefmt", date_format=custom_date_format)
    
    # Capture log output to verify date format
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            # Replace stream with a StringIO to capture output
            string_stream = io.StringIO()
            handler.stream = string_stream
            logger.info("Test message")
            output = string_stream.getvalue()
            # Verify the output contains time in HH:MM:SS format (no date)
            # Pattern: HH:MM:SS at the start of the line
            assert re.search(r'^\d{2}:\d{2}:\d{2}', output), f"Expected time format HH:MM:SS in output: {output}"
            # Ensure it doesn't contain full date (YYYY-MM-DD)
            assert not re.search(r'\d{4}-\d{2}-\d{2}', output), f"Should not contain full date in output: {output}"
            break
    
    # Clean up
    logger.handlers.clear()


def test_logging_output_to_file():
    """Test that logging actually writes to file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = logging_config.setup_logging("test_file_output", log_file=log_file)
        logger.info("Test message")
        
        # Flush and read the log file
        for handler in logger.handlers:
            handler.flush()
        
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Test message" in content
            assert "INFO" in content
        
        # Clean up
        logger.handlers.clear()
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)
