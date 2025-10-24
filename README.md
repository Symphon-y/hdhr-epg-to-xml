# HD HomeRun XMLTV Converter

A professional Python application that converts HD HomeRun EPG (Electronic Program Guide) data to XMLTV format for use with Plex, Jellyfin, and other media server applications.

## Features

- **Clean Architecture**: Built following SOLID principles with clear separation of concerns
- **Environment-Driven Configuration**: All settings configurable via environment variables
- **Robust Error Handling**: Comprehensive logging and graceful error recovery
- **Atomic File Operations**: Safe file writing with backup and verification
- **Flexible Scheduling**: Cron-based scheduling with timezone support
- **Docker Ready**: Complete containerization with health checks
- **Production Ready**: Proper logging, monitoring, and operational considerations

## Architecture

```
┌─────────────────────────────────────┐
│ hdhr-xmltv-converter Container      │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Main Application                │ │
│ │ ├── HD HomeRun API Client       │ │
│ │ ├── XMLTV Converter             │ │
│ │ ├── File Manager                │ │
│ │ └── Scheduler                   │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Shared Volume Mount             │ │
│ │ └── /output/xmltv.xml           │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
                    │
                    ▼ (mounted volume)
┌─────────────────────────────────────┐
│ Plex/Jellyfin Container             │
│ └── /config/xmltv/guide.xml        │
└─────────────────────────────────────┘
```

## Quick Start

### Docker Compose (Recommended)

1. **Clone and configure:**
```bash
git clone <repository-url>
cd hdhr-xml-converter
```

2. **Edit configuration:**
```bash
# Edit docker/.env with your settings
# The .env file is already provided with sensible defaults
# Key settings to verify:
HDHR_HOST=192.168.1.100  # Your HD HomeRun IP
HDHR_SCHEDULE_CRON=0 1 * * *  # Daily at 1 AM
OUTPUT_VOLUME=./output  # Local output directory
```

3. **Run the container:**
```bash
cd docker
docker-compose up -d
```

**Important Requirements:**
- **HD HomeRun DVR Subscription**: The default configuration uses HD HomeRun's official XMLTV API which requires a paid DVR subscription (~$35-50/year)
- **Network Access**: Container needs access to your HD HomeRun device on your local network
- **Single Device Support**: Works with single devices (like HD HomeRun Quatro) or multiple devices
- **Alternative**: If you don't have a DVR subscription, set `HDHR_USE_OFFICIAL_XMLTV=false` in the .env file (limited success due to API restrictions)

### Manual Docker Build

```bash
# Build the image
docker build -f docker/Dockerfile -t hdhr-xmltv-converter .

# Run the container
docker run -d \
  --name hdhr-xmltv-converter \
  --network host \
  -e HDHR_HOST=192.168.1.100 \
  -e HDHR_OUTPUT_FILE_PATH=/output/xmltv.xml \
  -v ./output:/output \
  hdhr-xmltv-converter
```

## Configuration

All configuration is done via environment variables with the `HDHR_` prefix:

### HD HomeRun Settings
- `HDHR_HOST`: HD HomeRun device IP/hostname (default: `hdhomerun.local`)

### API Method Settings
- `HDHR_USE_OFFICIAL_XMLTV`: Use official XMLTV API instead of legacy JSON (default: `true`)

### EPG Settings
- `HDHR_EPG_DAYS`: Days of EPG data to retrieve 1-14 (default: `7`)
- `HDHR_EPG_HOURS_INCREMENT`: Hours per API request 1-24 (default: `3`)

### Output Settings
- `HDHR_OUTPUT_FILE_PATH`: Full output file path (default: `/output/xmltv.xml`)
- `HDHR_OUTPUT_FILENAME`: Output filename (default: `xmltv.xml`)

### Scheduling Settings
- `HDHR_SCHEDULE_CRON`: Cron schedule (default: `0 1 * * *` - daily at 1 AM)
- `HDHR_SCHEDULE_TIMEZONE`: Timezone for scheduling (default: `UTC`)

### File Operations
- `HDHR_ATOMIC_WRITES`: Use atomic file writes (default: `true`)
- `HDHR_BACKUP_PREVIOUS`: Keep backup of previous file (default: `false`)

### Logging
- `HDHR_LOG_LEVEL`: Logging level DEBUG/INFO/WARNING/ERROR (default: `INFO`)

## Usage Modes

### Scheduled Mode (Default)
Runs continuously with cron-based scheduling:
```bash
docker run hdhr-xmltv-converter scheduled
```

### Single Run Mode
Run once and exit:
```bash
docker run hdhr-xmltv-converter once
```

