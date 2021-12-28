import argparse

from differential.plugins.nexusphp import NexusPHP


class GreatPosterWall(NexusPHP):

    @classmethod
    def get_aliases(cls):
        return 'gpw',

    @classmethod
    def get_help(cls):
        return 'GreatPosterWall插件，适用于GreatPosterWall'

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        return super().add_parser(parser)

    def __init__(self, **kwargs):
        super().__init__(upload_url="https://greatposterwall.com/upload.php", **kwargs)
