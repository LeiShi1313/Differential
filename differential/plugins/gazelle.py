import argparse

from differential.base_plugin import Base


class Gazelle(Base):
    @classmethod
    def get_aliases(cls):
        return "gz",

    @classmethod
    def get_help(cls):
        return "Gazelle插件，适用于未经过大规模结构改动的Gazelle站点"

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        super().add_parser(parser)
        return parser
