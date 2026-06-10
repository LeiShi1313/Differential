
from differential.torrent import TorrnetBase


class EasyUpload(TorrnetBase):
    VIDEO_TYPE_MAP = {
        "web": "web",
        "webdl": "web",
        "webrip": "web",
        "remux": "remux",
        "hdtv": "hdtv",
        "encode": "encode",
        "encodes": "encode",
        "bluray": "bluray",
        "bd": "bluray",
        "uhd": "uhdbluray",
        "uhdbluray": "uhdbluray",
        "ultrahdbluray": "uhdbluray",
        "hddvd": "hddvd",
        "dvd": "dvd",
        "dvdr": "dvdr",
        "dvdrip": "dvdrip",
        "cd": "cd",
    }

    VIDEO_CODEC_MAP = {
        "avc": "h264",
        "h264": "h264",
        "x264": "x264",
        "hevc": "hevc",
        "h265": "hevc",
        "x265": "x265",
        "vvc": "vvc",
        "h266": "vvc",
        "av1": "av1",
        "vc1": "vc1",
        "mpeg2": "mpeg2",
        "mpeg4": "mpeg4",
        "xvid": "xvid",
        "divx": "divx",
        "vp9": "vp9",
    }

    AUDIO_CODEC_MAP = {
        "aac": "aac",
        "dd": "dd",
        "dd+": "dd+",
        "ddp": "dd+",
        "eac3": "dd+",
        "ac3": "ac3",
        "dolbydigital": "dd",
        "dolbydigitalplus": "dd+",
        "dtshd": "dtshd",
        "dtshdma": "dtshdma",
        "dtshdmasteraudio": "dtshdma",
        "dtshdhr": "dtshd",
        "dtsx": "dtsx",
        "dts": "dts",
        "atmos": "atmos",
        "dolbydigitalpluswithdolbyatmos": "atmos",
        "truehd": "truehd",
        "dolbytruehd": "truehd",
        "dolbytruehdwithdolbyatmos": "atmos",
        "lpcm": "lpcm",
        "pcm": "lpcm",
        "flac": "flac",
        "ape": "ape",
        "mp3": "mp3",
        "m4a": "m4a",
        "wav": "wav",
        "ogg": "ogg",
        "opus": "opus",
    }

    RESOLUTION_MAP = {
        "8k": "4320p",
        "4320p": "4320p",
        "4k": "2160p",
        "uhd": "2160p",
        "2160p": "2160p",
        "1080p": "1080p",
        "1080i": "1080i",
        "720p": "720p",
        "576p": "576p",
        "480p": "480p",
        "sd": "480p",
    }

    def __init__(self, plugin: TorrnetBase):
        self.plugin = plugin

    @staticmethod
    def _compact(value: str) -> str:
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("_", "")
            .replace("-", "")
            .replace(".", "")
            .replace(" ", "")
            .replace("/", "")
            .replace(":", "")
        )

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except NotImplementedError:
            if not name.startswith('__') and name in dir(TorrnetBase):
                return getattr(self.plugin, name)
            else:
                raise AttributeError(name)

    @property
    def area(self):
        # map EU coutries to EU
        area = self.plugin.area
        area_map = {
            "FR": "EU",
            "IT": "EU",
            "GE": "EU",
            "ES": "EU",
            "PT": "EU",
        }
        if area in area_map:
            return area_map[area]
        return area

    @property
    def video_type(self):
        value = self.plugin.video_type
        return self.VIDEO_TYPE_MAP.get(self._compact(value), value)

    @property
    def source(self):
        value = self.plugin.source
        if not value:
            value = self.plugin.video_type
        return self.VIDEO_TYPE_MAP.get(self._compact(value), value)

    @property
    def video_codec(self):
        value = self.plugin.video_codec
        return self.VIDEO_CODEC_MAP.get(self._compact(value), str(value or "").lower())

    @property
    def audio_codec(self):
        value = self.plugin.audio_codec
        return self.AUDIO_CODEC_MAP.get(self._compact(value), str(value or "").lower())

    @property
    def resolution(self):
        value = self.plugin.resolution
        return self.RESOLUTION_MAP.get(self._compact(value), value)

    @property
    def torrent_info(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "originalDescription": self.original_description,
            "doubanUrl": self.douban_url,
            "doubanInfo": self.douban_info,
            "imdbUrl": self.imdb_url,
            "mediaInfo": self.media_info,
            "mediaInfos": self.media_infos,
            "screenshots": self.screenshots,
            "poster": self.poster,
            "year": self.year,
            "category": self.category,
            "videoType": self.video_type,
            "format": self.format,
            "source": self.source,
            "videoCodec": self.video_codec,
            "audioCodec": self.audio_codec,
            "resolution": self.resolution,
            "area": self.area,
            "movieAkaName": self.movie_aka_name,
            "movieName": self.movie_name,
            "size": self.size,
            "tags": self.tags,
            "otherTags": self.other_tags,
            "comparisons": self.comparisons,
            "isForbidden": False,
            "sourceSiteType": "NexusPHP",
        }
