import os
import re
import sys
import json
import shutil
import tempfile
import argparse
from pathlib import Path
from decimal import Decimal
from typing import Optional
from abc import ABC, ABCMeta, abstractmethod

import requests
from PIL import Image
from torf import Torrent
from loguru import logger
from pymediainfo import MediaInfo

from differential.version import version
from differential.constants import ImageHosting
from differential.utils.torrent import make_torrent
from differential.utils.binary import ffprobe, execute
from differential.utils.mediainfo import get_track_attr
from differential.utils.mediainfo import get_full_mediainfo
from differential.utils.image import ptpimg_upload, smms_upload, imgurl_upload, chevereto_api_upload, chevereto_cookie_upload


PARSER = argparse.ArgumentParser(description="Differential - 差速器 PT快速上传工具")
PARSER.add_argument('-v', '--version', help="显示差速器当前版本", action='version', version=f"Differential {version}")
subparsers = PARSER.add_subparsers(help="使用下列插件名字来查看插件的详细用法")
REGISTERED_PLUGINS = {}


class PluginRegister(ABCMeta):

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        # Skip base class
        if name != 'Base' and name not in REGISTERED_PLUGINS:
            aliases = (name.lower(),)
            if 'get_aliases' in cls.__dict__:
                aliases += cls.get_aliases()
            subparser = subparsers.add_parser(name, aliases=aliases, help=cls.get_help())
            subparser.set_defaults(plugin=name)
            cls.add_parser(subparser)
            for n in aliases:
                REGISTERED_PLUGINS[n] = cls
            REGISTERED_PLUGINS[name] = cls

    @classmethod
    @abstractmethod
    def get_help(mcs):
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def get_aliases(mcs):
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def add_parser(mcs, parser: argparse.ArgumentParser):
        raise NotImplementedError()


