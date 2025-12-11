"""Logging configuration for Babylon/Babylon.

Logging is the nervous system of the simulation.
Every action must be traceable, every decision auditable.

This module provides:
- setup_logging(): Single entry point for logging initialization
- load_logging_config(): Load config from pyproject.toml
- RotatingFileHandler for main and error-only logs
- JSONFormatter for machine-parseable output
- Console handler for human-readable output

Configuration Hierarchy (highest precedence first):
1. LOG_LEVEL environment variable (global override)
2. pyproject.toml [tool.babylon.logging] section
3. logging.yaml file (if exists)
4. Default hardcoded values
"""

from __future__ import annotations

import logging
import logging.config
import os
import sys
from dataclasses import dataclass, field
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

# TRACE level for ultra-verbose debugging (defined in utils/log.py)
TRACE: int = 5


@dataclass
class LoggingConfig:
    """Centralized logging configuration loaded from pyproject.toml.

    Attributes:
        default_level: Global default log level
        console_level: Log level for console output
        file_level: Log level for file output
        modules: Per-module log level overrides
    """

    default_level: str = "INFO"
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    modules: dict[str, str] = field(default_factory=dict)


def load_logging_config(pyproject_path: Path | None = None) -> LoggingConfig:
    """Load logging configuration from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml. If None, searches for it.

    Returns:
        LoggingConfig with settings from pyproject.toml or defaults.

    The configuration is loaded from [tool.babylon.logging] section.
    """
    config = LoggingConfig()

    # Find pyproject.toml
    if pyproject_path is None:
        pyproject_path = _find_pyproject_toml()

    if pyproject_path is None or not pyproject_path.exists():
        return config

    try:
        # Use tomllib for Python 3.11+ (stdlib)
        import tomllib

        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)

        # Navigate to [tool.babylon.logging]
        babylon_config = pyproject.get("tool", {}).get("babylon", {}).get("logging", {})

        if babylon_config:
            config.default_level = babylon_config.get("default_level", config.default_level)
            config.console_level = babylon_config.get("console_level", config.console_level)
            config.file_level = babylon_config.get("file_level", config.file_level)
            config.modules = babylon_config.get("modules", {})

    except Exception as e:
        # If we can't load config, log a warning and use defaults
        # (can't use logging here as it's not set up yet)
        print(f"Warning: Could not load logging config from pyproject.toml: {e}", file=sys.stderr)

    return config


def _find_pyproject_toml() -> Path | None:
    """Find pyproject.toml by searching up from current directory.

    Returns:
        Path to pyproject.toml or None if not found.
    """
    # Start from the babylon package directory
    current = Path(__file__).resolve().parent

    # Search up to 10 levels (reasonable limit)
    for _ in range(10):
        candidate = current / "pyproject.toml"
        if candidate.exists():
            return candidate
        if current.parent == current:
            break
        current = current.parent

    # Also check common locations
    for location in [Path.cwd(), Path.cwd().parent]:
        candidate = location / "pyproject.toml"
        if candidate.exists():
            return candidate

    return None


def setup_logging(
    config_path: Path | None = None,
    default_level: str | None = None,
    pyproject_path: Path | None = None,
) -> None:
    """Initialize the logging system.

    Args:
        config_path: Path to a YAML logging configuration file.
                    If None, uses pyproject.toml or default configuration.
        default_level: Override for the default log level.
        pyproject_path: Path to pyproject.toml (optional, auto-detected).

    Configuration is loaded in this order (highest precedence first):
    1. LOG_LEVEL environment variable
    2. default_level parameter
    3. pyproject.toml [tool.babylon.logging] section
    4. logging.yaml file (if config_path provided)
    5. Default values

    The logging system is deterministic - given the same inputs,
    it produces the same outputs. No probabilistic behavior.

    Handler hierarchy:
    - Console: Human-readable, INFO level (or configured level)
    - Main file (RotatingFileHandler): JSON Lines, DEBUG level, 10MB rotation
    - Error file (RotatingFileHandler): JSON Lines, ERROR only, 5MB rotation
    """
    # Ensure log directory exists
    BaseConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Load configuration from pyproject.toml
    logging_config = load_logging_config(pyproject_path)

    # Override with environment variable if set
    env_level = os.getenv("LOG_LEVEL")
    if env_level:
        logging_config.default_level = env_level.upper()
        logging_config.console_level = env_level.upper()

    # Override with parameter if provided
    if default_level:
        logging_config.default_level = default_level.upper()

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

        # Apply per-module levels from pyproject.toml even when using yaml config
        _apply_module_levels(logging_config.modules)
    else:
        # Default configuration using pyproject.toml settings
        _setup_default_logging(logging_config)


def _apply_module_levels(modules: dict[str, str]) -> None:
    """Apply per-module log levels.

    Args:
        modules: Dict mapping logger names to log levels.
    """
    for module_name, level_str in modules.items():
        level = _parse_level(level_str)
        logging.getLogger(module_name).setLevel(level)


def _parse_level(level_str: str) -> int:
    """Parse a log level string to its integer value.

    Args:
        level_str: Level name (DEBUG, INFO, etc.) or TRACE.

    Returns:
        Integer log level.
    """
    level_str = level_str.upper()
    if level_str == "TRACE":
        return TRACE
    return getattr(logging, level_str, logging.INFO)


def _setup_default_logging(config: LoggingConfig) -> None:
    """Set up default logging configuration.

    Args:
        config: LoggingConfig with settings from pyproject.toml.

    Creates a handler hierarchy with:
    - Console handler (human-readable)
    - Rotating main file handler (JSON, DEBUG level)
    - Rotating error file handler (JSON, ERROR only)
    """
    console_level = _parse_level(config.console_level)
    file_level = _parse_level(config.file_level)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers filter

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create context-aware filter for all handlers
    context_filter = ContextAwareFilter()

    # Console handler - the immediate feedback loop
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
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
    main_handler.setLevel(file_level)
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

    # Apply per-module levels from pyproject.toml
    _apply_module_levels(config.modules)


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


def get_current_config() -> LoggingConfig:
    """Get the current logging configuration (for debugging/inspection).

    Returns:
        LoggingConfig loaded from pyproject.toml.
    """
    return load_logging_config()
