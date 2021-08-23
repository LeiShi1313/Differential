import argparse

from differential.plugins.nexusphp import NexusPHP


class LemonHD(NexusPHP):

    @classmethod
    def get_help(cls):
        return 'LemonHD插件，适用于LemnonHD电影及电视剧上传'

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        super().add_parser(parser)
        parser.add_argument('--upload-type', type=str, help="上传类型，默认为电影（movies），其他类型参见柠檬上传URL",
                            default=argparse.SUPPRESS)

    def __init__(self, folder: str, url: str, upload_type='movie', **kwargs):
        super().__init__(folder, url, upload_url="https://lemonhd.org/upload_{}.php".format(upload_type), **kwargs)
