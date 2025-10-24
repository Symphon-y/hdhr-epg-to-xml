"""HD HomeRun API client for retrieving EPG data.

This module provides a clean interface to the HD HomeRun API endpoints
for device discovery, channel lineup, and EPG data retrieval.
"""

import json
import logging
import ssl
import time
import urllib.request
import urllib.parse
import socket
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

import pytz


logger = logging.getLogger(__name__)


@dataclass
class ChannelInfo:
    """Channel information from HD HomeRun lineup."""
    guide_number: str
    guide_name: str
    url: str
    image_url: Optional[str] = None


@dataclass
class ProgramInfo:
    """Program information from HD HomeRun EPG."""
    title: str
    start_time: datetime
    end_time: datetime
    guide_number: str
    synopsis: Optional[str] = None
    episode_title: Optional[str] = None
    episode_number: Optional[str] = None
    image_url: Optional[str] = None
    original_airdate: Optional[datetime] = None
    filters: Optional[List[str]] = None
    first: Optional[bool] = None


class HDHomeRunAPIError(Exception):
    """Custom exception for HD HomeRun API errors."""
    pass


class HDHomeRunClient:
    """Client for interacting with HD HomeRun API endpoints."""

    def __init__(self, host: str, timeout: int = 30):
        """Initialize the HD HomeRun client.

        Args:
            host: HD HomeRun device hostname or IP address (can be one of many)
            timeout: Request timeout in seconds
        """
        self.host = host
        self.timeout = timeout
        self.device_auth: Optional[str] = None
        self.all_device_auths: List[str] = []
        self.discovered_devices: List[str] = []
        self._channels: Optional[List[ChannelInfo]] = None

        # Set up SSL context for HTTPS requests
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def discover_all_devices(self) -> str:
        """Discover all HD HomeRun devices on the network and concatenate their DeviceAuth.

        This method implements the proper authentication as documented by HD HomeRun:
        "Concatenation of the DeviceAuth strings from all HDHomeRun tuners"

        Returns:
            Concatenated DeviceAuth string from all discovered devices

        Raises:
            HDHomeRunAPIError: If no devices are discovered or authentication fails
        """
        logger.info("Discovering all HD HomeRun devices on the network")

        # Start with the explicitly configured host
        device_hosts = {self.host}

        # Try to discover additional devices via broadcast
        try:
            additional_hosts = self._discover_via_broadcast()
            device_hosts.update(additional_hosts)
            logger.info(
                f"Found {len(additional_hosts)} additional devices via broadcast discovery")
        except Exception as e:
            logger.warning(f"Broadcast discovery failed: {e}")

        # Try common hostnames
        common_names = ["hdhomerun.local", "hdhomerun"]
        for name in common_names:
            if name not in device_hosts:
                device_hosts.add(name)

        # Discover DeviceAuth from all reachable devices
        self.all_device_auths = []
        self.discovered_devices = []

        for host in device_hosts:
            try:
                device_auth = self._discover_single_device(host)
                if device_auth and device_auth not in self.all_device_auths:
                    self.all_device_auths.append(device_auth)
                    self.discovered_devices.append(host)
                    logger.info(
                        f"Successfully discovered device at {host} with auth: {device_auth[:8]}...")
            except Exception as e:
                logger.debug(f"Could not discover device at {host}: {e}")

        if not self.all_device_auths:
            raise HDHomeRunAPIError(
                f"No HD HomeRun devices discovered. Tried hosts: {', '.join(device_hosts)}")

        # Concatenate all DeviceAuth strings as per documentation
        self.device_auth = ''.join(self.all_device_auths)

        logger.info(f"Successfully discovered {len(self.all_device_auths)} devices. "
                    f"Concatenated DeviceAuth length: {len(self.device_auth)}")

        return self.device_auth

    def _discover_via_broadcast(self) -> Set[str]:
        """Discover HD HomeRun devices via UDP broadcast.

        Returns:
            Set of discovered device IP addresses
        """
        discovered_hosts = set()

        try:
            # Create UDP socket for broadcast discovery
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)  # 3 second timeout
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # HD HomeRun discovery packet
            discovery_packet = b'\x00\x02\x00\x0c\x01\x04\x00\x00\x00\x01\x02\x04\x00\x00\x00\x01'

            # Send broadcast to HD HomeRun discovery port
            sock.sendto(discovery_packet, ('255.255.255.255', 65001))

            # Listen for responses for up to 3 seconds
            start_time = time.time()
            while time.time() - start_time < 3.0:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data and len(data) >= 8:
                        # Extract IP from response if it looks like HD HomeRun response
                        discovered_hosts.add(addr[0])
                        logger.debug(
                            f"Broadcast discovery found device at {addr[0]}")
                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"Error in broadcast receive: {e}")
                    break

            sock.close()

        except Exception as e:
            logger.debug(f"Broadcast discovery failed: {e}")

        return discovered_hosts

    def _discover_single_device(self, host: str) -> Optional[str]:
        """Discover a single HD HomeRun device and get its DeviceAuth.

        Args:
            host: Device hostname or IP address

        Returns:
            Device authentication token, or None if discovery fails
        """
        url = f"http://{host}/discover.json"

        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())

            return data.get("DeviceAuth")

        except Exception:
            # Silently fail for individual device discovery
            return None

    def discover_device(self) -> str:
        """Legacy method for backward compatibility.

        Now calls discover_all_devices() for proper multi-device support.

        Returns:
            Concatenated DeviceAuth string from all discovered devices
        """
        return self.discover_all_devices()

    def get_channels(self) -> List[ChannelInfo]:
        """Get channel lineup from HD HomeRun device.

        Returns:
            List of channel information

        Raises:
            HDHomeRunAPIError: If channel retrieval fails
        """
        if not self.device_auth:
            self.discover_device()

        url = f"http://{self.host}/lineup.json"

        try:
            logger.info("Fetching channel lineup")

            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())

            channels = []
            for channel_data in data:
                channel = ChannelInfo(
                    guide_number=channel_data.get("GuideNumber", ""),
                    guide_name=channel_data.get("GuideName", "Unknown"),
                    url=channel_data.get("URL", ""),
                    image_url=channel_data.get("ImageURL")
                )
                channels.append(channel)

            self._channels = channels
            logger.info(f"Retrieved {len(channels)} channels")

            return channels

        except urllib.error.URLError as e:
            raise HDHomeRunAPIError(f"Failed to get channel lineup: {e}")
        except json.JSONDecodeError as e:
            raise HDHomeRunAPIError(
                f"Invalid JSON response from channel lineup: {e}")

    def get_epg_data(self, days: int = 7, hours_increment: int = 3) -> List[ProgramInfo]:
        """Get EPG data for all channels.

        Args:
            days: Number of days of EPG data to retrieve
            hours_increment: Hours to increment for each request

        Returns:
            List of program information

        Raises:
            HDHomeRunAPIError: If EPG data retrieval fails
        """
        if not self.device_auth:
            self.discover_device()

        if not self._channels:
            self.get_channels()

        # Prepare request data - Try different API endpoints due to potential blocking
        api_endpoints = [
            f"https://api.hdhomerun.com/api/guide?DeviceAuth={self.device_auth}",
            f"https://my.hdhomerun.com/api/guide.php?DeviceAuth={self.device_auth}"
        ]

        post_data = {
            "AppName": "HDHomeRun",
            "AppVersion": "20241024",
            "DeviceAuth": self.device_auth,
            "Platform": "LINUX",
            "PlatformInfo": {"Vendor": "Docker"}
        }

        programs = []
        start_time = datetime.now(pytz.UTC)
        end_time = start_time + timedelta(days=days)
        current_time = start_time

        logger.info(
            f"Retrieving EPG data for {days} days in {hours_increment}-hour increments")

        # Try different user agents if we get 403 errors
        user_agents = [
            "Mozilla/5.0 (Linux; HDHomeRun-XMLTV-Converter)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "HDHomeRun/1.0",
            "Python-urllib/3.11"
        ]

        current_ua_index = 0
        consecutive_403_errors = 0

        try:
            while current_time < end_time:
                timestamp = int(current_time.timestamp())

                success = False
                for endpoint_idx, url_base in enumerate(api_endpoints):
                    url = f"{url_base}&Start={timestamp}"

                    # Encode POST data
                    data_encoded = urllib.parse.urlencode(post_data).encode()

                    # Create request with current user agent
                    req = urllib.request.Request(
                        url, data=data_encoded, method="POST")
                    req.add_header("User-Agent", user_agents[current_ua_index])
                    req.add_header(
                        "Content-Type", "application/x-www-form-urlencoded")

                    # Add additional headers to look more like a real browser
                    req.add_header(
                        "Accept", "application/json, text/plain, */*")
                    req.add_header("Accept-Language", "en-US,en;q=0.9")
                    req.add_header("Cache-Control", "no-cache")

                    logger.debug(
                        f"Fetching EPG data from {url_base} starting from {current_time.isoformat()}")

                    try:
                        with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as response:
                            epg_data = json.loads(response.read().decode())

                        # Process EPG response
                        programs_added = 0
                        for channel_data in epg_data:
                            guide_number = channel_data.get("GuideNumber", "")

                            # Check if this channel is in our lineup
                            if not any(ch.guide_number == guide_number for ch in self._channels):
                                logger.debug(
                                    f"Skipping program for untuned channel {guide_number}")
                                continue

                            # Process programs for this channel
                            for program_data in channel_data.get("Guide", []):
                                program = self._parse_program_data(
                                    program_data, guide_number)

                                # Check for duplicates (overlapping requests)
                                if not any(
                                    p.start_time == program.start_time and
                                    p.title == program.title and
                                    p.guide_number == program.guide_number
                                    for p in programs
                                ):
                                    programs.append(program)
                                    programs_added += 1
                                    logger.debug(
                                        f"Added program: {program.title} on channel {guide_number}")
                                else:
                                    logger.debug(
                                        f"Skipping duplicate program: {program.title}")

                        logger.info(
                            f"Successfully retrieved {programs_added} programs from {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        success = True
                        consecutive_403_errors = 0
                        break

                    except urllib.error.HTTPError as e:
                        if e.code == 403:
                            consecutive_403_errors += 1
                            logger.warning(
                                f"403 Forbidden from endpoint {endpoint_idx + 1}/{len(api_endpoints)} with UA {current_ua_index + 1}/{len(user_agents)}")

                            # If we get 403 errors, try different user agent or endpoint
                            # Last endpoint failed
                            if endpoint_idx == len(api_endpoints) - 1:
                                current_ua_index = (
                                    current_ua_index + 1) % len(user_agents)

                                if consecutive_403_errors >= len(api_endpoints) * len(user_agents):
                                    raise HDHomeRunAPIError(
                                        "Received 403 Forbidden from all endpoints and user agents. "
                                        "HD HomeRun may be blocking requests. This is a known issue "
                                        "mentioned in the HD HomeRun community. Try again later or "
                                        "contact HD HomeRun support."
                                    )
                            continue
                        else:
                            raise HDHomeRunAPIError(
                                f"HTTP error {e.code}: {e.reason}")

                    except urllib.error.URLError as e:
                        logger.error(
                            f"Network error with endpoint {endpoint_idx + 1}: {e}")
                        if endpoint_idx == len(api_endpoints) - 1:  # Last endpoint
                            raise HDHomeRunAPIError(
                                f"Failed to retrieve EPG data: {e}")
                        continue

                if not success:
                    raise HDHomeRunAPIError(
                        "Failed to retrieve EPG data from any endpoint")

                current_time += timedelta(hours=hours_increment)

                # Add a small delay between requests to be respectful
                if current_time < end_time:
                    time.sleep(1)

            logger.info(
                f"Retrieved {len(programs)} programs across all channels")
            return programs

        except HDHomeRunAPIError:
            raise
        except json.JSONDecodeError as e:
            raise HDHomeRunAPIError(
                f"Invalid JSON response from EPG request: {e}")
        except Exception as e:
            raise HDHomeRunAPIError(
                f"Unexpected error retrieving EPG data: {e}")

    def get_xmltv_data(self) -> str:
        """Get XMLTV data directly from HD HomeRun's official XMLTV API.

        This method uses the official HD HomeRun XMLTV endpoint as documented:
        https://github.com/Silicondust/documentation/wiki/XMLTV-Guide-Data

        Returns:
            Raw XMLTV data as string

        Raises:
            HDHomeRunAPIError: If XMLTV data retrieval fails
        """
        if not self.device_auth:
            self.discover_all_devices()

        url = f"https://api.hdhomerun.com/api/xmltv?DeviceAuth={self.device_auth}"

        try:
            logger.info("Fetching XMLTV data from official HD HomeRun API")

            # Create request with proper headers for XMLTV API
            req = urllib.request.Request(url)
            req.add_header("Accept-Encoding", "gzip, deflate")
            req.add_header("User-Agent", "HDHomeRun-XMLTV-Converter/1.0")
            req.add_header("Accept", "application/xml, text/xml, */*")

            with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as response:
                # Handle gzipped response
                import gzip
                import io

                data = response.read()

                # Check if response is gzipped
                if response.headers.get('content-encoding') == 'gzip':
                    data = gzip.decompress(data)

                xmltv_content = data.decode('utf-8')

                logger.info(
                    f"Successfully retrieved XMLTV data ({len(xmltv_content)} characters)")
                return xmltv_content

        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise HDHomeRunAPIError(
                    f"403 Forbidden: HD HomeRun XMLTV API access denied. "
                    f"This usually means:\n"
                    f"1. No active HD HomeRun DVR subscription\n"
                    f"2. Invalid DeviceAuth (tried auth from {len(self.all_device_auths)} devices)\n"
                    f"3. Devices not associated with a DVR account\n"
                    f"Please verify your HD HomeRun DVR subscription and device setup."
                )
            else:
                raise HDHomeRunAPIError(f"HTTP error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise HDHomeRunAPIError(f"Failed to retrieve XMLTV data: {e}")
        except Exception as e:
            raise HDHomeRunAPIError(
                f"Unexpected error retrieving XMLTV data: {e}")

    def _parse_program_data(self, program_data: Dict[str, Any], guide_number: str) -> ProgramInfo:
        """Parse program data from HD HomeRun API response.

        Args:
            program_data: Raw program data from API
            guide_number: Channel guide number

        Returns:
            Parsed program information
        """
        start_time = datetime.fromtimestamp(
            program_data["StartTime"], tz=pytz.UTC)
        end_time = datetime.fromtimestamp(program_data["EndTime"], tz=pytz.UTC)

        # Parse original airdate if available
        original_airdate = None
        if "OriginalAirdate" in program_data:
            original_airdate = datetime.fromtimestamp(
                program_data["OriginalAirdate"],
                tz=pytz.UTC
            )

        return ProgramInfo(
            title=program_data.get("Title", ""),
            start_time=start_time,
            end_time=end_time,
            guide_number=guide_number,
            synopsis=program_data.get("Synopsis"),
            episode_title=program_data.get("EpisodeTitle"),
            episode_number=program_data.get("EpisodeNumber"),
            image_url=program_data.get("ImageURL"),
            original_airdate=original_airdate,
            filters=program_data.get("Filter", []),
            first=program_data.get("First")
        )
