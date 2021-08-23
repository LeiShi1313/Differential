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

from differential.constants import ImageHosting
from differential.utils import ffprobe, execute, make_torrent_progress, get_track_attr

PARSER = argparse.ArgumentParser(description="Differential - 差速器 PT快速上传工具")
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
        parser.add_argument('--image-hosting-url', type=str, help="图床地址，非自建的图床可不填", default=argparse.SUPPRESS)
        parser.add_argument('--ptpimg-api-key', type=str, help="PTPIMG的API Key", default=argparse.SUPPRESS)
        parser.add_argument('--chevereto-api-key', type=str, help="自建Chevereto的API Key", default=argparse.SUPPRESS)
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
        image_hosting_url: str = "",
        ptpimg_api_key: str = None,
        chevereto_api_key: str = None,
        imgurl_api_key: str = None,
        smms_api_key: str = None,
        ptgen_url: str = "https://ptgen.lgto.workers.dev",
        announce_url: str = 'https://example.com',
        ptgen_retry: int = 3,
        generate_nfo: bool = False,
        make_torrent: bool = False,
        **kwargs,
    ):
        self.folder = folder
        self.url = url
        self.screenshot_count = screenshot_count
        self.optimize_screenshot = optimize_screenshot
        self.image_hosting = image_hosting
        self.image_hosting_url = image_hosting_url
        self.ptpimg_api_key = ptpimg_api_key
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

    def ptpimg_upload(self, img: Path) -> Optional[str]:
        data = {'api_key': self.ptpimg_api_key}
        files = {'file-upload[0]': open(img, 'rb')}
        req = requests.post('https://ptpimg.me/upload.php', data=data, files=files)

        try:
            res = req.json()
            logger.trace(res)
        except json.decoder.JSONDecodeError:
            res = {}
        if not req.ok:
            logger.trace(req.content)
            logger.warning(
                f"上传图片失败: HTTP {req.status_code}, reason: {req.reason}")
            return None
        if len(res) < 1 or 'code' not in res[0] or 'ext' not in res[0]:
            logger.warning(f"图片直链获取失败")
            return None
        return f"https://ptpimg.me/{res[0].get('code')}.{res[0].get('ext')}"

    def chevereto_upload(self, img: Path) -> Optional[str]:
        data = {'key': self.chevereto_api_key}
        files = {'source': open(img, 'rb')}
        req = requests.post(f'{self.image_hosting_url}/api/1/upload', data=data, files=files)

        try:
            res = req.json()
            logger.trace(res)
        except json.decoder.JSONDecodeError:
            res = {}
        if not req.ok:
            logger.trace(req.content)
            logger.warning(
                f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
                f"{res['error'].get('message') if 'error' in res else ''}")
            return None
        if 'error' in res:
            logger.warning(f"上传图片失败: [{res['error'].get('code')}]{res['error'].get('message')}")
            return None
        if 'image' not in res or 'url' not in res['image']:
            logger.warning(f"图片直链获取失败")
            return None
        return res['image']['url']

    def imgurl_upload(self, img: Path) -> Optional[str]:
        data = {'token': self.imgurl_api_key}
        files = {'file': open(img, 'rb')}
        req = requests.post(f'{self.image_hosting_url}/api/upload', data=data, files=files)

        try:
            res = req.json()
            logger.trace(res)
        except json.decoder.JSONDecodeError:
            res = {}
        if not req.ok:
            logger.trace(req.content)
            logger.warning(
                f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
                f"{res.get('msg') if 'msg' in res else ''}")
            return None
        if res.get('code') > 200:
            logger.warning(f"上传图片失败: [{res.get('code')}]{res.get('msg')}")
            return None
        return res.get('url')

    def smms_upload(self, img: Path) -> Optional[str]:
        data = {'Authorization': self.smms_api_key}
        files = {'smfile': open(img, 'rb'), 'format': 'json'}
        req = requests.post('https://sm.ms/api/v2/upload', data=data, files=files)

        try:
            res = req.json()
            logger.trace(res)
        except json.decoder.JSONDecodeError:
            res = {}
        if not req.ok:
            logger.trace(req.content)
            logger.warning(
                f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
                f"{res.get('msg') if 'msg' in res else ''}")
            return None
        if not res.get('success') and res.get('code') != 'image_repeated':
            logger.warning(f"上传图片失败: [{res.get('code')}]{res.get('message')}")
            return None
        if res.get('code') == 'image_repeated':
            return res.get('images')
        if 'data' not in res or 'url' not in res['data']:
            logger.warning(f"图片直链获取失败")
            return None
        return res['data']['url']

    def upload_screenshots(self, img_dir: str) -> list:
        img_urls = []
        for count, img in enumerate(sorted(Path(img_dir).iterdir())):
            if img.is_file() and img.name.lower().endswith('png'):
                logger.info(f"正在上传第{count + 1}张截图...")
                upload_func = None
                if self.image_hosting == ImageHosting.PTPIMG:
                    upload_func = self.ptpimg_upload
                elif self.image_hosting == ImageHosting.CHEVERETO:
                    upload_func = self.chevereto_upload
                elif self.image_hosting == ImageHosting.IMGURL:
                    upload_func = self.imgurl_upload
                elif self.image_hosting == ImageHosting.SMMS:
                    upload_func = self.smms_upload

                if upload_func:
                    img_url = upload_func(img)
                    if img_url:
                        img_urls.append(img_url)
                else:
                    logger.warning(f'Image hosting: {self.image_hosting} not supported!')
                    break
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
        if os.path.isfile(self.folder):
            self._main_file = Path(self.folder)
        else:
            logger.info("目标为文件夹，正在获取最大的文件...")
            biggest_size = -1
            biggest_file = None
            for root, _, files in os.walk(self.folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    s = os.stat(full_path).st_size
                    if s > biggest_size:
                        biggest_size = s
                        biggest_file = full_path
            if biggest_file:
                self._main_file = Path(biggest_file)
        if self._main_file is None:
            logger.error("未在目标目录找到文件！")
            sys.exit(1)
        mediainfo = MediaInfo.parse(self._main_file)
        logger.info(f"已获取Mediainfo: {self._main_file}")
        logger.trace(mediainfo.to_data())
        return mediainfo

    def _get_full_mediainfo(self) -> str:
        track_format = {
            'general': ['Unique ID', 'Complete name', 'Format', 'Format version', 'Duration', 'Overall bit rate',
                        'Encoded date', 'Writing application', 'Writing library'],
            'video': ['ID', 'Format', 'Format/Info', 'Format profile', 'Codec ID', 'Duration', 'Bit rate', 'Width',
                      'Height', 'Display aspect ratio', 'Frame rate mode', 'Frame rate', 'Color space',
                      'Chroma subsampling', 'Bit depth', 'Bits/(Pixel*Frame)', 'Stream size', 'Writing library',
                      'Encoding settings', 'Default', 'Forced', 'Color range', 'Color primaries',
                      'Transfer characteristics', 'Matrix coefficients'],
            'audio': ['ID', 'Format', 'Format/Info', 'Commercial name', 'Codec ID', 'Duration', 'Bit rate mode',
                      'Bit rate', 'Channel(s)', 'Channel layout', 'Sampling rate', 'Frame rate', 'Compression mode',
                      'Stream size', 'Title', 'Language', 'Service kind', 'Default', 'Forced'],
            'text': ['ID', 'Format', 'Muxing mode', 'Codec ID', 'Codec ID/Info', 'Duration', 'Bit rate',
                     'Count of elements', 'Stream size', 'Title', 'Language', 'Default', 'Forced'],
        }
        media_info = ''
        for track_name in track_format.keys():
            for idx, track in enumerate(getattr(self._mediainfo, "{}_tracks".format(track_name))):
                if len(getattr(self._mediainfo, "{}_tracks".format(track_name))) > 1:
                    media_info += "{} #{}\n".format(track_name.capitalize(), idx + 1)
                else:
                    media_info += "{}\n".format(track_name.capitalize())

                media_info += '\n'.join(
                    filter(lambda a: a is not None,
                           [get_track_attr(track, name) for name in track_format[track_name]])) + '\n\n'
        # Special treatment with charters
        for track in self._mediainfo.menu_tracks:
            # Assuming there are always one menu tracks
            media_info += "Menu\n"
            for name in dir(track):
                # TODO: needs improvement
                if name[:2].isdigit():
                    media_info += "{} : {}\n".format(name[:-3].replace('_', ':') + '.' + name[-3:],
                                                     getattr(track, name))
            media_info += '\n'
        media_info.strip()
        return media_info

    def _generate_nfo(self):
        logger.info("正在生成nfo文件...")
        p = Path(self.folder)
        if p.is_file():
            with open(f"{p.resolve().parent.joinpath(p.stem)}.nfo", 'wb') as f:
                f.write(self.mediaInfo.encode())
        elif p.is_dir():
            with open(p.joinpath(f"{p.name}.nfo"), 'wb') as f:
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

        # 生成截图
        temp_dir = tempfile.mkdtemp()
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
        shutil.rmtree(temp_dir, ignore_errors=True)

        return screenshots

    def _mktorrent(self):
        logger.info("正在生成种子...")
        p = Path(self.folder)
        t = Torrent(path=self.folder, trackers=[self.announce_url],
                    comment=f"Generate by Differential made by XGCM")
        t.private = True
        t.generate(callback=make_torrent_progress, interval=1)
        t.write(p.resolve().parent.joinpath(f"{p.name if p.is_dir() else p.stem}.torrent"), overwrite=True)

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
            self._mktorrent()

    @abstractmethod
    def upload(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def mediaInfo(self):
        raise NotImplementedError()