class Base(ABC, metaclass=PluginRegister):

    @classmethod
    @abstractmethod
    def add_parser(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument('-c', '--config', type=str, help='配置文件的路径，默认为config.ini', default='config.ini')
        parser.add_argument('-l', '--log', type=str, help='log文件的路径', default=argparse.SUPPRESS)
        parser.add_argument('-f', '--folder', type=str, help='种子文件夹的路径', default=argparse.SUPPRESS)
        parser.add_argument('-u', '--url', type=str, help='豆瓣链接', default=argparse.SUPPRESS)
        parser.add_argument('-t', '--make-torrent', action="store_true", help="是否制种，默认否", default=argparse.SUPPRESS)
        parser.add_argument('-n', '--generate-nfo', action="store_true", help="是否用MediaInfo生成NFO文件，默认否",
                            default=argparse.SUPPRESS)
        parser.add_argument('-s', '--screenshot-count', type=int, help="截图数量，默认为0，即不生成截图", default=argparse.SUPPRESS)
        parser.add_argument('--optimize-screenshot', action="store_true", help="是否压缩截图（无损），默认压缩",
                            default=argparse.SUPPRESS)
        parser.add_argument('--image-hosting', type=ImageHosting,
                            help=f"图床的类型，现在支持{','.join(i.value for i in ImageHosting)}", default=argparse.SUPPRESS)
        parser.add_argument('--imgurl-hosting-url', type=str, help="自建imgurl图床的地址", default=argparse.SUPPRESS)
        parser.add_argument('--chevereto-hosting-url', type=str, help="自建chevereto图床的地址", default=argparse.SUPPRESS)
        parser.add_argument('--ptpimg-api-key', type=str, help="PTPIMG的API Key", default=argparse.SUPPRESS)
        parser.add_argument('--chevereto-api-key', type=str, help="自建Chevereto的API Key，详情见https://v3-docs.chevereto.com/api/#api-call", default=argparse.SUPPRESS)
        parser.add_argument('--chevereto-cookie', type=str, help="如果自建Chevereto的API未开放，请设置auth token和cookie", default=argparse.SUPPRESS)
        parser.add_argument('--chevereto-auth-token', type=str, help="如果自建Chevereto的API未开放，请设置auth token和cookie", default=argparse.SUPPRESS)
        parser.add_argument('--imgurl-api-key', type=str, help="Imgurl的API Key", default=argparse.SUPPRESS)
        parser.add_argument('--smms-api-key', type=str, help="SM.MS的API Key", default=argparse.SUPPRESS)
        parser.add_argument('--ptgen-url', type=str, help="自定义PTGEN的地址", default=argparse.SUPPRESS)
        parser.add_argument('--ptgen-retry', type=int, help="PTGEN重试次数，默认为3次", default=argparse.SUPPRESS)
        parser.add_argument('--announce-url', type=str, help="制种时announce地址", default=argparse.SUPPRESS)
        return parser

    def __init__(
        self,
        folder: str,
        url: str,
        screenshot_count: int = 0,
        optimize_screenshot: bool = True,
        image_hosting: ImageHosting = ImageHosting.PTPIMG,
        chevereto_hosting_url: str = '',
        imgurl_hosting_url: str = '',
        ptpimg_api_key: str = None,
        chevereto_api_key: str = None,
        chevereto_cookie: str = None,
        chevereto_auth_token: str = None,
        imgurl_api_key: str = None,
        smms_api_key: str = None,
        ptgen_url: str = "https://ptgen.lgto.workers.dev",
        announce_url: str = 'https://example.com',
        ptgen_retry: int = 3,
        generate_nfo: bool = False,
        make_torrent: bool = False,
        **kwargs,
    ):
        self.folder = Path(folder)
        self.url = url
        self.screenshot_count = screenshot_count
        self.optimize_screenshot = optimize_screenshot
        self.image_hosting = image_hosting
        self.chevereto_hosting_url = chevereto_hosting_url
        self.imgurl_hosting_url = imgurl_hosting_url
        self.ptpimg_api_key = ptpimg_api_key
        self.chevereto_cookie = chevereto_cookie
        self.chevereto_auth_token = chevereto_auth_token
        self.chevereto_api_key = chevereto_api_key
        self.imgurl_api_key = imgurl_api_key
        self.smms_api_key = smms_api_key
        self.ptgen_url = ptgen_url
        self.announce_url = announce_url
        self.ptgen_retry = ptgen_retry
        self.generate_nfo = generate_nfo
        self.make_torrent = make_torrent

        self._main_file: Optional[Path] = None
        self._ptgen: dict = {}
        self._imdb: dict = {}
        self._mediainfo: Optional[MediaInfo] = None
        self._screenshots: list = []


    def upload_screenshots(self, img_dir: str) -> list:
        img_urls = []
        for count, img in enumerate(sorted(Path(img_dir).glob("*.png"))):
            if img.is_file() and img.name.lower().endswith('png'):
                img_url = None
                img_url_file = img.resolve().parent.joinpath(".{}.{}".format(self.image_hosting.value, img.stem))
                if img_url_file.is_file():
                    with open(img_url_file, 'r') as f:
                        img_url = f.read().strip()
                        logger.info(f"发现已上传的第{count + 1}张截图链接：{img_url}")
                else:
                    if self.image_hosting == ImageHosting.PTPIMG:
                        img_url = ptpimg_api_upload(img, self.ptpimg_api_key)
                    elif self.image_hosting == ImageHosting.CHEVERETO:
                        if not self.chevereto_hosting_url:
                            logger.error("Chevereto地址未提供，请设置chevereto_hosting_url")
                            sys.exit(1)
                        if self.chevereto_api_key:
                            img_url = chevereto_api_upload(img, self.chevereto_hosting_url, self.chevereto_api_key)
                        elif self.chevereto_cookie and self.chevereto_auth_token:
                            img_url = chevereto_cookie_upload(img, self.chevereto_hosting_url, self.chevereto_cookie, self.chevereto_auth_token)
                        else:
                            logger.error("Chevereto的API Key/Cookie均未设置，请检查chevereto-api-key/chevereto-cookie+chevereto-auth-token设置")
                    elif self.image_hosting == ImageHosting.IMGURL:
                        img_url = imgurl_upload(img, self.imgurl_hosting_url, self.imgurl_api_key)
                    elif self.image_hosting == ImageHosting.SMMS:
                        img_url = smms_upload(img, self.smms_api_key)

                if img_url:
                    logger.info(f"第{count + 1}张截图地址：{img_url}")
                    with open(img_url_file, 'w') as f:
                        f.write(img_url)
                    img_urls.append(img_url)
                else:
                    logger.info(f"第{count + 1}张截图上传失败，请自行上传：{img.resolve()}")
        return img_urls

    def _get_ptgen(self) -> dict:
        self._imdb = {}
        ptgen_failed = {"format": "PTGen获取失败，请自行获取相关信息", "failed": True}
        logger.info(f"正在获取PTGen: {self.url}")
        params = {"url": self.url}
        req = requests.get(self.ptgen_url, params)
        if not req.ok:
            logger.trace(req.content)
            logger.warning(f"获取PTGen失败: HTTP f{req.status_code}, reason: {req.reason}")
            return ptgen_failed
        if not req.json().get("success", False):
            logger.trace(req.json())
            logger.warning(f"获取PTGen失败: {req.json().get('error', 'Unknown error')}")
            return ptgen_failed

        # 尝试获取IMDB描述
        if req.json().get('site') != 'imdb':
            if req.json().get('imdb_link'):
                imdb_params = {'url': req.json().get('imdb_link')}
                imdb_req = requests.get(self.ptgen_url, imdb_params)
                if imdb_req.ok and imdb_req.json().get('success'):
                    self._imdb = imdb_req.json()
        else:
            self._imdb = req.json()
        logger.info(f"获取PTGen成功 {req.json().get('chinese_title', '')}")
        return req.json()

    def _get_mediainfo(self) -> MediaInfo:
        # Always find the biggest file in the folder
        logger.info(f"正在获取Mediainfo: {self.folder}")
        if self.folder.is_file():
            self._main_file = self.folder
        else:
            logger.info("目标为文件夹，正在获取最大的文件...")
            biggest_size = -1
            biggest_file = None
            for f in self.folder.glob('**/*'):
                if f.is_file():
                    s = os.stat(f.absolute()).st_size
                    if s > biggest_size:
                        biggest_size = s
                        biggest_file = f
            if biggest_file:
                self._main_file = biggest_file
        if self._main_file is None:
            logger.error("未在目标目录找到文件！")
            sys.exit(1)
        mediainfo = MediaInfo.parse(self._main_file)
        logger.info(f"已获取Mediainfo: {self._main_file}")
        logger.trace(mediainfo.to_data())
        return mediainfo

    def _generate_nfo(self):
        logger.info("正在生成nfo文件...")
        if self.folder.is_file():
            with open(f"{self.folder.resolve().parent.joinpath(self.folder.stem)}.nfo", 'wb') as f:
                f.write(self.mediaInfo.encode())
        elif self.folder.is_dir():
            with open(self.folder.joinpath(f"{self.folder.name}.nfo"), 'wb') as f:
                f.write(self.mediaInfo.encode())

    def _get_screenshots(self) -> list:
        if self._main_file is None:
            logger.error("未找到可以被截图的资源，请确认目标目录含有支持的资源!")
            return []

        # 利用ffprobe获取视频基本信息
        ffprobe_out = ffprobe(self._main_file)
        m = re.search(r"Stream.*?Video.*?(\d{2,5})x(\d{2,5})", ffprobe_out)
        if not m:
            logger.debug(ffprobe_out)
            logger.warning(f"无法获取到视频的分辨率")
            return []

        # 获取视频分辨率以及长度等信息
        width, height = int(m.group(1)), int(m.group(2))
        for track in self._mediainfo.tracks:
            if track.track_type == "Video":
                duration = Decimal(track.duration)
                pixel_aspect_ratio = Decimal(track.pixel_aspect_ratio)
                break
        else:
            logger.error(f"未找到视频Track，请检查{self._main_file}是否为支持的文件")
            return []

        if pixel_aspect_ratio <= 1:
            pheight = int(height * pixel_aspect_ratio) + (
                int(height * pixel_aspect_ratio) % 2
            )
            resolution = f"{width}x{pheight}"
        else:
            pwidth = int(width * pixel_aspect_ratio) + (
                int(width * pixel_aspect_ratio) % 2
            )
            resolution = f"{pwidth}x{height}"
        logger.trace(
            f"duration: {duration}, "
            f"width: {width} height: {height}, "
            f"PAR: {pixel_aspect_ratio}, resolution: {resolution}"
        )

        temp_dir = None
        # 查找已有的截图
        for f in Path(tempfile.gettempdir()).glob("Differential*"):
            if f.is_dir() and self.folder.name in f.name:
                if len(list(f.glob("*.png"))) == self.screenshot_count:
                    temp_dir = f.absolute()
                    logger.info("发现已生成的{}张截图，跳过截图...".format(self.screenshot_count))
                    break
        else:
            temp_dir = tempfile.mkdtemp(prefix="Differential.{}.".format(version), suffix=self.folder.name)
            # 生成截图
            for i in range(1, self.screenshot_count + 1):
                logger.info(f"正在生成第{i}张截图...")
                t = int(i * duration / (self.screenshot_count + 1))
                screenshot_path = f'{temp_dir}/{self._main_file.stem}.thumb_{str(i).zfill(2)}.png'
                execute("ffmpeg", (
                    f'-y -ss {t}ms -skip_frame nokey -i "{self._main_file.absolute()}" '
                    f'-s {resolution} -vsync 0 -vframes 1 -c:v png -v quiet "{screenshot_path}"'))
                if self.optimize_screenshot:
                    image = Image.open(screenshot_path)
                    image.save(f"{screenshot_path}", format="PNG", optimized=True)

        # 上传截图
        screenshots = self.upload_screenshots(temp_dir)
        logger.trace(f"Collected screenshots: {screenshots}")

        # 删除临时文件夹
        # shutil.rmtree(temp_dir, ignore_errors=True)

        return screenshots

    def _prepare(self):
        ptgen_retry = self.ptgen_retry
        self._ptgen = self._get_ptgen()
        while self._ptgen.get('failed') and ptgen_retry > 0:
            self._ptgen = self._get_ptgen()
            ptgen_retry -= 1
        self._mediainfo = self._get_mediainfo()
        if self.generate_nfo:
            self._generate_nfo()
        self._screenshots = self._get_screenshots()
        if self.make_torrent:
            make_torrent(self.folder, [self.announce_url])

    @property
    def title(self):
        # TODO: Either use file name or generate from mediainfo and ptgen
        temp_name = (self.folder.name if self.folder.is_dir() else self.folder.stem).replace('.', ' ')
        temp_name = temp_name.replace('5 1 ', '5.1 ')
        temp_name = temp_name.replace('7 1 ', '7.1 ')
        return temp_name

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
        return get_full_mediainfo(self._mediainfo)

    @property
    def mediaInfos(self):
        return []

    @property
    def description(self):
        return "{}\n\n[quote]{}{}[/quote]\n\n{}".format(
            self._ptgen.get("format"),
            self.mediaInfo,
            "\n\n" + self.parsed_encoder_log if self.parsed_encoder_log else "",
            "\n".join([f"[img]{url}[/img]" for url in self._screenshots]),
        )

    @property
    def originalDescription(self):
        return ''

    @property
    def doubanUrl(self):
        if self._ptgen.get("site") == "douban":
            return f"https://movie.douban.com/subject/{self._ptgen.get('sid')}"
        return ""

    @property
    def doubanInfo(self):
        return ''

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
                    return "h264"
                if track.commercial_name == 'HEVC':
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
    def otherTags(self):
        return []

    @property
    def comparisons(self):
        return []

    @property
    def torrentInfo(self):
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "originalDescription": self.originalDescription,
            "doubanUrl": self.doubanUrl,
            "doubanInfo": self.doubanInfo,
            "imdbUrl": self.imdbUrl,
            "mediaInfo": self.mediaInfo,
            "mediaInfos": self.mediaInfos,
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
            "otherTags": self.otherTags,
            "comparisons": self.comparisons,
            "isForbidden": False,
            "sourceSiteType": "NexusPHP",
        }

    @abstractmethod
    def upload(self):
        raise NotImplementedError()
