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
from itertools import chain
from urllib.parse import quote
from abc import ABC, ABCMeta, abstractmethod

import requests
from PIL import Image
from loguru import logger
from pymediainfo import MediaInfo

from differential import tools
from differential.plugin_register import PluginRegister
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
    ImageUploaded,
    get_all_images,
    byr_upload,
    hdbits_upload,
    imgbox_upload,
    ptpimg_upload,
    smms_upload,
    imgurl_upload,
    chevereto_api_upload,
    chevereto_username_upload,
    cloudinary_upload,
)


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
        byr_authorization: str = None,
        byr_alternative_url: str = None,
        imgbox_username: str = None,
        imgbox_password: str = None,
        imgbox_thumbnail_size: str = "300r",
        imgbox_family_safe: bool = True,
        ptgen_url: str = "https://ptgen.lgto.workers.dev",
        second_ptgen_url: str = "https://ptgen.caosen.com",
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
        self.screenshot_count = screenshot_count
        self.screenshot_path = screenshot_path
        self.optimize_screenshot = optimize_screenshot
        self.create_folder = create_folder
        self.use_short_bdinfo = use_short_bdinfo
        self.scan_bdinfo = scan_bdinfo
        self.image_hosting = image_hosting
        self.chevereto_hosting_url = chevereto_hosting_url
        self.imgurl_hosting_url = imgurl_hosting_url
        self.ptpimg_api_key = ptpimg_api_key
        self.hdbits_cookie = hdbits_cookie
        self.hdbits_thumb_size = hdbits_thumb_size
        self.chevereto_username = chevereto_username
        self.chevereto_password = chevereto_password
        self.chevereto_api_key = chevereto_api_key
        self.cloudinary_cloud_name = cloudinary_cloud_name
        self.cloudinary_api_key = cloudinary_api_key
        self.cloudinary_api_secret = cloudinary_api_secret
        self.imgurl_api_key = imgurl_api_key
        self.smms_api_key = smms_api_key
        self.byr_authorization = byr_authorization
        self.byr_alternative_url = byr_alternative_url
        self.imgbox_username = imgbox_username
        self.imgbox_password = imgbox_password
        self.imgbox_thumbnail_size = imgbox_thumbnail_size
        self.imgbox_family_safe = imgbox_family_safe
        self.ptgen_url = ptgen_url
        self.second_ptgen_url = second_ptgen_url
        self.announce_url = announce_url
        self.ptgen_retry = ptgen_retry
        self.generate_nfo = generate_nfo
        self.make_torrent = make_torrent
        self.easy_upload = easy_upload
        self.auto_feed = auto_feed
        self.trim_description = trim_description
        self.use_short_url = use_short_url
        self.encoder_log = encoder_log
        self.reuse_torrent = reuse_torrent
        self.from_torrent = from_torrent

        self.is_bdmv = False
        self._bdinfo = None
        self._main_file: Optional[Path] = None
        self._ptgen: dict = {}
        self._imdb: dict = {}
        self._mediainfo: Optional[MediaInfo] = None
        self._screenshots: list = []


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
            link = f"{self.upload_url}{quote(self.auto_feed_info, safe='#:/=@,')}"
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
        self._mediainfo = self._find_mediainfo()

        ptgen_retry = 2 * self.ptgen_retry
        self._ptgen = self._get_ptgen()
        while self._ptgen.get("failed") and ptgen_retry > 0:
            self._ptgen = self._get_ptgen(ptgen_retry <= self.ptgen_retry)
            ptgen_retry -= 1

        if self.generate_nfo:
            self._generate_nfo()
        if self.screenshot_count > 0:
            self._screenshots = self._get_screenshots()
        if self.make_torrent:
            make_torrent(
                self.folder,
                self.announce_url,
                self.__class__.__name__,
                self.reuse_torrent,
                self.from_torrent,
            )

    def upload_screenshots(self, img_dir: str) -> list:
        img_urls = []
        if (
            self.image_hosting == ImageHosting.HDB
            or self.image_hosting == ImageHosting.IMGBOX
        ):
            img_urls_file = Path(img_dir).joinpath(
                ".{}.{}".format(self.image_hosting.value, self.folder.name)
            )
            if img_urls_file.is_file():
                _img_urls = []
                with open(img_urls_file, "r") as f:
                    for line in f.readlines():
                        url, thumb = line.split(" ")
                        _img_urls.append(ImageUploaded(url, thumb))
                if len(_img_urls) == len(list(get_all_images(img_dir))):
                    logger.info(f"发现已上传的{len(_img_urls)}张截图链接")
                    return _img_urls
            if self.image_hosting == ImageHosting.HDB:
                img_urls = hdbits_upload(
                    sorted(get_all_images(img_dir)),
                    self.hdbits_cookie,
                    self.folder.name,
                    self.hdbits_thumb_size,
                )
            elif self.image_hosting == ImageHosting.IMGBOX:
                img_urls = imgbox_upload(
                    sorted(get_all_images(img_dir)),
                    self.imgbox_username,
                    self.imgbox_password,
                    self.folder.name,
                    self.imgbox_thumbnail_size,
                    self.imgbox_family_safe,
                    False,
                )
            if not img_urls:
                logger.info("图床上传失败，请自行上传截图：{}".format(img_dir))
            with open(img_urls_file, "w") as f:
                for img_url in img_urls:
                    f.write(f"{img_url.url} {img_url.thumb}\n")
        else:
            for count, img in enumerate(sorted(get_all_images(img_dir))):
                if img.is_file():
                    img_url = None
                    img_url_file = img.resolve().parent.joinpath(
                        ".{}.{}".format(self.image_hosting.value, img.stem)
                    )
                    if img_url_file.is_file():
                        with open(img_url_file, "r") as f:
                            line = f.read().strip()
                            if len(line.split(" ")) > 1:
                                img_url = ImageUploaded(
                                    line.split(" ")[0], line.split(" ")[1]
                                )
                            else:
                                img_url = ImageUploaded(line)
                            logger.info(f"发现已上传的第{count + 1}张截图链接：{img_url}")
                    else:
                        if self.image_hosting == ImageHosting.PTPIMG:
                            img_url = ptpimg_upload(img, self.ptpimg_api_key)
                        elif self.image_hosting == ImageHosting.CHEVERETO:
                            if not self.chevereto_hosting_url:
                                logger.error("Chevereto地址未提供，请设置chevereto_hosting_url")
                                sys.exit(1)
                            if self.chevereto_hosting_url.endswith("/"):
                                self.chevereto_hosting_url = self.chevereto_hosting_url[
                                    :-1
                                ]
                            if self.chevereto_api_key:
                                img_url = chevereto_api_upload(
                                    img,
                                    self.chevereto_hosting_url,
                                    self.chevereto_api_key,
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
                        elif self.image_hosting == ImageHosting.CLOUDINARY:
                            if (
                                not self.cloudinary_cloud_name
                                or not self.cloudinary_api_key
                                or not self.cloudinary_api_secret
                            ):
                                logger.error(
                                    "Cloudinary的参数未设置，请检查cloudinary_cloud_name/cloudinary_api_key/cloudinary_api_secret设置"
                                )
                            else:
                                img_url = cloudinary_upload(
                                    img,
                                    self.folder.stem,
                                    self.cloudinary_cloud_name,
                                    self.cloudinary_api_key,
                                    self.cloudinary_api_secret,
                                )
                        elif self.image_hosting == ImageHosting.IMGURL:
                            if self.imgurl_hosting_url.endswith("/"):
                                self.imgurl_hosting_url = self.imgurl_hosting_url[:-1]
                            img_url = imgurl_upload(
                                img, self.imgurl_hosting_url, self.imgurl_api_key
                            )
                        elif self.image_hosting == ImageHosting.SMMS:
                            img_url = smms_upload(img, self.smms_api_key)
                        elif self.image_hosting == ImageHosting.BYR:
                            if (
                                self.byr_alternative_url
                                and self.byr_alternative_url.endswith("/")
                            ):
                                self.byr_alternative_url = self.byr_alternative_url[:-1]
                            img_url = byr_upload(
                                img, self.byr_authorization, self.byr_alternative_url
                            )
                    if img_url:
                        logger.info(f"第{count + 1}张截图地址：{img_url.url}")
                        with open(img_url_file, "w") as f:
                            if img_url.thumb:
                                f.write(f"{img_url.url} {img_url.thumb}")
                            else:
                                f.write(f"{img_url.url}")
                        img_urls.append(img_url)
                    else:
                        logger.info(f"第{count + 1}张截图上传失败，请自行上传：{img.resolve()}")
        return img_urls

    def _get_ptgen(self, use_second: bool = False) -> dict:
        self._imdb = {}
        ptgen_failed = {"format": "PTGen获取失败，请自行获取相关信息", "failed": True}
        logger.info(f"正在获取PTGen: {self.url}")
        params = {"url": self.url}
        req = requests.get(self.ptgen_url if not use_second else self.second_ptgen_url, params)
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
        if not self.scan_bdinfo:
            logger.info("目标为BDMV，跳过扫描BDInfo")
            return "[BDINFO HERE]"
        else:
            logger.info("目标为BDMV，正在扫描BDInfo...")
            for f in Path(tempfile.gettempdir()).glob("Differential.bdinfo.*"):
                if f.is_dir() and self.folder.name in f.name:
                    if list(f.glob("*.txt")):
                        temp_dir = f.absolute()
                        logger.info(
                            "发现已生成的BDInfo，跳过扫描BDInfo...".format(self.screenshot_count)
                        )
                        break
            else:
                temp_dir = temp_dir = tempfile.mkdtemp(
                    prefix="Differential.bdinfo.{}.".format(version),
                    suffix=self.folder.name,
                )
                for f in self.folder.glob("**/BDMV"):
                    logger.info(f"正在扫描{f.parent}...")
                    if platform.system() == "Windows":
                        execute_with_output(
                            os.path.join(
                                os.path.dirname(tools.__file__),
                                "BDinfoCli.0.7.3\BDInfo.exe",
                            ),
                            f'-w "{f.parent}" "{temp_dir}"',
                            abort=True,
                        )
                    else:
                        execute_with_output(
                            "mono",
                            f""""{os.path.join(os.path.dirname(tools.__file__), 'BDinfoCli.0.7.3/BDInfo.exe')}" -w """
                            f'"{f.parent}" "{temp_dir}"',
                            abort=True,
                        )
            bdinfos = []
            for info in sorted(Path(temp_dir).glob("*.txt")):
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
            # shutil.rmtree(temp_dir, ignore_errors=True)
            return "\n\n".join(bdinfos)

    def _find_mediainfo(self) -> MediaInfo:
        # Always find the biggest file in the folder
        logger.info(f"正在获取Mediainfo: {self.folder}")
        has_bdmv = False
        if not self.folder.exists() and self.create_folder and "." in str(self.folder):
            # If file not exist and create_folder is True, try to find the folder with the same name
            self.folder = self.folder.parent.joinpath(self.folder.stem)
        if self.folder.is_file():
            if not self.create_folder:
                self._main_file = self.folder
            else:
                logger.info("目标是文件，正在创建文件夹...")
                folder = self.folder.parent.joinpath(self.folder.stem)
                filename = self.folder.name
                # TODO: decide whether to add exist_ok=True
                if not folder.is_dir():
                    os.makedirs(folder)
                shutil.move(str(self.folder.absolute()), folder)
                self.folder = folder
                self._main_file = folder.joinpath(filename)
        else:
            logger.info("目标为文件夹，正在获取最大的文件...")
            biggest_size = -1
            biggest_file = None
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
        elif self._main_file.suffix == ".iso":
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
        for f in Path(tempfile.gettempdir()).glob(
            "Differential.screenshots.{}.*".format(self.image_hosting.value)
        ):
            if f.is_dir() and self.folder.name in f.name:
                if 0 < self.screenshot_count == len(list(f.glob("*.png"))):
                    temp_dir = f.absolute()
                    logger.info("发现已生成的{}张截图，跳过截图...".format(self.screenshot_count))
                    break
        else:
            temp_dir = tempfile.mkdtemp(
                prefix="Differential.screenshots.{}.{}.".format(
                    self.image_hosting.value, version
                ),
                suffix=self.folder.name,
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

        if not self.screenshot_path:
            temp_dir = self._make_screenshots()
        else:
            temp_dir = self.screenshot_path
            images = list(sorted(get_all_images(temp_dir)))
            if not any(images):
                logger.warning("未在截图文件夹找到支持的图片文件（jpg、jpeg、png、gif、webp）")
            else:
                logger.info(
                    "发现以下图片文件：\n{}".format("\n".join("- " + i.name for i in images))
                )
        if temp_dir is None or not Path(temp_dir).exists():
            return []

        # 上传截图
        screenshots = self.upload_screenshots(temp_dir)
        logger.trace(f"Collected screenshots: {screenshots}")

        # 删除临时文件夹
        # shutil.rmtree(temp_dir, ignore_errors=True)

        return screenshots

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
            "\n".join([f"{uploaded}" for uploaded in self._screenshots]),
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
        return [u.url for u in self._screenshots]

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
