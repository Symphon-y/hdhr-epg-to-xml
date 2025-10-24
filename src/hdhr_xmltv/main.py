"""Main application entry point for HD HomeRun XMLTV converter.

This module provides the main application logic, scheduling, and orchestration
of the EPG data retrieval and XMLTV conversion process.
"""

import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

from croniter import croniter

from .config import settings
from .hdhr_client import HDHomeRunClient, HDHomeRunAPIError
from .xmltv_converter import XMLTVConverter
from .file_manager import FileManager, FileOperationError


logger = logging.getLogger(__name__)


class HDHomeRunXMLTVApp:
    """Main application class for HD HomeRun XMLTV converter."""

    def __init__(self):
        """Initialize the application."""
        self.hdhr_client = HDHomeRunClient(
            host=settings.hdhr_host,
            timeout=30
        )
        self.xmltv_converter = XMLTVConverter(
            timezone=settings.schedule_timezone
        )
        self.file_manager = FileManager(
            atomic_writes=settings.atomic_writes,
            backup_previous=settings.backup_previous
        )
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def run_once(self) -> bool:
        """Run EPG conversion once.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting EPG data retrieval and conversion")
            start_time = datetime.now()

            # Check if we should use the official XMLTV API
            if settings.use_official_xmltv:
                return self._run_once_xmltv_api()
            else:
                return self._run_once_legacy_json()

        except Exception as e:
            logger.error(
                f"Unexpected error during EPG conversion: {e}", exc_info=True)
            return False

    def _run_once_xmltv_api(self) -> bool:
        """Run EPG conversion using official HD HomeRun XMLTV API.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Using official HD HomeRun XMLTV API")
            start_time = datetime.now()

            # Get XMLTV data directly from HD HomeRun
            logger.info(
                f"Connecting to HD HomeRun devices (primary: {settings.hdhr_host})")
            xmltv_content = self.hdhr_client.get_xmltv_data()

            if not xmltv_content or len(xmltv_content) < 100:
                logger.error("No valid XMLTV data received")
                return False

            logger.info(
                f"Retrieved XMLTV data ({len(xmltv_content):,} characters)")

            # Write to file directly (no conversion needed)
            output_path = settings.output_file_path
            if settings.output_filename and settings.output_filename != "xmltv.xml":
                # Use custom filename if specified
                from pathlib import Path
                output_path = str(
                    Path(settings.output_file_path).parent / settings.output_filename)

            self.file_manager.write_xmltv_file(xmltv_content, output_path)

            # Clean up old backups if enabled
            if settings.backup_previous:
                self.file_manager.cleanup_old_backups(
                    output_path, keep_count=5)

            # Log completion stats
            end_time = datetime.now()
            duration = end_time - start_time

            file_info = self.file_manager.get_file_info(output_path)
            file_size = file_info['size'] if file_info else 0

            logger.info(
                f"XMLTV conversion completed successfully in {duration.total_seconds():.2f}s. "
                f"Output file: {output_path} ({file_size:,} bytes)"
            )

            return True

        except HDHomeRunAPIError as e:
            logger.error(f"HD HomeRun API error: {e}")
            return False
        except FileOperationError as e:
            logger.error(f"File operation error: {e}")
            return False

    def _run_once_legacy_json(self) -> bool:
        """Run EPG conversion using legacy HD HomeRun JSON API.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Using legacy HD HomeRun JSON API")
            start_time = datetime.now()

            # Get EPG data from HD HomeRun
            logger.info(f"Connecting to HD HomeRun at {settings.hdhr_host}")
            channels = self.hdhr_client.get_channels()

            if not channels:
                logger.error("No channels found, cannot proceed")
                return False

            logger.info(f"Found {len(channels)} channels")

            # Get EPG data
            programs = self.hdhr_client.get_epg_data(
                days=settings.epg_days,
                hours_increment=settings.epg_hours_increment
            )

            if not programs:
                logger.warning("No program data found")
                return False

            logger.info(f"Retrieved {len(programs)} programs")

            # Convert to XMLTV
            xmltv_root = self.xmltv_converter.convert_to_xmltv(
                channels=channels,
                programs=programs,
                generator_name=settings.app_name,
                generator_url="https://github.com/user/hdhr-xml-converter"
            )

            # Format as string
            xmltv_content = self.xmltv_converter.format_xmltv(xmltv_root)

            # Write to file
            output_path = settings.output_file_path
            if settings.output_filename and settings.output_filename != "xmltv.xml":
                # Use custom filename if specified
                from pathlib import Path
                output_path = str(
                    Path(settings.output_file_path).parent / settings.output_filename)

            self.file_manager.write_xmltv_file(xmltv_content, output_path)

            # Clean up old backups if enabled
            if settings.backup_previous:
                self.file_manager.cleanup_old_backups(
                    output_path, keep_count=5)

            # Log completion stats
            end_time = datetime.now()
            duration = end_time - start_time

            file_info = self.file_manager.get_file_info(output_path)
            file_size = file_info['size'] if file_info else 0

            logger.info(
                f"EPG conversion completed successfully in {duration.total_seconds():.2f}s. "
                f"Generated {len(channels)} channels, {len(programs)} programs. "
                f"Output file: {output_path} ({file_size:,} bytes)"
            )

            return True

        except HDHomeRunAPIError as e:
            logger.error(f"HD HomeRun API error: {e}")
            return False
        except FileOperationError as e:
            logger.error(f"File operation error: {e}")
            return False

    def run_scheduled(self) -> None:
        """Run the application with scheduling."""
        logger.info(
            f"Starting scheduled mode with cron: {settings.schedule_cron}")
        logger.info(f"Timezone: {settings.schedule_timezone}")

        self.running = True
        cron = croniter(settings.schedule_cron, datetime.now())

        # Calculate and log next run time
        next_run = cron.get_next(datetime)
        logger.info(f"Next scheduled run: {next_run}")

        while self.running:
            try:
                current_time = datetime.now()

                if current_time >= next_run:
                    logger.info("Scheduled run starting")
                    success = self.run_once()

                    if success:
                        logger.info("Scheduled run completed successfully")
                    else:
                        logger.error("Scheduled run failed")

                    # Calculate next run time
                    cron = croniter(settings.schedule_cron, current_time)
                    next_run = cron.get_next(datetime)
                    logger.info(f"Next scheduled run: {next_run}")

                # Sleep for a minute before checking again
                if self.running:
                    time.sleep(60)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(60)  # Wait before retrying

        logger.info("Scheduler stopped")

    def health_check(self) -> dict:
        """Perform health check.

        Returns:
            Health check status dictionary
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": settings.app_version,
            "checks": {}
        }

        try:
            # Check HD HomeRun connectivity
            try:
                self.hdhr_client.discover_all_devices()
                health_status["checks"]["hdhr_connectivity"] = "ok"
            except Exception as e:
                health_status["checks"]["hdhr_connectivity"] = f"error: {e}"
                health_status["status"] = "unhealthy"

            # Check output directory writability
            try:
                import tempfile
                from pathlib import Path

                output_dir = Path(settings.output_file_path).parent
                with tempfile.NamedTemporaryFile(dir=output_dir, delete=True):
                    pass
                health_status["checks"]["output_writable"] = "ok"
            except Exception as e:
                health_status["checks"]["output_writable"] = f"error: {e}"
                health_status["status"] = "unhealthy"

            # Check file status
            file_info = self.file_manager.get_file_info(
                settings.output_file_path)
            if file_info:
                health_status["checks"]["last_output"] = {
                    "status": "ok",
                    "size": file_info["size"],
                    "modified": file_info["modified"].isoformat()
                }
            else:
                health_status["checks"]["last_output"] = "no output file found"

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)

        return health_status


