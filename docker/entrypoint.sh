#!/bin/bash
set -e

# HD HomeRun XMLTV Converter Entrypoint Script

echo "Starting HD HomeRun XMLTV Converter..."
echo "Host: ${HDHR_HOST}"
echo "Output: ${HDHR_OUTPUT_FILE_PATH}"
echo "Schedule: ${HDHR_SCHEDULE_CRON}"
echo "Timezone: ${HDHR_SCHEDULE_TIMEZONE}"

# Ensure output directory exists and is writable
OUTPUT_DIR=$(dirname "${HDHR_OUTPUT_FILE_PATH}")
mkdir -p "${OUTPUT_DIR}"

if [ ! -w "${OUTPUT_DIR}" ]; then
    echo "ERROR: Output directory ${OUTPUT_DIR} is not writable"
    exit 1
fi

# Set timezone if specified
if [ -n "${HDHR_SCHEDULE_TIMEZONE}" ] && [ "${HDHR_SCHEDULE_TIMEZONE}" != "UTC" ]; then
    export TZ="${HDHR_SCHEDULE_TIMEZONE}"
    echo "Timezone set to: ${TZ}"
fi

# Run the application
case "${1:-scheduled}" in
    "once")
        echo "Running in single-run mode..."
        exec python -m hdhr_xmltv.main once
        ;;
    "health")
        echo "Running health check..."
        exec python -m hdhr_xmltv.main health
        ;;
    "scheduled"|"")
        echo "Running in scheduled mode..."
        exec python -m hdhr_xmltv.main scheduled
        ;;
    *)
        echo "Unknown command: $1"
        echo "Usage: $0 [once|health|scheduled]"
        exit 1
        ;;
esac