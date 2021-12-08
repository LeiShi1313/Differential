import os
import re
import sys
import json
import shutil
import platform
import tempfile
import argparse
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from abc import ABC, ABCMeta, abstractmethod

import requests
from PIL import Image
from loguru import logger
from pymediainfo import MediaInfo

from differential import tools
from differential.torrent import TorrnetBase
from differential.version import version
from differential.constants import ImageHosting
from differential.utils.browser import open_link
from differential.utils.torrent import make_torrent
from differential.utils.parse import parse_encoder_log
from differential.utils.uploader import EasyUpload, AutoFeed
from differential.utils.binary import ffprobe, execute, execute_with_output
from differential.utils.mediainfo import (
    get_full_mediainfo,
    get_resolution,
    get_duration,
)
from differential.utils.image import (
    byr_upload,
    ptpimg_upload,
    smms_upload,
    imgurl_upload,
    chevereto_api_upload,
    chevereto_username_upload,
)


PARSER = argparse.ArgumentParser(description="Differential - 差速器 PT快速上传工具")
PARSER.add_argument(
    "-v",
    "--version",
    help="显示差速器当前版本",
    action="version",
    version=f"Differential {version}",
)
subparsers = PARSER.add_subparsers(help="使用下列插件名字来查看插件的详细用法")
REGISTERED_PLUGINS = {}


