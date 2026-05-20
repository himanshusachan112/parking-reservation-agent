"""
Production Logging Configuration for ParkSmart.

Provides structured, rotating log output for API requests,
errors, and application events.

Usage:
    from src.utils.logging_config import setup_logging
    setup_logging()  # Call once at startup
"""

import logging
import logging.handlers
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Configure structured logging with rotating file handlers.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files (created if missing).
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear any existing handlers to avoid duplicates on reload
    root_logger.handlers.clear()

    # ---- Formatter ----
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---- Console Handler (stdout) ----
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # ---- Application Log (rotating, 5 MB × 5 backups) ----
    app_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "app.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    # ---- Error Log (errors only, rotating) ----
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # ---- API Access Log (separate file for request logging) ----
    access_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / "access.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(formatter)
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addHandler(access_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    root_logger.info("Logging initialized — level=%s, dir=%s", log_level, log_path.resolve())
