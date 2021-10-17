import argparse

from differential.plugins.nexusphp import NexusPHP


class CHDBits(NexusPHP):

    @classmethod
    def get_help(cls):
        return 'CHDBits插件，适用于CHDBits'

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        return super().add_parser(parser)

    def __init__(self, folder: str, url: str, **kwargs):
        super().__init__(folder, url, upload_url="https://chdbits.co/upload.php", **kwargs)
