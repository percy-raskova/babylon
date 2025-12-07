"""Logging configuration for Babylon/Babylon.

Logging is the nervous system of the simulation.
Every action must be traceable, every decision auditable.
"""

import logging
import logging.config
import sys
from pathlib import Path

import yaml

from babylon.config.base import BaseConfig


def setup_logging(config_path: Path | None = None, default_level: str = "INFO") -> None:
    """Initialize the logging system.

    Args:
        config_path: Path to a YAML logging configuration file.
                    If None, uses default configuration.
        default_level: Fallback log level if config file is missing.

    The logging system is deterministic - given the same inputs,
    it produces the same outputs. No probabilistic behavior.
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

    Simple, functional, materialist.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler - the immediate feedback loop
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler - the permanent record
    log_file = BaseConfig.LOG_DIR / "gameplay.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s|%(levelname)s|%(name)s|%(funcName)s:%(lineno)d|%(message)s"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
