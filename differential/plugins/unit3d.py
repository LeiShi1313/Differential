import re
import json
import argparse
from pathlib import Path
from urllib.parse import quote

from loguru import logger

from differential.plugins.base import Base
from differential.utils.browser import open_link
from differential.utils.mediainfo import get_track_attr


class Unit3D(Base):
    @classmethod
    def get_aliases(cls):
        return "u3d",

    @classmethod
    def get_help(cls):
        return "Unit3D插件，适用于未经过大规模结构改动的Unit3D站点"

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        super().add_parser(parser)
        return parser
