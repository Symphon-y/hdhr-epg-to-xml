# HD HomeRun XMLTV Converter

A Docker container that converts HD HomeRun EPG data to XMLTV format for use with Plex, Jellyfin, and other media servers.

## Features

- **Official XMLTV API Support**: Uses HD HomeRun's official XMLTV endpoint (requires DVR subscription)
- **Legacy JSON API Fallback**: Supports older HD HomeRun devices
- **Multi-Device Discovery**: Automatically discovers all HD HomeRun devices on your network
- **Scheduled Updates**: Configurable cron scheduling for automatic EPG updates
- **Docker Optimized**: Multi-stage builds, health checks, and proper signal handling
- **Unraid Ready**: Pre-configured for Unraid deployment

## Quick Start

### Docker Compose (Recommended)

```yaml
services:
  hdhr-xmltv-converter:
    image: travisredden/hdhr-xmltv-converter:latest
    container_name: hdhr-xmltv-converter
    restart: unless-stopped
    environment:
      HDHR_HOST: 192.168.1.100  # Your HD HomeRun IP
      HDHR_USE_OFFICIAL_XMLTV: true
      HDHR_SCHEDULE_CRON: "0 1 * * *"
      HDHR_SCHEDULE_TIMEZONE: America/New_York
    volumes:
      - ./output:/output
    network_mode: host
```

### Docker Run

```bash
docker run -d \
  --name hdhr-xmltv-converter \
  --restart unless-stopped \
  --network host \
  -e HDHR_HOST=192.168.1.100 \
  -e HDHR_USE_OFFICIAL_XMLTV=true \
  -v ./output:/output \
  travisredden/hdhr-xmltv-converter:latest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HDHR_HOST` | `hdhomerun.local` | IP address or hostname of your HD HomeRun |
| `HDHR_USE_OFFICIAL_XMLTV` | `false` | Use official XMLTV API (requires DVR subscription) |
| `HDHR_EPG_DAYS` | `7` | Number of days of EPG data to fetch |
| `HDHR_SCHEDULE_CRON` | `"0 1 * * *"` | Cron schedule for updates (daily at 1 AM) |
| `HDHR_SCHEDULE_TIMEZONE` | `UTC` | Timezone for scheduling |
| `HDHR_OUTPUT_FILE_PATH` | `/output/xmltv.xml` | Full path to output file |
| `HDHR_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Requirements

- HD HomeRun device on your local network
- For official XMLTV API: HD HomeRun DVR subscription
- Docker with host networking access

## Usage with Media Servers

### Plex
1. Mount output to Plex-accessible location
2. In Plex Settings → Live TV & DVR → EPG Data Source → XMLTV
3. Point to the generated `xmltv.xml` file

### Jellyfin
1. In Jellyfin Admin → Live TV → TV Guide Data Provider
2. Select "XMLTV" and provide path to `xmltv.xml`

## Health Check

The container includes a health check that verifies:
- Application is running
- Output file exists and is recent
- HD HomeRun connectivity

## Support

- **Repository**: https://github.com/Symphon-y/hdhr-epg-to-xml
- **Issues**: Report bugs and feature requests on GitHub

## Tags

- `latest`: Latest stable release
- `v1.0.0`: Specific version tags
- `main`: Development builds (auto-updated from main branch)