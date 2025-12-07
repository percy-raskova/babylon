"""Backup and restore utilities for the Archive (ChromaDB).

Data preservation is a revolutionary act.
The historical record must survive state repression.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from babylon.config.chromadb_config import ChromaDBConfig

logger = logging.getLogger(__name__)


def backup_chroma(
    backup_dir: Path | None = None,
    backup_name: str | None = None,
) -> Path:
    """Create a backup of the ChromaDB data directory.

    Args:
        backup_dir: Directory to store backups. Defaults to ./backups
        backup_name: Name for the backup. Defaults to timestamp-based name.

    Returns:
        Path to the created backup directory

    Raises:
        FileNotFoundError: If ChromaDB directory doesn't exist
        PermissionError: If backup directory isn't writable
    """
    source_dir = ChromaDBConfig.BASE_DIR

    if not source_dir.exists():
        logger.warning("ChromaDB directory does not exist: %s", source_dir)
        raise FileNotFoundError(f"ChromaDB directory not found: {source_dir}")

    # Set up backup destination
    if backup_dir is None:
        backup_dir = Path("./backups")

    backup_dir.mkdir(parents=True, exist_ok=True)

    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"chromadb_backup_{timestamp}"

    destination = backup_dir / backup_name

    logger.info("Creating ChromaDB backup: %s -> %s", source_dir, destination)

    # Perform the backup
    shutil.copytree(source_dir, destination)

    logger.info("Backup completed successfully: %s", destination)
    return destination


def restore_chroma(
    backup_path: Path,
    force: bool = False,
) -> None:
    """Restore ChromaDB from a backup.

    Args:
        backup_path: Path to the backup directory
        force: If True, overwrite existing ChromaDB data

    Raises:
        FileNotFoundError: If backup doesn't exist
        FileExistsError: If ChromaDB exists and force=False
    """
    target_dir = ChromaDBConfig.BASE_DIR

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    if target_dir.exists():
        if not force:
            raise FileExistsError(
                f"ChromaDB directory already exists: {target_dir}. " "Use force=True to overwrite."
            )
        logger.warning("Removing existing ChromaDB directory: %s", target_dir)
        shutil.rmtree(target_dir)

    logger.info("Restoring ChromaDB: %s -> %s", backup_path, target_dir)

    shutil.copytree(backup_path, target_dir)

    logger.info("Restore completed successfully")


def list_backups(backup_dir: Path | None = None) -> list[Path]:
    """List all available ChromaDB backups.

    Args:
        backup_dir: Directory containing backups. Defaults to ./backups

    Returns:
        List of backup directory paths, sorted by modification time (newest first)
    """
    if backup_dir is None:
        backup_dir = Path("./backups")

    if not backup_dir.exists():
        return []

    backups = [
        p for p in backup_dir.iterdir() if p.is_dir() and p.name.startswith("chromadb_backup_")
    ]

    # Sort by modification time, newest first
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return backups
