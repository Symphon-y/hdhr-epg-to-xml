"""XMLTV converter for HD HomeRun EPG data.

This module converts HD HomeRun EPG data structures to XMLTV format
following the XMLTV DTD specification.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from .hdhr_client import ChannelInfo, ProgramInfo


logger = logging.getLogger(__name__)


class XMLTVConverter:
    """Converter for transforming HD HomeRun data to XMLTV format."""

    def __init__(self, timezone: str = "UTC"):
        """Initialize the XMLTV converter.

        Args:
            timezone: Target timezone for XMLTV output
        """
        self.timezone = ZoneInfo(timezone)

    def convert_to_xmltv(
        self,
        channels: List[ChannelInfo],
        programs: List[ProgramInfo],
        generator_name: str = "HDHomeRun-XMLTV-Converter",
        generator_url: str = "https://github.com/user/hdhr-xml-converter"
    ) -> ET.Element:
        """Convert HD HomeRun data to XMLTV format.

        Args:
            channels: List of channel information
            programs: List of program information
            generator_name: Name of the generating application
            generator_url: URL of the generating application

        Returns:
            XMLTV root element
        """
        logger.info("Converting HD HomeRun data to XMLTV format")

        # Create root TV element
        tv_root = ET.Element("tv")
        tv_root.set("source-info-name", "HDHomeRun")
        tv_root.set("generator-info-name", generator_name)
        tv_root.set("generator-info-url", generator_url)

        # Add channels
        for channel in channels:
            self._add_channel(tv_root, channel)

        # Add programs
        for program in programs:
            self._add_program(tv_root, program)

        logger.info(
            f"Generated XMLTV with {len(channels)} channels and {len(programs)} programs")
        return tv_root

    def _add_channel(self, tv_root: ET.Element, channel: ChannelInfo) -> None:
        """Add a channel element to the XMLTV document.

        Args:
            tv_root: XMLTV root element
            channel: Channel information
        """
        channel_elem = ET.SubElement(
            tv_root, "channel", id=channel.guide_number)

        # Display name
        display_name = ET.SubElement(channel_elem, "display-name", lang="en")
        display_name.text = channel.guide_name

        # Channel icon
        if channel.image_url:
            ET.SubElement(channel_elem, "icon", src=channel.image_url)

        logger.debug(
            f"Added channel: {channel.guide_name} ({channel.guide_number})")

    def _add_program(self, tv_root: ET.Element, program: ProgramInfo) -> None:
        """Add a program element to the XMLTV document.

        Args:
            tv_root: XMLTV root element
            program: Program information
        """
        try:
            # Convert times to target timezone
            start_time = program.start_time.astimezone(self.timezone)
            end_time = program.end_time.astimezone(self.timezone)

            # Create program element with required attributes
            program_elem = ET.SubElement(
                tv_root,
                "programme",
                start=start_time.strftime("%Y%m%d%H%M%S %z"),
                stop=end_time.strftime("%Y%m%d%H%M%S %z"),
                channel=program.guide_number
            )

            # Title (required)
            title_elem = ET.SubElement(program_elem, "title", lang="en")
            title_elem.text = program.title

            # Sub-title (episode title)
            if program.episode_title:
                subtitle_elem = ET.SubElement(
                    program_elem, "sub-title", lang="en")
                subtitle_elem.text = program.episode_title

            # Description
            if program.synopsis:
                desc_elem = ET.SubElement(program_elem, "desc", lang="en")
                desc_elem.text = self._clean_text(program.synopsis)

            # Categories
            if program.filters:
                for filter_name in program.filters:
                    category_elem = ET.SubElement(
                        program_elem, "category", lang="en")
                    category_elem.text = filter_name

            # Program icon
            if program.image_url:
                ET.SubElement(program_elem, "icon", src=program.image_url)

            # Episode numbering
            if program.episode_number:
                self._add_episode_numbering(
                    program_elem, program.episode_number)

            # Previously shown / new episode handling
            self._add_episode_status(program_elem, program)

            logger.debug(f"Added program: {program.title} at {start_time}")

        except Exception as e:
            logger.error(f"Error adding program '{program.title}': {e}")

    def _add_episode_numbering(self, program_elem: ET.Element, episode_number: str) -> None:
        """Add episode numbering information.

        Args:
            program_elem: Program XML element
            episode_number: Episode number string (e.g., "S01E05")
        """
        try:
            # Add onscreen episode number
            onscreen_elem = ET.SubElement(
                program_elem, "episode-num", system="onscreen")
            onscreen_elem.text = episode_number

            # Try to parse XMLTV-style numbering (series.episode.part/total)
            if "S" in episode_number and "E" in episode_number:
                # Extract series and episode numbers
                series_start = episode_number.index("S") + 1
                series_end = episode_number.index("E")
                episode_start = episode_number.index("E") + 1

                try:
                    series_num = int(
                        episode_number[series_start:series_end]) - 1
                    episode_num = int(episode_number[episode_start:]) - 1

                    # XMLTV format: series.episode.part/total (part is always 0, total is omitted)
                    xmltv_elem = ET.SubElement(
                        program_elem, "episode-num", system="xmltv_ns")
                    xmltv_elem.text = f"{series_num}.{episode_num}.0/0"

                except (ValueError, IndexError):
                    logger.warning(
                        f"Could not parse episode number: {episode_number}")

        except Exception as e:
            logger.warning(
                f"Error processing episode number '{episode_number}': {e}")

    def _add_episode_status(self, program_elem: ET.Element, program: ProgramInfo) -> None:
        """Add episode status (new/previously-shown).

        Args:
            program_elem: Program XML element
            program: Program information
        """
        try:
            if program.first is True:
                # Mark as new episode
                ET.SubElement(program_elem, "new")
                logger.debug(f"Marked '{program.title}' as new episode")
            elif program.original_airdate:
                # Add previously-shown with original air date
                start_time = program.start_time.astimezone(self.timezone)
                start_date = start_time.replace(
                    hour=0, minute=0, second=0, microsecond=0)

                air_date = program.original_airdate.astimezone(self.timezone)
                air_date_only = air_date.replace(
                    hour=0, minute=0, second=0, microsecond=0)

                if air_date_only != start_date:
                    # Different air date, mark as previously shown
                    prev_shown = ET.SubElement(
                        program_elem, "previously-shown")
                    prev_shown.set("start", air_date.strftime("%Y%m%d%H%M%S"))
                elif program.first is False:
                    # Same air date but marked as not first
                    ET.SubElement(program_elem, "previously-shown")
            elif program.first is False:
                # Explicitly marked as not first, no air date available
                ET.SubElement(program_elem, "previously-shown")

        except Exception as e:
            logger.warning(
                f"Error processing episode status for '{program.title}': {e}")

    def _clean_text(self, text: str) -> str:
        """Clean text content for XML.

        Args:
            text: Input text

        Returns:
            Cleaned text suitable for XML
        """
        if not text:
            return ""

        # Remove control characters
        cleaned = "".join(ch for ch in text if ord(ch) >= 32 or ch in '\t\n\r')

        # Remove common TV guide formatting artifacts
        import re

        # Remove feature tags like [HD], [CC], etc.
        cleaned = re.sub(r'\[[A-Z,]+\]', '', cleaned)

        # Remove season/episode info that might be duplicated
        cleaned = re.sub(r'\(?[SE]?\d+\s?Ep\s?\d+[\d/]*\)?', '', cleaned)

        return cleaned.strip()

    def format_xmltv(self, tv_root: ET.Element) -> str:
        """Format XMLTV element as pretty-printed string.

        Args:
            tv_root: XMLTV root element

        Returns:
            Formatted XML string
        """
        # Add proper indentation
        ET.indent(tv_root, space="  ", level=0)

        # Create tree and get string
        tree = ET.ElementTree(tv_root)

        # Return XML declaration + formatted content
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            tv_root,
            encoding="unicode",
            method="xml"
        )
