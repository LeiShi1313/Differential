import os
import sys
import shutil
import platform
import argparse
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional
from configparser import ConfigParser

from loguru import logger
from pymediainfo import Track

from differential.constants import ImageHosting, BOOLEAN_STATES, BOOLEAN_ARGS


def make_torrent_progress(torrent, filepath, pieces_done, pieces_total):
    logger.info(f'制种进度：{pieces_done/pieces_total*100:3.0f} %')


def find_binary(name: str, alternative_names: list = None) -> Optional[Path]:
    if alternative_names is None:
        alternative_names = []

    path = os.environ.get(f"{name.upper()}PATH")
    if path:
        pp = Path(path)
        if not pp.is_file():
            logger.error(f"{p}不是可执行文件！")
            sys.exit(1)
        return pp
    for n in [name] + alternative_names:
        if n in os.listdir(os.getcwd()):
            return Path(os.getcwd()).joinpath(n)
        _which = shutil.which(n)
        if _which:
            return Path(_which)
        if platform.system() == "Windows":
            if f"{n}.exe" in os.listdir(os.getcwd()):
                return Path(os.getcwd()).joinpath(f"{n}.exe")
            _which = shutil.which(f"{n}.exe")
            if _which:
                return Path(_which)

    logger.error(
        f"{name} not found in path, you can specify its binary location "
        f"by setting environment variable: {name.upper()}PATH or put it under the tool folder."
    )
    return None


def execute(binary_name: str, args: str, abort: bool = False) -> str:
    executable = find_binary(binary_name)
    if executable is None:
        if abort:
            sys.exit(1)
        else:
            return ''
    cmd = f'"{executable}" {args}'
    logger.trace(cmd)
    proc = subprocess.run(cmd, shell=True, capture_output=True)
    logger.trace(proc)
    return "\n".join([proc.stdout.decode(), proc.stderr.decode()])


def ffmpeg(path: Path, extra_args: str = "") -> str:
    return execute("ffmpeg", f'-i "{path.absolute()}" {extra_args}')


def ffprobe(path: Path) -> str:
    return execute("ffprobe", f'-i "{path.absolute()}"')


def open_link(link: str):
    try:
        browser = webbrowser.get()
    except webbrowser.Error:
        browser = None

    if browser is None or isinstance(browser, webbrowser.GenericBrowser):
        logger.info(f"未找到浏览器，请直接复制以下链接：{link}")
    else:
        browser.open(link, new=1)


def get_track_attr(track: Track, name) -> Optional[str]:
    alternative_name = None
    if name == 'ID':
        alternative_name = 'track_id'
    elif name == 'Format/Info':
        alternative_name = 'format_info'
    elif name == 'Codec ID/Info':
        alternative_name = 'codec_id_info'
    elif name == 'Channel(s)':
        alternative_name = 'channel_s'
    elif name == 'Bits/(Pixel*Frame)':
        alternative_name = 'bits__pixel_frame'

    attr = None
    if alternative_name:
        attr = getattr(track, alternative_name)
    if not attr:
        attrs = getattr(track, "other_" + name.replace(' ', '_').lower())
        # Always get the first options
        if attrs and len(attrs):
            attr = attrs[0]
    if not attr:
        attr = getattr(track, name.replace(' ', '_').lower())

    if attr:
        return "{}: {}".format(name, attr)


def merge_config(args: argparse.Namespace) -> dict:
    merged = {}
    config = None
    if hasattr(args, 'config'):
        config = ConfigParser()
        config.read(args.config)

    if config:
        # First use the args in the general section
        for arg in config.defaults().keys():
            merged[arg] = config.defaults()[arg]

        # Then use the args from config file matching the plugin name
        if args.plugin in config.sections():
            for arg in config[args.plugin].keys():
                merged[arg] = config[args.plugin][arg]

    # Args from command line has the highest priority
    for arg in vars(args):
        merged[arg] = getattr(args, arg)

    # Handling non-str non-int args
    if 'image_hosting' in merged:
        merged['image_hosting'] = ImageHosting.parse(merged['image_hosting'])
    if any(arg in BOOLEAN_ARGS for arg in merged.keys()):
        for arg in BOOLEAN_ARGS:
            if arg in merged and not isinstance(merged[arg], bool):
                # Might be buggy to always assume not recognized args is False
                merged[arg] = BOOLEAN_STATES.get(merged[arg], False)

    # Parse int args
    for arg in merged:
        if isinstance(merged[arg], str) and merged[arg].isdigit():
            merged[arg] = int(merged[arg])
    return merged
