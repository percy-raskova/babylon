"""Logging configuration for Babylon/Babylon.

Logging is the nervous system of the simulation.
Every action must be traceable, every decision auditable.

This module provides:
- setup_logging(): Single entry point for logging initialization
- RotatingFileHandler for main and error-only logs
- JSONFormatter for machine-parseable output
- Console handler for human-readable output
"""

from __future__ import annotations

import logging
import logging.config
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from babylon.config.base import BaseConfig
from babylon.utils.log import ContextAwareFilter, JSONFormatter

if TYPE_CHECKING:
    pass

# Constants for log rotation (from logging-architecture.yaml spec)
MAIN_LOG_MAX_BYTES: int = 10_000_000  # 10MB
MAIN_LOG_BACKUP_COUNT: int = 5  # 50MB total

ERROR_LOG_MAX_BYTES: int = 5_000_000  # 5MB
ERROR_LOG_BACKUP_COUNT: int = 10  # 50MB total


def setup_logging(config_path: Path | None = None, default_level: str = "INFO") -> None:
    """Initialize the logging system.

    Args:
        config_path: Path to a YAML logging configuration file.
                    If None, uses default configuration.
        default_level: Fallback log level if config file is missing.

    The logging system is deterministic - given the same inputs,
    it produces the same outputs. No probabilistic behavior.

    Handler hierarchy:
    - Console: Human-readable, INFO level (or configured level)
    - Main file (RotatingFileHandler): JSON Lines, DEBUG level, 10MB rotation
    - Error file (RotatingFileHandler): JSON Lines, ERROR only, 5MB rotation
    """
    # Ensure log directory exists
    BaseConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Try to load YAML config if provided
    if config_path and config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Update file handler paths to use configured log directory
        if "handlers" in config:
            for _handler_name, handler_config in config["handlers"].items():
                if "filename" in handler_config:
                    # Make path relative to LOG_DIR
                    filename = Path(handler_config["filename"]).name
                    handler_config["filename"] = str(BaseConfig.LOG_DIR / filename)

        logging.config.dictConfig(config)
    else:
        # Default configuration
        _setup_default_logging(default_level)


def _setup_default_logging(level: str) -> None:
    """Set up default logging configuration.

    Creates a handler hierarchy with:
    - Console handler (human-readable)
    - Rotating main file handler (JSON, DEBUG level)
    - Rotating error file handler (JSON, ERROR only)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers filter

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create context-aware filter for all handlers
    context_filter = ContextAwareFilter()

    # Console handler - the immediate feedback loop
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(context_filter)
    root_logger.addHandler(console_handler)

    # Main file handler - rotating JSON Lines for all logs
    main_log_file = BaseConfig.LOG_DIR / "babylon.log"
    main_handler = RotatingFileHandler(
        main_log_file,
        maxBytes=MAIN_LOG_MAX_BYTES,
        backupCount=MAIN_LOG_BACKUP_COUNT,
    )
    main_handler.setLevel(logging.DEBUG)
    main_handler.setFormatter(JSONFormatter())
    main_handler.addFilter(context_filter)
    root_logger.addHandler(main_handler)

    # Error file handler - rotating JSON Lines for errors only
    error_log_file = BaseConfig.LOG_DIR / "errors.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=ERROR_LOG_MAX_BYTES,
        backupCount=ERROR_LOG_BACKUP_COUNT,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    error_handler.addFilter(context_filter)
    root_logger.addHandler(error_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def create_simulation_handler(
    simulation_id: str,
    seed: int | None = None,
) -> RotatingFileHandler:
    """Create a file handler for a specific simulation run.

    Creates a per-simulation log file for forensic analysis and replay.

    Args:
        simulation_id: Unique identifier for the simulation.
        seed: Random seed used for the simulation (optional).

    Returns:
        Configured RotatingFileHandler for the simulation log.
    """
    from datetime import UTC, datetime

    # Ensure simulation logs directory exists
    sim_log_dir = BaseConfig.LOG_DIR / "simulation"
    sim_log_dir.mkdir(parents=True, exist_ok=True)

    # Build filename: sim_{timestamp}_{seed}.jsonl
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    seed_str = f"_{seed}" if seed is not None else ""
    filename = f"sim_{timestamp}{seed_str}_{simulation_id}.jsonl"

    handler = RotatingFileHandler(
        sim_log_dir / filename,
        maxBytes=MAIN_LOG_MAX_BYTES,
        backupCount=3,  # Less retention for individual sims
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(ContextAwareFilter())

    return handler
