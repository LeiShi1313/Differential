from enum import Enum


BOOLEAN_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                  '0': False, 'no': False, 'false': False, 'off': False}

BOOLEAN_ARGS = ('generate_nfo', 'make_torrent', 'easy_upload', 'trim_description', 'combine_screenshots', 'use_short_bdinfo', 'use_short_url')

URL_SHORTENER_PATH = 'https://lg.to'


class ImageHosting(Enum):
    PTPIMG = 'ptpimg'
    IMGURL = 'imgurl'
    CHEVERETO = 'chevereto'
    SMMS = 'smms'
    BYR = 'byr'

    @staticmethod
    def parse(s: str):
        if isinstance(s, ImageHosting):
            return s
        if s.lower() == 'ptpimg':
            return ImageHosting.PTPIMG
        elif s.lower() == 'imgurl':
            return ImageHosting.IMGURL
        elif s.lower() == 'chevereto':
            return ImageHosting.CHEVERETO
        elif s.lower() == 'smms':
            return ImageHosting.SMMS
        elif s.lower() == 'byr':
            return ImageHosting.BYR
        raise ValueError(f"不支持的图床：{s}")
