import argparse

from differential.plugins.base import Base


class HDBits(Base):
    @classmethod
    def get_aliases(cls):
        return "HDB","hdb",

    @classmethod
    def get_help(cls):
        return "HDBits插件，适用于HDBits"

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        return super().add_parser(parser)

    def __init__(self, **kwargs):
        super().__init__(upload_url="https://hdbits.org/upload", **kwargs)

    @property
    def media_info(self):
        if self.is_bdmv:
            return ''
        else:
            return get_full_mediainfo(self._mediainfo)


    @property
    def description(self):
        description = ''
        if self.is_bdmv:
            description += "[quote]{}[/quote]\n\n".format(self._bdinfo)
        # TODO: missing encoder log
        description += "\n".join([f"{uploaded}" for uploaded in self._screenshots])
        return description