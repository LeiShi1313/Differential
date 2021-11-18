import argparse

from differential.plugins.base import Base


class NexusPHP(Base):
    @classmethod
    def get_aliases(cls):
        return "nexus", "ne"

    @classmethod
    def get_help(cls):
        return "NexusPHP插件，适用于未经过大规模结构改动的NexusPHP站点"

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        super().add_parser(parser)
        return parser
