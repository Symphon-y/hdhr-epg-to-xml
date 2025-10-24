"""File operations service for XMLTV file management.

This module handles all file operations including atomic writes,
backup management, and error handling for XMLTV file output.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class FileOperationError(Exception):
    """Custom exception for file operation errors."""
    pass


class FileManager:
    """Service for managing XMLTV file operations."""

    def __init__(self, atomic_writes: bool = True, backup_previous: bool = False):
        """Initialize the file manager.

        Args:
            atomic_writes: Use atomic file writes (write to temp then move)
            backup_previous: Keep backup of previous file
        """
        self.atomic_writes = atomic_writes
        self.backup_previous = backup_previous

    def write_xmltv_file(self, content: str, file_path: str) -> None:
        """Write XMLTV content to file with error handling.

        Args:
            content: XMLTV content to write
            file_path: Destination file path

        Raises:
            FileOperationError: If file writing fails
        """
        try:
            file_path_obj = Path(file_path)

            # Ensure directory exists
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if requested and file exists
            if self.backup_previous and file_path_obj.exists():
                self._create_backup(file_path_obj)

            # Write file (atomically or directly)
            if self.atomic_writes:
                self._write_atomic(content, file_path_obj)
            else:
                self._write_direct(content, file_path_obj)

            # Verify the written file
            self._verify_file(file_path_obj, content)

            logger.info(f"Successfully wrote XMLTV file to {file_path}")

        except Exception as e:
            raise FileOperationError(
                f"Failed to write XMLTV file to {file_path}: {e}")

    def _write_atomic(self, content: str, file_path: Path) -> None:
        """Write file atomically using temporary file.

        Args:
            content: Content to write
            file_path: Destination file path
        """
        # Create temporary file in the same directory as target
        temp_dir = file_path.parent

        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=temp_dir,
            delete=False,
            prefix=f"{file_path.stem}_tmp_",
            suffix=file_path.suffix
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())  # Force write to disk

        try:
            # Atomic move (rename) operation
            temp_path.replace(file_path)
            logger.debug(f"Atomically moved {temp_path} to {file_path}")
        except Exception as e:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise FileOperationError(
                f"Failed to atomically move temp file: {e}")

    def _write_direct(self, content: str, file_path: Path) -> None:
        """Write file directly.

        Args:
            content: Content to write
            file_path: Destination file path
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        logger.debug(f"Directly wrote content to {file_path}")

    def _create_backup(self, file_path: Path) -> None:
        """Create backup of existing file.

        Args:
            file_path: Path to file to backup
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(
            f".{timestamp}{file_path.suffix}.bak")

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup of {file_path}: {e}")
            # Don't fail the main operation for backup failure

    def _verify_file(self, file_path: Path, expected_content: str) -> None:
        """Verify that written file contains expected content.

        Args:
            file_path: Path to file to verify
            expected_content: Expected file content

        Raises:
            FileOperationError: If verification fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                actual_content = f.read()

            if len(actual_content) != len(expected_content):
                raise FileOperationError(
                    f"File size mismatch: expected {len(expected_content)}, "
                    f"got {len(actual_content)}"
                )

            # For large files, just check start and end to avoid memory issues
            if len(expected_content) > 1024 * 1024:  # 1MB
                start_check = min(1024, len(expected_content) // 4)
                end_check = min(1024, len(expected_content) // 4)

                if (actual_content[:start_check] != expected_content[:start_check] or
                        actual_content[-end_check:] != expected_content[-end_check:]):
                    raise FileOperationError(
                        "File content verification failed (partial check)")
            else:
                # Full content check for smaller files
                if actual_content != expected_content:
                    raise FileOperationError(
                        "File content verification failed (full check)")

            logger.debug(f"File verification successful for {file_path}")

        except FileOperationError:
            raise
        except Exception as e:
            raise FileOperationError(f"File verification failed: {e}")

    def cleanup_old_backups(self, file_path: str, keep_count: int = 5) -> None:
        """Clean up old backup files, keeping only the most recent ones.

        Args:
            file_path: Main file path (backups will be in same directory)
            keep_count: Number of backups to keep
        """
        try:
            file_path_obj = Path(file_path)
            directory = file_path_obj.parent
            base_name = file_path_obj.stem
            extension = file_path_obj.suffix

            # Find all backup files
            backup_pattern = f"{base_name}.*.{extension}.bak"
            backup_files = list(directory.glob(backup_pattern))

            if len(backup_files) <= keep_count:
                return

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Remove old backups
            for old_backup in backup_files[keep_count:]:
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logger.warning(
                        f"Failed to remove old backup {old_backup}: {e}")

            logger.info(
                f"Cleaned up {len(backup_files) - keep_count} old backup files")

        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get information about the XMLTV file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information or None if file doesn't exist
        """
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                return None

            stat = file_path_obj.stat()

            return {
                "path": str(file_path_obj.absolute()),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "readable": file_path_obj.is_file() and os.access(file_path_obj, os.R_OK),
                "writable": os.access(file_path_obj.parent, os.W_OK)
            }

        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None
