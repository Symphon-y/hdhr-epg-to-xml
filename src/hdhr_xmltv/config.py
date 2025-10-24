"""Configuration management for HD HomeRun XMLTV converter.

This module handles all configuration settings using environment variables
with sensible defaults. Follows the 12-factor app methodology.
"""

import os
from typing import Optional

try:
    from pydantic import BaseSettings, Field, validator
except ImportError:
    # For newer pydantic versions
    from pydantic_settings import BaseSettings
    from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # HD HomeRun Configuration
    hdhr_host: str = Field(
        default="hdhomerun.local",
        description="HD HomeRun device hostname or IP address"
    )

    # EPG Configuration
    epg_days: int = Field(
        default=7,
        ge=1,
        le=14,
        description="Number of days of EPG data to retrieve"
    )

    epg_hours_increment: int = Field(
        default=3,
        ge=1,
        le=24,
        description="Hours to increment for each EPG request"
    )

    # API Method Configuration
    use_official_xmltv: bool = Field(
        default=True,
        description="Use official HD HomeRun XMLTV API instead of legacy JSON endpoints"
    )

    # Output Configuration
    output_file_path: str = Field(
        default="/output/xmltv.xml",
        description="Full path where XMLTV file should be written"
    )

    output_filename: str = Field(
        default="xmltv.xml",
        description="Name of the output XMLTV file"
    )

    # Scheduling Configuration
    schedule_cron: str = Field(
        default="0 1 * * *",
        description="Cron schedule for EPG updates (default: daily at 1 AM)"
    )

    schedule_timezone: str = Field(
        default="UTC",
        description="Timezone for scheduling"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )

    # Application Configuration
    app_name: str = Field(
        default="HDHomeRun-XMLTV-Converter",
        description="Application name for logging and monitoring"
    )

    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )

    # Health check and monitoring
    health_check_enabled: bool = Field(
        default=True,
        description="Enable health check endpoint"
    )

    # File operation settings
    atomic_writes: bool = Field(
        default=True,
        description="Use atomic file writes (write to temp then move)"
    )

    backup_previous: bool = Field(
        default=False,
        description="Keep backup of previous XMLTV file"
    )

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is one of the standard levels."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @validator("output_file_path")
    def validate_output_path(cls, v):
        """Ensure output directory exists or can be created."""
        directory = os.path.dirname(v)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as e:
                raise ValueError(
                    f"Cannot create output directory {directory}: {e}")
        return v

    class Config:
        """Pydantic configuration."""
        env_prefix = "HDHR_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    if not hasattr(get_settings, "_settings"):
        get_settings._settings = Settings()
    return get_settings._settings


# Global settings instance
settings = get_settings()
