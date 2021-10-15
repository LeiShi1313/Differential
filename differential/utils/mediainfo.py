import os
import sys
import shutil
import platform
import argparse
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, List
from configparser import ConfigParser

from loguru import logger
from pymediainfo import Track, MediaInfo

from differential.constants import ImageHosting, BOOLEAN_STATES, BOOLEAN_ARGS


def get_track_attr(
    track: Track, name: str, attr_only: bool = False, use_other: bool = True
) -> Optional[str]:
    alternative_name = None
    if name == "ID":
        alternative_name = "track_id"
    elif name == "Format/Info":
        alternative_name = "format_info"
    elif name == "Codec ID/Info":
        alternative_name = "codec_id_info"
    elif name == "Channel(s)":
        alternative_name = "channel_s"
    elif name == "Bits/(Pixel*Frame)":
        alternative_name = "bits__pixel_frame"

    attr = None
    if alternative_name:
        attr = getattr(track, alternative_name)
    if not attr and use_other:
        attrs = getattr(track, "other_" + name.replace(" ", "_").lower())
        # Always get the first options
        if attrs and len(attrs):
            attr = attrs[0]
    if not attr:
        attr = getattr(track, name.replace(" ", "_").lower())

    if attr:
        return attr if attr_only else "{}: {}".format(name, attr)
    return None


def get_track_attrs(track: Track, names: List[str], join_str: str = " ") -> str:
    attrs = []
    for name in names:
        attr = get_track_attr(track, name, True)
        if attr:
            attrs.append(attr)
    return join_str.join(attrs)


def get_full_mediainfo(mediainfo: MediaInfo) -> str:
    track_format = {
        "general": [
            "Unique ID",
            "Complete name",
            "Format",
            "Format version",
            "Duration",
            "Overall bit rate",
            "Encoded date",
            "Writing application",
            "Writing library",
            "Attachments",
        ],
        "video": [
            "ID",
            "Format",
            "Format/Info",
            "Format profile",
            "Codec ID",
            "Duration",
            "Bit rate",
            "Width",
            "Height",
            "Display aspect ratio",
            "Frame rate mode",
            "Frame rate",
            "Color space",
            "Chroma subsampling",
            "Bit depth",
            "Bits/(Pixel*Frame)",
            "Stream size",
            "Writing library",
            "Encoding settings",
            "Title",
            "Default",
            "Forced",
            "Color range",
            "Color primaries",
            "Transfer characteristics",
            "Matrix coefficients",
            "Mastering display color primaries",
            "Mastering display luminance",
            "Maximum Content Light Level",
            "Maximum Frame-Average Light Level",
        ],
        "audio": [
            "ID",
            "Format",
            "Format/Info",
            "Commercial name",
            "Codec ID",
            "Duration",
            "Bit rate mode",
            "Bit rate",
            "Channel(s)",
            "Channel layout",
            "Sampling rate",
            "Frame rate",
            "Compression mode",
            "Stream size",
            "Title",
            "Language",
            "Service kind",
            "Default",
            "Forced",
        ],
        "text": [
            "ID",
            "Format",
            "Muxing mode",
            "Codec ID",
            "Codec ID/Info",
            "Duration",
            "Bit rate",
            "Count of elements",
            "Stream size",
            "Title",
            "Language",
            "Default",
            "Forced",
        ],
    }
    media_info = ""
    for track_name in track_format.keys():
        for idx, track in enumerate(getattr(mediainfo, "{}_tracks".format(track_name))):
            if len(getattr(mediainfo, "{}_tracks".format(track_name))) > 1:
                media_info += "{} #{}\n".format(track_name.capitalize(), idx + 1)
            else:
                media_info += "{}\n".format(track_name.capitalize())

            media_info += (
                "\n".join(
                    filter(
                        lambda a: a is not None,
                        [
                            get_track_attr(track, name)
                            for name in track_format[track_name]
                        ],
                    )
                )
                + "\n\n"
            )
    # Special treatment with charters
    for track in mediainfo.menu_tracks:
        # Assuming there are always one menu tracks
        media_info += "Menu\n"
        for name in dir(track):
            # TODO: needs improvement
            if name[:2].isdigit():
                media_info += "{} : {}\n".format(
                    name[:-3].replace("_", ":") + "." + name[-3:], getattr(track, name)
                )
        media_info += "\n"
    media_info.strip()
    return media_info
