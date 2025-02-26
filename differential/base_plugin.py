import re
import json
import argparse
from pathlib import Path
from typing import Optional
from itertools import chain
from urllib.parse import quote
from abc import ABC, abstractmethod

from loguru import logger

from differential.plugin_register import PluginRegister
from differential.torrent import TorrnetBase
from differential.constants import ImageHosting
from differential.utils.browser import open_link
from differential.utils.torrent import make_torrent
from differential.utils.parse import parse_encoder_log
from differential.utils.uploader import EasyUpload, AutoFeed
from differential.utils.mediainfo_handler import MediaInfoHandler
from differential.utils.ptgen_handler import PTGenHandler
from differential.utils.screenshot_handler import ScreenshotHandler
from differential.utils.nfo import generate_nfo
from differential.utils.ptgen.base import PTGenData, DataType
from differential.utils.ptgen.imdb import IMDBData
from differential.utils.ptgen.douban import DoubanData


class Base(ABC, TorrnetBase, metaclass=PluginRegister):
    @classmethod
    @abstractmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "-c",
            "--config",
            type=str,
            help="配置文件的路径，默认为config.ini",
            default="config.ini",
        )
        parser.add_argument(
            "-l", "--log", type=str, help="log文件的路径", default=argparse.SUPPRESS
        )
        parser.add_argument(
            "-f",
            "--folder",
            type=str,
            help="种子文件夹的路径",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "-u", "--url", type=str, help="豆瓣链接", default=argparse.SUPPRESS
        )
        parser.add_argument(
            "-uu",
            "--upload-url",
            type=str,
            help="PT站点上传的路径，一般为https://xxxxx.com/upload.php",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "-t",
            "--make-torrent",
            action="store_true",
            help="是否制种，默认否",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "-n",
            "--generate-nfo",
            action="store_true",
            help="是否用MediaInfo生成NFO文件，默认否",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "-s",
            "--screenshot-count",
            type=int,
            help="截图数量，默认为0，即不生成截图",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--screenshot-path",
            type=str,
            help="截图文件夹，会在提供的文件夹中查找图片并上传，不会再生成截图",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--create-folder",
            action="store_true",
            dest="create_folder",
            help="如果目标为文件，创建文件夹并把目标文件放入其中",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--use-short-bdinfo",
            action="store_true",
            help="使用QUICK SUMMARY作为BDInfo，默认使用完整BDInfo",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--no-scan-bdinfo",
            action="store_false",
            dest="scan_bdinfo",
            help="如果为原盘，跳过扫描BDInfo",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--optimize-screenshot",
            action="store_true",
            help="是否压缩截图（无损），默认压缩",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--image-hosting",
            type=ImageHosting,
            help=f"图床的类型，现在支持{','.join(i.value for i in ImageHosting)}",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--ptpimg-api-key",
            type=str,
            help="PTPIMG的API Key",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--hdbits-cookie",
            type=str,
            help="HDBits的Cookie",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--hdbits-thumb-size",
            type=str,
            help="HDBits图床缩略图的大小，默认w300",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--chevereto-hosting-url",
            type=str,
            help="自建chevereto图床的地址",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--chevereto-api-key",
            type=str,
            help="自建Chevereto的API Key，详情见https://v3-docs.chevereto.com/api/#api-call",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--chevereto-username",
            type=str,
            help="如果自建Chevereto的API未开放，请设置username和password",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--chevereto-password",
            type=str,
            help="如果自建Chevereto的API未开放，请设置username和password",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--imgurl-api-key",
            type=str,
            help="Imgurl的API Key",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--smms-api-key", type=str, help="SM.MS的API Key", default=argparse.SUPPRESS
        )
        parser.add_argument(
            "--byr-cookie",
            type=str,
            help="BYR的Cookie，可登录后访问任意页面F12查看",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--byr-alternative-url",
            type=str,
            help="BYR反代地址(如有)，可为空",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--cloudinary-cloud-name",
            type=str,
            help="Cloudinary的cloud name",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--cloudinary-api-key",
            type=str,
            help="Cloudinary的api key",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--cloudinary-api-secret",
            type=str,
            help="Cloudinary的api secret",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--imgbox-username",
            type=str,
            help="Imgbox图床登录用户名，留空则匿名上传",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--imgbox-password",
            type=str,
            help="Imgbox图床登录密码，留空则匿名上传",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--imgbox-thumbnail-size",
            type=str,
            help="Imgbox图床缩略图的大小，默认300r",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--imgbox-family-safe",
            action="store_true",
            dest="imgbox_family_safe",
            help="Imgbox图床是否是非成人内容",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--imgbox-not-family-safe",
            action="store_false",
            dest="imgbox_family_safe",
            help="Imgbox图床是否是成人内容",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--ptgen-url", type=str, help="自定义PTGEN的地址", default=argparse.SUPPRESS
        )
        parser.add_argument(
            "--ptgen-retry",
            type=int,
            help="PTGEN重试次数，默认为3次",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--announce-url",
            type=str,
            help="制种时announce地址",
            default=argparse.SUPPRESS,
        )

        parser.add_argument(
            "--encoder-log", type=str, help="压制log的路径", default=argparse.SUPPRESS
        )
        upload_option_group = parser.add_mutually_exclusive_group()
        upload_option_group.add_argument(
            "--easy-upload",
            action="store_true",
            help="使用树大Easy Upload插件自动填充",
            dest="easy_upload",
            default=argparse.SUPPRESS,
        )
        upload_option_group.add_argument(
            "--auto-feed",
            action="store_true",
            help="使用明日大Auto Feed插件自动填充",
            dest="auto_feed",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--trim-description",
            action="store_true",
            help="是否在生成的链接中省略种子描述，该选项主要是为了解决浏览器限制URL长度的问题，默认关闭",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--use-short-url",
            action="store_true",
            help="是否缩短生成的上传链接",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--no-reuse-torrent",
            action="store_false",
            dest="reuse_torrent",
            help="是否直接在差速器已经制作的种子基础上重新制种",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--from-torrent",
            type=str,
            help="提供种子，在此基础上，直接洗种生成新种子",
            default=argparse.SUPPRESS,
        )
        return parser

    def __init__(
        self,
        folder: str,
        url: str,
        upload_url: str,
        screenshot_count: int = 0,
        screenshot_path: str = None,
        optimize_screenshot: bool = True,
        create_folder: bool = False,
        use_short_bdinfo: bool = False,
        scan_bdinfo: bool = True,
        image_hosting: ImageHosting = ImageHosting.PTPIMG,
        chevereto_hosting_url: str = "",
        imgurl_hosting_url: str = "",
        ptpimg_api_key: str = None,
        hdbits_cookie: str = None,
        hdbits_thumb_size: str = "w300",
        chevereto_api_key: str = None,
        chevereto_username: str = None,
        chevereto_password: str = None,
        cloudinary_cloud_name: str = None,
        cloudinary_api_key: str = None,
        cloudinary_api_secret: str = None,
        imgurl_api_key: str = None,
        smms_api_key: str = None,
        byr_cookie: str = None,
        byr_alternative_url: str = None,
        imgbox_username: str = None,
        imgbox_password: str = None,
        imgbox_thumbnail_size: str = "300r",
        imgbox_family_safe: bool = True,
        ptgen_url: str = "https://ptgen.lgto.workers.dev",
        second_ptgen_url: str = "https://api.slyw.me",
        announce_url: str = "https://example.com",
        ptgen_retry: int = 3,
        generate_nfo: bool = False,
        make_torrent: bool = False,
        easy_upload: bool = False,
        auto_feed: bool = False,
        trim_description: bool = False,
        use_short_url: bool = False,
        encoder_log: str = "",
        reuse_torrent: bool = True,
        from_torrent: str = None,
        **kwargs,
    ):
        self.folder = Path(folder)
        self.url = url
        self.upload_url = upload_url

        self.announce_url = announce_url
        self.generate_nfo = generate_nfo
        self.make_torrent = make_torrent
        self.easy_upload = easy_upload
        self.auto_feed = auto_feed
        self.trim_description = trim_description
        self.use_short_url = use_short_url
        self.encoder_log = encoder_log
        self.reuse_torrent = reuse_torrent
        self.from_torrent = from_torrent

        self.mediainfo_handler = MediaInfoHandler(
            folder=self.folder,
            create_folder=create_folder,
            use_short_bdinfo=use_short_bdinfo,
            scan_bdinfo=scan_bdinfo,
        )
        self.ptgen_handler = PTGenHandler(
            url=self.url,
            ptgen_url=ptgen_url,
            second_ptgen_url=second_ptgen_url,
            ptgen_retry=ptgen_retry,
        )
        self.screenshot_handler = ScreenshotHandler(
            folder=self.folder,
            screenshot_count=screenshot_count,
            screenshot_path=screenshot_path,
            optimize_screenshot=optimize_screenshot,
            image_hosting=image_hosting,
            chevereto_hosting_url=chevereto_hosting_url,
            imgurl_hosting_url=imgurl_hosting_url,
            ptpimg_api_key=ptpimg_api_key,
            hdbits_cookie=hdbits_cookie,
            hdbits_thumb_size=hdbits_thumb_size,
            chevereto_username=chevereto_username,
            chevereto_password=chevereto_password,
            chevereto_api_key=chevereto_api_key,
            cloudinary_cloud_name=cloudinary_cloud_name,
            cloudinary_api_key=cloudinary_api_key,
            cloudinary_api_secret=cloudinary_api_secret,
            imgurl_api_key=imgurl_api_key,
            smms_api_key=smms_api_key,
            byr_cookie=byr_cookie,
            byr_alternative_url=byr_alternative_url,
            imgbox_username=imgbox_username,
            imgbox_password=imgbox_password,
            imgbox_thumbnail_size=imgbox_thumbnail_size,
            imgbox_family_safe=imgbox_family_safe,
        )

        self.main_file: Optional[Path] = None
        self.ptgen: Optional[PTGenData] = None
        self.douban: Optional[DoubanData] = None
        self.imdb: Optional[IMDBData] = None

    def upload(self):
        self._prepare()
        if self.easy_upload:
            torrent_info = self.easy_upload_torrent_info
            if self.trim_description:
                # 直接打印简介部分来绕过浏览器的链接长度限制
                torrent_info["description"] = ""
            logger.trace(f"torrent_info: {torrent_info}")
            link = f"{self.upload_url}#torrentInfo={quote(json.dumps(torrent_info))}"
            logger.trace(f"已生成自动上传链接：{link}")
            if self.trim_description:
                logger.info(f"种子描述：\n{self.description}")
            open_link(link, self.use_short_url)
        elif self.auto_feed:
            link = f"{self.upload_url}#{self.auto_feed_info}"
            # if self.trim_description:
            #     logger.info(f"种子描述：\n{self.description}")
            logger.trace(f"已生成自动上传链接：{link}")
            open_link(link, self.use_short_url)
        else:
            logger.info(
                "\n"
                f"标题: {self.title}\n"
                f"副标题: {self.subtitle}\n"
                f"豆瓣: {self.douban_url}\n"
                f"IMDB: {self.imdb_url}\n"
                f"视频编码: {self.video_codec} 音频编码: {self.audio_codec} 分辨率: {self.resolution}\n"
                f"描述:\n{self.description}"
            )

    def _prepare(self):
        self.main_file = self.mediainfo_handler.find_mediainfo()
        self.ptgen, self.douban, self.imdb = self.ptgen_handler.fetch_ptgen_info()
        self.screenshot_handler.collect_screenshots(
            self.main_file,
            self.mediainfo_handler.resolution,
            self.mediainfo_handler.duration,
        )

        if self.generate_nfo:
            generate_nfo(self.folder, self.mediainfo_handler.media_info)

        if self.make_torrent:
            make_torrent(
                self.folder,
                self.announce_url,
                self.__class__.__name__,
                self.reuse_torrent,
                self.from_torrent,
            )

    @property
    def parsed_encoder_log(self):
        return parse_encoder_log(self.encoder_log)

    @property
    def title(self):
        # TODO: Either use file name or generate from mediainfo and ptgen
        temp_name = (
            self.folder.name if self.folder.is_dir() else self.folder.stem
        ).replace(".", " ")
        temp_name = re.sub(r"(?<=5|7)( )1(?=.*$)", ".1", temp_name)
        return temp_name

    @property
    def subtitle(self):
        if not self.douban:
            return self.ptgen.subtitle
        return self.douban.subtitle

    @property
    def media_info(self):
        return self.mediainfo_handler.media_info

    @property
    def media_infos(self):
        return []

    @property
    def description(self):
        return "{}\n\n[quote]{}{}[/quote]\n\n{}".format(
            self.ptgen.format,
            self.media_info,
            "\n\n" + self.parsed_encoder_log if self.parsed_encoder_log else "",
            "\n".join(
                [f"{uploaded}" for uploaded in self.screenshot_handler.screenshots]
            ),
        )

    @property
    def original_description(self):
        return ""

    @property
    def douban_url(self):
        if self.douban:
            return f"https://movie.douban.com/subject/{self.douban.sid}"
        return ""

    @property
    def douban_info(self):
        return ""

    @property
    def imdb_url(self):
        return getattr(self.ptgen, "imdb_link", "")

    @property
    def screenshots(self):
        return [u.url for u in self.screenshot_handler.screenshots]

    @property
    def poster(self):
        return getattr(self.ptgen, "poster")

    @property
    def year(self):
        return (
            self.imdb.year
            if self.imdb
            else self.douban.year if self.douban else getattr(self.ptgen, "year", "")
        )

    @property
    def category(self):
        if self.douban:
            if "演唱会" in self.douban.genre and "音乐" in self.douban.genre:
                return "concert"
        if self.imdb:
            if "Documentary" in self.imdb.genre:
                return "documentary"
            if self.imdb.type_ == DataType.MOVIE:
                return "movie"
            if self.imdb.type_ == DataType.TV_SERIES:
                return "tvPack"
        return self.ptgen.type_

    @property
    def video_type(self):
        if "webdl" in self.folder.name.lower() or "web-dl" in self.folder.name.lower():
            return "web"
        elif "remux" in self.folder.name.lower():
            return "remux"
        elif "hdtv" in self.folder.name.lower():
            return "hdtv"
        elif any(e in self.folder.name.lower() for e in ("x264", "x265")):
            return "encode"
        elif "bluray" in self.folder.name.lower() and not any(
            e in self.folder.name.lower() for e in ("x264", "x265")
        ):
            return "bluray"
        elif "uhd" in self.folder.name.lower():
            return "uhdbluray"
        for track in self.mediainfo_handler.tracks:
            if track.track_type == "Video":
                if track.encoding_settings:
                    return "encode"
        return ""

    @property
    def format(self):
        # TODO: Maybe read from mediainfo
        return self.main_file.suffix

    @property
    def source(self):
        return ""

    @property
    def video_codec(self):
        for track in self.mediainfo_handler.mediainfo.tracks:
            if track.track_type == "Video":
                if track.encoded_library_name:
                    return track.encoded_library_name
                if track.commercial_name == "AVC":
                    return "h264"
                if track.commercial_name == "HEVC":
                    return "hevc"
        #  h264: "AVC/H.264",
        #  hevc: "HEVC",
        #  x264: "x264",
        #  x265: "x265",
        #  h265: "HEVC",
        #  mpeg2: "MPEG-2",
        #  mpeg4: "AVC/H.264",
        #  vc1: "VC-1",
        #  dvd: "MPEG"
        return ""

    @property
    def audio_codec(self):
        codec_map = {
            "AAC": "aac",
            "Dolby Digital Plus": "dd+",
            "Dolby Digital": "dd",
            "DTS-HD Master Audio": "dtshdma",
            "Dolby Digital Plus with Dolby Atmos": "atmos",
            "Dolby TrueHD": "truehd",
            "Dolby TrueHD with Dolby Atmos": "truehd",
        }
        for track in self.mediainfo_handler.mediainfo.tracks:
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
        for track in self.mediainfo_handler.mediainfo.tracks:
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
        if self.douban:
            return self.douban.area
        return ""

    @property
    def movie_name(self):
        if self.imdb:
            return self.imdb.name
        if self.douban:
            return next(iter(self.douban.aka), "")
        return ""

    @property
    def movie_aka_name(self):
        return ""

    @property
    def size(self):
        for track in self.mediainfo_handler.tracks:
            if track.track_type == "General":
                return track.file_size
        return ""

    @property
    def tags(self):
        tags = {}
        for track in self.mediainfo_handler.tracks:
            if track.track_type == "General":
                if track.audio_language_list and "Chinese" in track.audio_language_list:
                    tags["chinese_audio"] = True
                if track.text_language_list and "Chinese" in track.text_language_list:
                    tags["chinese_subtitle"] = True
        # TODO: hdr, hdr10_plus, dolby_vision, diy, cantonese_audio, false,dts_x, dolby_atoms
        return tags

    @property
    def other_tags(self):
        return []

    @property
    def comparisons(self):
        return []

    @property
    def easy_upload_torrent_info(self):
        return EasyUpload(plugin=self).torrent_info

    @property
    def auto_feed_info(self):
        return AutoFeed(plugin=self).info