def setup_logging():
    """Set up application logging."""
    from .logging_config import setup_logging as setup_logging_config

    setup_logging_config(
        level=settings.log_level,
        format_string=settings.log_format
    )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="HD HomeRun XMLTV Converter")
    parser.add_argument("--run-once", action="store_true",
                        help="Run once and exit (instead of scheduled mode)")
    parser.add_argument("--health-check", action="store_true",
                        help="Run health check and exit")
    parser.add_argument("mode", nargs="?", default="scheduled",
                        choices=["scheduled", "once", "health"],
                        help="Run mode (for backward compatibility)")

    args = parser.parse_args()

    setup_logging()

    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"HD HomeRun host: {settings.hdhr_host}")
    logger.info(f"Output path: {settings.output_file_path}")
    logger.info(f"EPG days: {settings.epg_days}")
    logger.info(f"Schedule: {settings.schedule_cron}")
    logger.info(
        f"API method: {'Official XMLTV' if settings.use_official_xmltv else 'Legacy JSON'}")

    app = HDHomeRunXMLTVApp()

    # Determine run mode from arguments
    if args.run_once or args.mode == "once":
        logger.info("Running in single-run mode")
        success = app.run_once()
        sys.exit(0 if success else 1)
    elif args.health_check or args.mode == "health":
        logger.info("Running health check")
        health = app.health_check()
        print(health)
        sys.exit(0 if health["status"] == "healthy" else 1)
    else:
        logger.info("Running in scheduled mode")
        app.run_scheduled()


if __name__ == "__main__":
    main()
