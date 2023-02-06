import argparse

from differential.plugins.base import Base


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
