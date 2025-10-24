# Base stage with common dependencies
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  cron \
  tzdata \
  && rm -rf /var/lib/apt/lists/*

# Set timezone support
ENV TZ=UTC

# Create output directory with proper permissions
RUN mkdir -p /output && chmod 755 /output

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path
ENV PYTHONPATH=/app/src

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir debugpy ipython

# Copy source code (in dev, this may be mounted as a volume)
COPY src/ /app/src/

# Copy Docker-specific files
COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/healthcheck.sh /app/healthcheck.sh

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh

# Development environment variables
ENV HDHR_LOG_LEVEL=DEBUG
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default to run-once mode in development
CMD ["python", "-m", "hdhr_xmltv", "--run-once"]

# Production stage
FROM base as production

# Copy source code
COPY src/ /app/src/

# Copy Docker-specific files
COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/healthcheck.sh /app/healthcheck.sh

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh

# Environment variable defaults (can be overridden)
ENV HDHR_HOST=hdhomerun.local
ENV HDHR_OUTPUT_FILE_PATH=/output/xmltv.xml
ENV HDHR_OUTPUT_FILENAME=xmltv.xml
ENV HDHR_EPG_DAYS=7
ENV HDHR_EPG_HOURS_INCREMENT=3
ENV HDHR_SCHEDULE_CRON="0 1 * * *"
ENV HDHR_SCHEDULE_TIMEZONE=UTC
ENV HDHR_LOG_LEVEL=INFO
ENV HDHR_ATOMIC_WRITES=true
ENV HDHR_BACKUP_PREVIOUS=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD /app/healthcheck.sh

# Use custom entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (scheduled mode)
CMD ["scheduled"]

# Default to production stage
FROM production