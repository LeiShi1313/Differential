from enum import Enum


BOOLEAN_STATES = {
    "1": True,
    "yes": True,
    "true": True,
    "on": True,
    "0": False,
    "no": False,
    "false": False,
    "off": False,
}

BOOLEAN_ARGS = (
    "generate_nfo",
    "make_torrent",
    "easy_upload",
    "trim_description",
    "combine_screenshots",
    "imgbox_family_safe",
    "use_short_bdinfo",
    "use_short_url",
    "reuse_torrent",
    "scan_bdinfo",
    "create_folder",
)

URL_SHORTENER_PATH = "https://2cn.io"


class ImageHosting(Enum):
    PTPIMG = "ptpimg"
    IMGURL = "imgurl"
    CHEVERETO = "chevereto"
    SMMS = "smms"
    BYR = "byr"
    HDB = "hdb"
    IMGBOX = "imgbox"
    CLOUDINARY = "cloudinary"

    @staticmethod
    def parse(s: str):
        if isinstance(s, ImageHosting):
            return s
        if s.lower() == "ptpimg" or s.lower() == 'ptp':
            return ImageHosting.PTPIMG
        elif s.lower() == "imgurl":
            return ImageHosting.IMGURL
        elif s.lower() == "chevereto":
            return ImageHosting.CHEVERETO
        elif s.lower() == "smms" or s.lower() == "sm.ms":
            return ImageHosting.SMMS
        elif s.lower() == "byr":
            return ImageHosting.BYR
        elif s.lower() == "hdb" or s.lower() == 'hdbits':
            return ImageHosting.HDB
        elif s.lower() == "imgbox":
            return ImageHosting.IMGBOX
        elif s.lower() == "cloudinary":
            return ImageHosting.CLOUDINARY
        raise ValueError(f"不支持的图床：{s}")
