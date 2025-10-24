#!/bin/bash

# Health check script for HD HomeRun XMLTV Converter

# Run the health check command
python -m hdhr_xmltv.main health > /tmp/health.json 2>&1

# Check exit code
if [ $? -eq 0 ]; then
    # Parse the health status from output
    if grep -q '"status": "healthy"' /tmp/health.json; then
        echo "Health check passed"
        exit 0
    else
        echo "Health check failed - unhealthy status"
        cat /tmp/health.json
        exit 1
    fi
else
    echo "Health check failed - command error"
    cat /tmp/health.json
    exit 1
fi