### Health Check Mode
Check application health:
```bash
docker run hdhr-xmltv-converter health
```

## Integration with Media Servers

### Plex Integration
1. Map the output directory to your Plex configuration:
```yaml
volumes:
  - ./output:/path/to/plex/config/xmltv
```

2. In Plex DVR settings, point to the XMLTV file:
```
/path/to/plex/config/xmltv/xmltv.xml
```

### Jellyfin Integration
1. Map the output directory to your Jellyfin configuration:
```yaml
volumes:
  - ./output:/config/xmltv
```

2. In Jellyfin Live TV settings, set the XMLTV path:
```
/config/xmltv/xmltv.xml
```

## Development

### Local Development Setup
```bash
# Clone repository
git clone <repository-url>
cd hdhr-xml-converter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
export HDHR_HOST=192.168.1.100
python -m src.hdhr_xmltv.main once
```

### Project Structure
```
hdhr-xml-converter/
├── src/hdhr_xmltv/          # Main application source
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management
│   ├── hdhr_client.py       # HD HomeRun API client
│   ├── xmltv_converter.py   # XMLTV format converter
│   ├── file_manager.py      # File operations service
│   ├── logging_config.py    # Logging configuration
│   └── main.py              # Main application entry point
├── docker/                  # Docker configuration
│   ├── Dockerfile           # Container definition
│   ├── docker-compose.yml   # Compose configuration
│   ├── entrypoint.sh        # Container entrypoint
│   ├── healthcheck.sh       # Health check script
│   └── .env.example         # Environment variables example
├── tests/                   # Test suite (future)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## API Endpoints Used

The application can use two different HD HomeRun API methods:

### Official XMLTV API (Default - Recommended)
When `HDHR_USE_OFFICIAL_XMLTV=true` (default):

1. **Device Discovery**: `http://{host}/discover.json`
   - Discovers all HD HomeRun devices on the network
   - Extracts DeviceAuth from each device and concatenates them
   - Implements proper multi-device authentication as per HD HomeRun documentation

2. **XMLTV Data**: `https://api.hdhomerun.com/api/xmltv?DeviceAuth={concatenated_auth}`
   - Retrieves pre-formatted XMLTV data directly from HD HomeRun
   - **Requires HD HomeRun DVR subscription** (paid service)
   - Uses gzip compression for efficient transfer
   - Provides 14-day guide data in official XMLTV format

### Legacy JSON API (Fallback)
When `HDHR_USE_OFFICIAL_XMLTV=false`:

1. **Device Discovery**: `http://{host}/discover.json`
   - Retrieves device authentication token

2. **Channel Lineup**: `http://{host}/lineup.json`
   - Gets available channels and metadata

3. **EPG Data**: `https://api.hdhomerun.com/api/guide` or `https://my.hdhomerun.com/api/guide.php`
   - Attempts to retrieve program guide data from legacy endpoints
   - **Note**: These endpoints are now heavily restricted and often return 403 Forbidden

## Monitoring and Health Checks

### Health Check Endpoint
The container includes built-in health checks that verify:
- HD HomeRun connectivity
- Output directory writability
- Last successful update status

### Logging
- Structured logging with configurable levels
- Automatic log rotation for file logging
- Request/response tracking for debugging

### Error Handling
- Graceful degradation on API failures
- Atomic file operations prevent corruption
- Comprehensive error logging with context

## Troubleshooting

### Common Issues

1. **Connection refused to HD HomeRun**:
   - Verify `HDHR_HOST` is correct
   - Ensure network connectivity
   - Try using IP address instead of hostname

2. **Permission denied writing files**:
   - Check volume mount permissions
   - Ensure output directory is writable
   - Verify Docker user permissions

3. **403 Forbidden errors from HD HomeRun API**:
   - **Root Cause**: HD HomeRun has changed their EPG API access model
   - **Official XMLTV API**: Requires a paid HD HomeRun DVR subscription
   - **Legacy JSON endpoints**: Now heavily restricted and often return 403 Forbidden
   - **Error Messages**: The application now provides detailed error messages indicating:
     - Number of devices discovered and DeviceAuth concatenation status
     - Whether a DVR subscription is required
     - Suggestions for alternative solutions

   **Recommended Solutions:**

   a) **Use HD HomeRun's Official XMLTV Service** (Recommended):
   - Requires a paid HD HomeRun DVR subscription
   - Set `HDHR_USE_OFFICIAL_XMLTV=true` (default)
   - Provides reliable 14-day XMLTV format guide data directly
   - Documentation: [HD HomeRun XMLTV Guide Data](https://github.com/Silicondust/documentation/wiki/XMLTV-Guide-Data)

   b) **Alternative EPG Sources**:
   - Use alternative XMLTV providers like Schedules Direct
   - Use OTA PSIP data (limited to basic program info)
   - Consider other EPG aggregation services

   c) **Legacy API Troubleshooting** (Limited Success):
   - Set `HDHR_USE_OFFICIAL_XMLTV=false` to try legacy endpoints
   - The application automatically discovers all HD HomeRun devices
   - Concatenates DeviceAuth from all devices as per HD HomeRun documentation
   - Implements multiple retry strategies and user agents
   - Success is unlikely due to HD HomeRun's restrictions

