import argparse

from differential.plugins.nexusphp import NexusPHP


class PTerClub(NexusPHP):

    @classmethod
    def get_aliases(cls):
        return 'pter',

    @classmethod
    def get_help(cls):
        return 'PTerClub插件，适用于PTerClub'

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        return super().add_parser(parser)

    def __init__(self, folder: str, url: str, **kwargs):
        super().__init__(folder, url, upload_url="https://pterclub.com/upload.php", **kwargs)