class PluginRegister(ABCMeta):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        # Skip base class
        if name != "Base" and name not in REGISTERED_PLUGINS:
            aliases = (name.lower(),)
            if "get_aliases" in cls.__dict__:
                aliases += cls.get_aliases()
            subparser = subparsers.add_parser(
                name, aliases=aliases, help=cls.get_help()
            )
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
            "-f", "--folder", type=str, help="种子文件夹的路径", default=argparse.SUPPRESS
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
            "--use-short-bdinfo",
            action="store_true",
            help="使用QUICK SUMMARY作为BDInfo，默认使用完整BDInfo",
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
            "--byr-authorization",
            type=str,
            help="BYR的Authorization头，可登录后访问任意页面F12查看，形如Basic xxxxxxxxxxxxxxxx==",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--byr-alternative-url",
            type=str,
            help="BYR反代地址(如有)，可为空",
            default=argparse.SUPPRESS,
        )
        parser.add_argument(
            "--ptgen-url", type=str, help="自定义PTGEN的地址", default=argparse.SUPPRESS
        )
        parser.add_argument(
            "--ptgen-retry", type=int, help="PTGEN重试次数，默认为3次", default=argparse.SUPPRESS
        )
        parser.add_argument(
            "--announce-url", type=str, help="制种时announce地址", default=argparse.SUPPRESS
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
        return parser

    def __init__(
        self,
        folder: str,
        url: str,
        upload_url: str,
        screenshot_count: int = 0,
        optimize_screenshot: bool = True,
        use_short_bdinfo: bool = False,
        image_hosting: ImageHosting = ImageHosting.PTPIMG,
        chevereto_hosting_url: str = "",
        imgurl_hosting_url: str = "",
        ptpimg_api_key: str = None,
        chevereto_api_key: str = None,
        chevereto_username: str = None,
        chevereto_password: str = None,
        imgurl_api_key: str = None,
        smms_api_key: str = None,
        byr_authorization: str = None,
        byr_alternative_url: str = None,
        ptgen_url: str = "https://ptgen.lgto.workers.dev",
        announce_url: str = "https://example.com",
        ptgen_retry: int = 3,
        generate_nfo: bool = False,
        make_torrent: bool = False,
        easy_upload: bool = False,
        auto_feed: bool = False,
        trim_description: bool = False,
        use_short_url: bool = False,
        encoder_log: str = "",
        **kwargs,
    ):
        self.folder = Path(folder)
        self.url = url
        self.upload_url = upload_url
        self.screenshot_count = screenshot_count
        self.optimize_screenshot = optimize_screenshot
        self.use_short_bdinfo = use_short_bdinfo
        self.image_hosting = image_hosting
        self.chevereto_hosting_url = chevereto_hosting_url
        self.imgurl_hosting_url = imgurl_hosting_url
        self.ptpimg_api_key = ptpimg_api_key
        self.chevereto_username = chevereto_username
        self.chevereto_password = chevereto_password
        self.chevereto_api_key = chevereto_api_key
        self.imgurl_api_key = imgurl_api_key
        self.smms_api_key = smms_api_key
        self.byr_authorization = byr_authorization
        self.byr_alternative_url = byr_alternative_url
        self.ptgen_url = ptgen_url
        self.announce_url = announce_url
        self.ptgen_retry = ptgen_retry
        self.generate_nfo = generate_nfo
        self.make_torrent = make_torrent
        self.easy_upload = easy_upload
        self.auto_feed = auto_feed
        self.trim_description = trim_description
        self.use_short_url = use_short_url
        self.encoder_log = encoder_log

        self.is_bdmv = False
        self._bdinfo = None
        self._main_file: Optional[Path] = None
        self._ptgen: dict = {}
        self._imdb: dict = {}
        self._mediainfo: Optional[MediaInfo] = None
        self._screenshots: list = []

    def upload_screenshots(self, img_dir: str) -> list:
        img_urls = []
        for count, img in enumerate(sorted(Path(img_dir).glob("*.png"))):
            if img.is_file():
                img_url = None
                img_url_file = img.resolve().parent.joinpath(
                    ".{}.{}".format(self.image_hosting.value, img.stem)
                )
                if img_url_file.is_file():
                    with open(img_url_file, "r") as f:
                        img_url = f.read().strip()
                        logger.info(f"发现已上传的第{count + 1}张截图链接：{img_url}")
                else:
                    if self.image_hosting == ImageHosting.PTPIMG:
                        img_url = ptpimg_upload(img, self.ptpimg_api_key)
                    elif self.image_hosting == ImageHosting.CHEVERETO:
                        if not self.chevereto_hosting_url:
                            logger.error("Chevereto地址未提供，请设置chevereto_hosting_url")
                            sys.exit(1)
                        if self.chevereto_api_key:
                            img_url = chevereto_api_upload(
                                img, self.chevereto_hosting_url, self.chevereto_api_key
                            )
                        elif self.chevereto_username and self.chevereto_password:
                            img_url = chevereto_username_upload(
                                img,
                                self.chevereto_hosting_url,
                                self.chevereto_username,
                                self.chevereto_password,
                            )
                        else:
                            logger.error(
                                "Chevereto的API或用户名或密码未设置，请检查chevereto-username/chevereto-password设置"
                            )
                    elif self.image_hosting == ImageHosting.IMGURL:
                        img_url = imgurl_upload(
                            img, self.imgurl_hosting_url, self.imgurl_api_key
                        )
                    elif self.image_hosting == ImageHosting.SMMS:
                        img_url = smms_upload(img, self.smms_api_key)
                    elif self.image_hosting == ImageHosting.BYR:
                        img_url = byr_upload(
                            img, self.byr_authorization, self.byr_alternative_url
                        )

                if img_url:
                    logger.info(f"第{count + 1}张截图地址：{img_url}")
                    with open(img_url_file, "w") as f:
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
        if req.json().get("site") != "imdb":
            if req.json().get("imdb_link"):
                imdb_params = {"url": req.json().get("imdb_link")}
                imdb_req = requests.get(self.ptgen_url, imdb_params)
                if imdb_req.ok and imdb_req.json().get("success"):
                    self._imdb = imdb_req.json()
        else:
            self._imdb = req.json()
        logger.info(f"获取PTGen成功 {req.json().get('chinese_title', '')}")
        return req.json()

    def _get_bdinfo(self) -> str:
        logger.info("目标为BDMV，正在扫描BDInfo...")
        temp_dir = tempfile.mkdtemp()
        bdinfos = []
        for f in self.folder.glob("**/BDMV"):
            logger.info(f"正在扫描{f.parent}...")
            if platform.system() == "Windows":
                execute_with_output(
                    os.path.join(
                        os.path.dirname(tools.__file__), "BDinfoCli.0.7.3\BDInfo.exe"
                    ),
                    f'-w "{f.parent}" {temp_dir}',
                    abort=True,
                )
            else:
                execute_with_output(
                    "mono",
                    f""""{os.path.join(os.path.dirname(tools.__file__), 'BDinfoCli.0.7.3/BDInfo.exe')}" -w """
                    f'"{f.parent}" {temp_dir}',
                    abort=True,
                )
        for info in Path(temp_dir).glob("*.txt"):
            with info.open("r") as f:
                content = f.read()
            if self.use_short_bdinfo:
                m = re.search(r"(QUICK SUMMARY:\n+(.+?\n)+)\n\n", content)
                if m:
                    bdinfos.append(m.groups()[0])
            else:
                m = re.search(
                    r"(DISC INFO:\n+(.+?\n{1,2})+?)(?:CHAPTERS:\n|STREAM DIAGNOSTICS:\n|\[\/code\]\n<---- END FORUMS PASTE ---->)",
                    content,
                )
                if m:
                    bdinfos.append(m.groups()[0])
        shutil.rmtree(temp_dir, ignore_errors=True)
        return "\n\n".join(bdinfos)

    def _find_mediainfo(self) -> MediaInfo:
        # Always find the biggest file in the folder
        logger.info(f"正在获取Mediainfo: {self.folder}")
        if self.folder.is_file():
            self._main_file = self.folder
        else:
            logger.info("目标为文件夹，正在获取最大的文件...")
            biggest_size = -1
            biggest_file = None
            has_bdmv = False
            for f in self.folder.glob("**/*"):
                if f.is_file():
                    if f.suffix == ".bdmv":
                        has_bdmv = True
                    s = os.stat(f.absolute()).st_size
                    if s > biggest_size:
                        biggest_size = s
                        biggest_file = f
            if biggest_file:
                self._main_file = biggest_file
        if self._main_file is None:
            logger.error("未在目标目录找到文件！")
            sys.exit(1)
        elif self._main_file.suffix == '.iso':
            logger.error("请将iso文件挂载后再使用差速器")
            sys.exit(1)
        mediainfo = MediaInfo.parse(self._main_file)
        logger.info(f"已获取Mediainfo: {self._main_file}")
        logger.trace(mediainfo.to_data())
        if has_bdmv:
            self.is_bdmv = True
            self._bdinfo = self._get_bdinfo()
        return mediainfo

    def _generate_nfo(self):
        logger.info("正在生成nfo文件...")
        if self.folder.is_file():
            with open(
                f"{self.folder.resolve().parent.joinpath(self.folder.stem)}.nfo", "wb"
            ) as f:
                f.write(self.media_info.encode())
        elif self.folder.is_dir():
            with open(self.folder.joinpath(f"{self.folder.name}.nfo"), "wb") as f:
                f.write(self.media_info.encode())

    def _make_screenshots(self) -> Optional[str]:
        resolution = get_resolution(self._main_file, self._mediainfo)
        duration = get_duration(self._mediainfo)
        if resolution is None or duration is None:
            return None

        temp_dir = None
        # 查找已有的截图
        for f in Path(tempfile.gettempdir()).glob("Differential*"):
            if f.is_dir() and self.folder.name in f.name:
                if (
                    self.screenshot_count > 0
                    and len(list(f.glob("*.png"))) == self.screenshot_count
                ):
                    temp_dir = f.absolute()
                    logger.info("发现已生成的{}张截图，跳过截图...".format(self.screenshot_count))
                    break
        else:
            temp_dir = tempfile.mkdtemp(
                prefix="Differential.{}.".format(version), suffix=self.folder.name
            )
            # 生成截图
            for i in range(1, self.screenshot_count + 1):
                logger.info(f"正在生成第{i}张截图...")
                t = int(i * duration / (self.screenshot_count + 1))
                screenshot_path = (
                    f"{temp_dir}/{self._main_file.stem}.thumb_{str(i).zfill(2)}.png"
                )
                execute(
                    "ffmpeg",
                    (
                        f'-y -ss {t}ms -skip_frame nokey -i "{self._main_file.absolute()}" '
                        f'-s {resolution} -vsync 0 -vframes 1 -c:v png "{screenshot_path}"'
                    ),
                )
                if self.optimize_screenshot:
                    image = Image.open(screenshot_path)
                    image.save(f"{screenshot_path}", format="PNG", optimized=True)
        return temp_dir

    def _get_screenshots(self) -> list:
        if self._main_file is None:
            logger.error("未找到可以被截图的资源，请确认目标目录含有支持的资源!")
            return []

        temp_dir = self._make_screenshots()
        if temp_dir is None:
            return []

        # 上传截图
        screenshots = self.upload_screenshots(temp_dir)
        logger.trace(f"Collected screenshots: {screenshots}")

        # 删除临时文件夹
        # shutil.rmtree(temp_dir, ignore_errors=True)

        return screenshots

    def _prepare(self):
        ptgen_retry = self.ptgen_retry
        self._ptgen = self._get_ptgen()
        while self._ptgen.get("failed") and ptgen_retry > 0:
            self._ptgen = self._get_ptgen()
            ptgen_retry -= 1
        self._mediainfo = self._find_mediainfo()
        if self.generate_nfo:
            self._generate_nfo()
        self._screenshots = self._get_screenshots()
        if self.make_torrent:
            make_torrent(self.folder, [self.announce_url])

    @property
    def parsed_encoder_log(self):
        return parse_encoder_log(self.encoder_log)

    @property
    def title(self):
        # TODO: Either use file name or generate from mediainfo and ptgen
        temp_name = (
            self.folder.name if self.folder.is_dir() else self.folder.stem
        ).replace(".", " ")
        temp_name = re.sub(r'(?<=5|7)( )1(?=.*$)', '.1', temp_name)
        return temp_name

    @property
    def subtitle(self):
        if not self._ptgen.get("site") == "douban":
            return ""
        if "chinese_title" in self._ptgen:
            subtitle = f"{'/'.join([self._ptgen.get('chinese_title')] + self._ptgen.get('aka', []))}"
        else:
            subtitle = f"{'/'.join(self._ptgen.get('aka', []))}"
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
    def media_info(self):
        if self.is_bdmv:
            return self._bdinfo
        else:
            return get_full_mediainfo(self._mediainfo)

    @property
    def media_infos(self):
        return []

    @property
    def description(self):
        return "{}\n\n[quote]{}{}[/quote]\n\n{}".format(
            self._ptgen.get("format"),
            self.media_info,
            "\n\n" + self.parsed_encoder_log if self.parsed_encoder_log else "",
            "\n".join([f"[img]{url}[/img]" for url in self._screenshots]),
        )

    @property
    def original_description(self):
        return ""

    @property
    def douban_url(self):
        if self._ptgen.get("site") == "douban":
            return f"https://movie.douban.com/subject/{self._ptgen.get('sid')}"
        return ""

    @property
    def douban_info(self):
        return ""

    @property
    def imdb_url(self):
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
    def video_codec(self):
        for track in self._mediainfo.tracks:
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
            "印度": "IN",
            "法国": "FR",
            "意大利": "IT",
            "德国": "GE",
            "西班牙": "ES",
            "葡萄牙": "PT",
        }
        regions = self._ptgen.get("region", [])
        for area in area_map.keys():
            if area in regions:
                return area_map[area]
        return ""

    @property
    def movie_name(self):
        if self._ptgen.get("site") == "imdb":
            return self._ptgen.get("name", "")
        if self._ptgen.get("site") == "douban":
            return self._ptgen.get("aka", [""])[0]
        return ""

    @property
    def movie_aka_name(self):
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
            link = f"{self.upload_url}{quote(self.auto_feed_info, safe='#:/=@')}"
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