4. **No EPG data retrieved**:
   - Verify HD HomeRun has tuned channels
   - Check if device has EPG data available
   - Increase `HDHR_EPG_HOURS_INCREMENT` if gaps appear

5. **Container won't start**:
   - Check Docker logs: `docker logs hdhr-xmltv-converter`
   - Verify environment variables
   - Ensure no port conflicts (if using bridge network)

### Debug Mode
Enable detailed logging:
```bash
docker run -e HDHR_LOG_LEVEL=DEBUG hdhr-xmltv-converter
```

### Working Around 403 API Blocking

⚠️ **Updated Analysis**: Based on testing with the latest HD HomeRun documentation and proper device authentication implementation:

**Current Status:**
- **Official XMLTV API**: Returns 403 Forbidden - requires paid HD HomeRun DVR subscription
- **Legacy JSON endpoints**: Return 403 Forbidden - endpoints are heavily restricted
- **Device Discovery**: Works correctly - can discover and authenticate with HD HomeRun devices
- **Multi-device Auth**: Properly implemented - concatenates DeviceAuth from all discovered devices

**Technical Implementation:**
- ✅ **Multi-device Discovery**: Application discovers all HD HomeRun devices on network via broadcast
- ✅ **Proper DeviceAuth**: Concatenates authentication tokens from all devices as per documentation
- ✅ **Official XMLTV Support**: Implements the recommended `https://api.hdhomerun.com/api/xmltv` endpoint
- ✅ **Proper Headers**: Uses gzip encoding and appropriate user agents
- ✅ **Error Handling**: Provides detailed error messages explaining subscription requirements

**Recommendations:**

1. **Subscribe to HD HomeRun DVR Service** (Most Reliable):
   - Official solution for EPG data access
   - Provides 14-day XMLTV guide data
   - Works with the application's default configuration
   - Set `HDHR_USE_OFFICIAL_XMLTV=true` (default)

2. **Alternative EPG Sources**:
   - **Schedules Direct**: Professional EPG service ($25/year)
   - **Gracenote/Tribune**: Via other applications
   - **OTA PSIP**: Limited but free (via HD HomeRun channel scan)

3. **Legacy API Testing** (Educational Purpose):
   - Set `HDHR_USE_OFFICIAL_XMLTV=false` to test legacy endpoints
   - Enable debug logging: `HDHR_LOG_LEVEL=DEBUG`
   - Monitor logs for detailed API interaction information

**Example Error Messages:**
```
403 Forbidden: HD HomeRun XMLTV API access denied. This usually means:
1. No active HD HomeRun DVR subscription
2. Invalid DeviceAuth (tried auth from 1 devices)
3. Devices not associated with a DVR account
Please verify your HD HomeRun DVR subscription and device setup.
```

The application correctly implements HD HomeRun's authentication requirements but cannot bypass the subscription requirement for EPG data access.

## Production Deployment

### Resource Requirements
- **CPU**: Minimal (1-2% during updates)
- **RAM**: ~50MB base + EPG data (typically <200MB total)
- **Storage**: ~10-50MB for XMLTV file depending on channel count
- **Network**: Outbound HTTPS for HD HomeRun API

### Security Considerations
- Container runs as non-root user
- No exposed ports (uses host network for HD HomeRun access)
- Read-only filesystem except output directory
- Minimal attack surface with slim base image

### Monitoring
- Built-in health checks
- Structured logging for external log aggregation
- Metrics can be extracted from health check endpoint

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the existing code style and architecture patterns
4. Add tests for new functionality
5. Submit a pull request

## License

[Your License Here]

## Acknowledgments

- Inspired by [IncubusVictim/HDHomeRunEPG-to-XmlTv](https://github.com/IncubusVictim/HDHomeRunEPG-to-XmlTv)
- Built for the Plex/Jellyfin community
- Follows HD HomeRun API documentation and best practices# hdhr-epg-to-xml
