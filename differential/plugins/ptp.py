import argparse

from differential.plugins.base import Base


class PassThePopcorn(Base):
    @classmethod
    def get_aliases(cls):
        return "PTP","ptp",

    @classmethod
    def get_help(cls):
        return "PTP插件，适用于PTP"

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        return super().add_parser(parser)

    def __init__(self, **kwargs):
        super().__init__(upload_url="https://passthepopcorn.me/upload.php", **kwargs)
