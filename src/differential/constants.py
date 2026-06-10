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
    "auto_feed",
    "trim_description",
    "combine_screenshots",
    "imgbox_family_safe",
    "use_short_bdinfo",
    "use_short_url",
    "reuse_torrent",
    "scan_bdinfo",
    "create_folder",
    "optimize_screenshot",
    "non_interactive",
)

SCREENSHOT_TONEMAP_STATES = {
    "auto": "auto",
    "automatic": "auto",
    "detect": "auto",
    "detected": "auto",
    "1": "always",
    "yes": "always",
    "true": "always",
    "on": "always",
    "always": "always",
    "force": "always",
    "forced": "always",
    "0": "never",
    "no": "never",
    "false": "never",
    "off": "never",
    "never": "never",
    "disable": "never",
    "disabled": "never",
}

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
    LSKY = "lsky"

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
        elif s.lower() == "lsky":
            return ImageHosting.LSKY
        raise ValueError(f"不支持的图床：{s}")
