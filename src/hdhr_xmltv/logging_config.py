"""Logging configuration for HD HomeRun XMLTV converter."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """Set up comprehensive logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        log_file: Optional log file path for file logging
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    # Default format if none provided
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(filename)s:%(lineno)d] - %(message)s"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Log initial setup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {level}")
    if log_file:
        logger.info(f"File logging enabled: {log_file}")


class LoggerMixin:
    """Mixin class to add logging capability to any class."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for this class."""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
