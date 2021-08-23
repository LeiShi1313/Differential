import re
import json
import argparse
from pathlib import Path
from urllib.parse import quote

from loguru import logger

from differential.utils import open_link
from differential.plugins.base import Base
from differential.utils import get_track_attr


class NexusPHP(Base):
    @classmethod
    def get_aliases(cls):
        return "nexus", "ne"

    @classmethod
    def get_help(cls):
        return "NexusPHP插件，适用于未经过大规模结构改动的NexusPHP站点"

    @classmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        super().add_parser(parser)
        parser.add_argument(
            "--upload-url",
            type=str,
            help="PT站点上传的路径，一般为https://xxxxx.com/upload.php",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--encoder-log", type=str, help="压制log的路径", default=argparse.SUPPRESS
        )
        parser.add_argument(
            "--no-easy-upload",
            action="store_false",
            help="不使用树大Easy Upload插件自动填充，在命令行显示所有数据",
            dest="easy_upload",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--trim-description",
            action="store_true",
            help="是否在生成的链接中省略种子描述，该选项主要是为了解决浏览器限制URL长度的问题，默认关闭",
            default=argparse.SUPPRESS,
        )
        return parser

    def __init__(
        self,
        folder,
        url,
        upload_url: str,
        easy_upload: bool = True,
        trim_description: bool = False,
        encoder_log: str = "",
        **kwargs,
    ):
        super().__init__(folder, url, **kwargs)
        self.upload_url = upload_url
        self.easy_upload = easy_upload
        self.trim_description = trim_description
        self.encoder_log = encoder_log

    @property
    def title(self):
        # TODO: Either use file name or generate from mediainfo and ptgen
        return ""

    @property
    def subtitle(self):
        if not self._ptgen.get("site") == "douban":
            return ""
        subtitle = f"{'/'.join(self._ptgen.get('this_title', []) + self._ptgen.get('aka', []))}"
        if self._ptgen.get("director"):
            subtitle += (
                f"【导演：{'/'.join([d.get('name') for d in self._ptgen.get('director')])}】"
            )
        if self._ptgen.get("writer"):
            subtitle += (
                f"【编剧：{'/'.join([w.get('name') for w in self._ptgen.get('writer')])}】"
            )
        if self._ptgen.get("cast"):
            subtitle += (
                f"【主演：{'/'.join([c.get('name') for c in self._ptgen.get('cast')[:3]])}】"
            )
        return subtitle

    @property
    def mediaInfo(self):
        return self._get_full_mediainfo()

    @property
    def description(self):
        return "{}\n\n[quote]{}{}[/quote]\n\n{}".format(
            self._ptgen.get("format"),
            self.mediaInfo,
            "\n\n" + self.parsed_encoder_log if self.parsed_encoder_log else "",
            "\n".join([f"[img]{url}[/img]" for url in self._screenshots]),
        )

    @property
    def doubanUrl(self):
        if self._ptgen.get("site") == "douban":
            return f"https://movie.douban.com/subject/{self._ptgen.get('sid')}"
        return ""

    @property
    def imdbUrl(self):
        return self._ptgen.get("imdb_link", "")

    @property
    def screenshots(self):
        return self._screenshots

    @property
    def poster(self):
        return self._ptgen.get("poster", "")

    @property
    def year(self):
        return self._ptgen.get("year", "")

    @property
    def category(self):
        if "演唱会" in self._ptgen.get("tags", []) and "音乐" in self._ptgen.get(
            "genre", []
        ):
            return "concert"
        imdb_genre = self._imdb.get("genre", [])
        if "Documentary" in imdb_genre:
            return "documentary"
        imdb_type = self._imdb.get("@type", "")
        if imdb_type == "Movie":
            return "movie"
        if imdb_type == "TVSeries":
            return "tvPack"
        return imdb_type

    @property
    def videoType(self):
        if "webdl" in self.folder.lower() or "web-dl" in self.folder.lower():
            return "web"
        elif "remux" in self.folder.lower():
            return "remux"
        elif "hdtv" in self.folder.lower():
            return "hdtv"
        elif any(e in self.folder.lower() for e in ("x264", "x265")):
            return "encode"
        elif "bluray" in self.folder.lower() and not any(
            e in self.folder.lower() for e in ("x264", "x265")
        ):
            return "bluray"
        elif "uhd" in self.folder.lower():
            return "uhdbluray"
        for track in self._mediainfo.tracks:
            if track.track_type == "Video":
                if track.encoding_settings:
                    return "encode"
        return ""

    @property
    def format(self):
        # TODO: Maybe read from mediainfo
        return self._main_file.suffix

    @property
    def source(self):
        return ""

    @property
    def videoCodec(self):
        for track in self._mediainfo.tracks:
            if track.track_type == "Video":
                if track.encoded_library_name:
                    return track.encoded_library_name
                if track.commercial_name == "AVC":
                    return "x264"
        return ""

    @property
    def audioCodec(self):
        codec_map = {
            "AAC": "aac",
            "Dolby Digital Plus": "dd+",
            "Dolby Digital": "dd",
            "DTS-HD Master Audio": "dtshdma",
            "Dolby Digital Plus with Dolby Atmos": "atmos",
            "Dolby TrueHD": "truehd",
        }
        for track in self._mediainfo.tracks:
            if track.track_type == "Audio":
                if track.format_info == "Audio Coding 3":
                    return "ac3"
                if track.format_info == "Free Lossless Audio Codec":
                    return "flac"
                if track.commercial_name in codec_map:
                    return codec_map.get(track.commercial_name)
                # TODO: other formats
                # dts: "3",
                # lpcm: "21",
                # dtsx: "3",
                # ape: "2",
                # wav: "22",
                # mp3: "4",
                # m4a: "5",
                # other: "7"
        return ""

    @property
    def resolution(self):
        for track in self._mediainfo.tracks:
            if track.track_type == "Video":
                if track.height <= 480:
                    return "480p"
                elif track.height <= 576:
                    return "576p"
                elif track.height <= 720:
                    return "720p"
                elif track.height <= 1080:
                    if getattr(track, "scan_type__store_method") == "InterleavedFields":
                        return "1080i"
                    return "1080p"
                elif track.height <= 2160:
                    return "2160p"
                elif track.height <= 4320:
                    return "4320p"
        return ""

    @property
    def area(self):
        area_map = {
            "中国大陆": "CN",
            "中国香港": "HK",
            "中国台湾": "TW",
            "美国": "US",
            "日本": "JP",
            "韩国": "KR",
            "印度": "IND",
            "法国": "EU",
            "意大利": "EU",
            "德国": "EU",
            "西班牙": "EU",
            "葡萄牙": "EU",
        }
        regions = self._ptgen.get("region", [])
        for area in area_map.keys():
            if area in regions:
                return area_map[area]
        return ""

    @property
    def movieName(self):
        if self._ptgen.get("site") == "imdb":
            return self._ptgen.get("name", "")
        if self._ptgen.get("site") == "douban":
            return self._ptgen.get("aka", [""])[0]
        return ""

    @property
    def movieAkaName(self):
        return ""

    @property
    def size(self):
        for track in self._mediainfo.tracks:
            if track.track_type == "General":
                return track.file_size
        return ""

    @property
    def tags(self):
        tags = {}
        for track in self._mediainfo.tracks:
            if track.track_type == "General":
                if track.audio_language_list and "Chinese" in track.audio_language_list:
                    tags["chinese_audio"] = True
                if track.text_language_list and "Chinese" in track.text_language_list:
                    tags["chinese_subtitle"] = True
        # TODO: hdr, hdr10_plus, dolby_vision, diy, cantonese_audio, false,dts_x, dolby_atoms
        return tags

    @property
    def parsed_encoder_log(self):
        log = ""
        if self.encoder_log and Path(self.encoder_log).is_file():
            with open(self.encoder_log, "r") as f:
                log = f.read()
        m = re.search(
            r".*?(x264 \[info\]: frame I:.*?)\n"
            r".*?(x264 \[info\]: frame P:.*?)\n"
            r".*?(x264 \[info\]: frame B:.*?)\n"
            r".*?(x264 \[info\]: consecutive B-frames:.*?)\n",
            log,
        )
        if m:
            return "\n".join(m.groups())
        m = re.search(
            r".*?(x265 \[info\]: frame I:.*?)\n"
            r".*?(x265 \[info\]: frame P:.*?)\n"
            r".*?(x265 \[info\]: frame B:.*?)\n"
            r".*?(x265 \[info\]: Weighted P\-Frames:.*?)\n"
            r".*?(x265 \[info\]: Weighted B\-Frames:.*?)\n"
            r".*?(x265 \[info\]: consecutive B\-frames:.*?)\n",
            log,
        )
        if m:
            return "\n".join(m.groups())
        return ""

    @property
    def torrentInfo(self):
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "doubanUrl": self.doubanUrl,
            "imdbUrl": self.imdbUrl,
            "mediaInfo": self.mediaInfo,
            "screenshots": self.screenshots,
            "poster": self.poster,
            "year": self.year,
            "category": self.category,
            "videoType": self.videoType,
            "format": self.format,
            "source": self.source,
            "videoCodec": self.videoCodec,
            "audioCodec": self.audioCodec,
            "resolution": self.resolution,
            "area": self.area,
            "movieAkaName": self.movieAkaName,
            "movieName": self.movieName,
            "size": self.size,
            "tags": self.tags,
        }

    def upload(self):
        self._prepare()
        if self.easy_upload:
            torrent_info = self.torrentInfo
            if self.trim_description:
                # 直接打印简介部分来绕过浏览器的链接长度限制
                torrent_info["description"] = ""
            logger.trace(f"torrent_info: {torrent_info}")
            link = f"{self.upload_url}#torrentInfo={quote(json.dumps(torrent_info))}"
            logger.info(f"已生成自动上传链接：{link}")
            if self.trim_description:
                logger.info(f"种子描述：\n{self.description}")
            open_link(link)
        else:
            for key in [
                "title",
                "subtitle",
                "doubanUrl",
                "imdbUrl",
                "mediaInfo",
                "description",
            ]:
                logger.info(f"{key}:\n{self.torrentInfo[key]}")

    @property
    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--easy-upload",
            action="store_true",
            help="自动打开浏览器，利用Easy Upload填充内容",
            default=argparse.SUPPRESS,
        )
        return parser
