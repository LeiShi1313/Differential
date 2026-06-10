import os
import shutil
import subprocess
import tempfile
from PIL import Image
from loguru import logger
from pathlib import Path
from decimal import Decimal

from differential.version import version
from differential.utils.binary import execute
from differential.constants import ImageHosting, SCREENSHOT_TONEMAP_STATES
from differential.utils.image import (
    get_all_images,
    byr_upload,
    hdbits_upload,
    imgbox_upload,
    ptpimg_upload,
    smms_upload,
    imgurl_upload,
    chevereto_upload,
    cloudinary_upload,
    lsky_upload,
)

class ScreenshotHandler:
    """
    Manages creating (ffmpeg) and uploading screenshots
    to a given image host.
    """

    PQ_TONEMAP = "tonemap=tonemap=hable:desat=0:peak=1000"
    HLG_TONEMAP = "tonemap=tonemap=mobius:desat=0:peak=400"
    _ffmpeg_filter_names = None

    def __init__(
        self,
        folder: Path,
        screenshot_count: int = 0,
        screenshot_path: str = None,
        optimize_screenshot: bool = True,
        screenshot_tonemap: str = "auto",
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
        lsky_hosting_url: str = "",
        lsky_token: str = None,
        lsky_email: str = None,
        lsky_password: str = None,
    ):
        self.folder = folder
        self.screenshot_count = screenshot_count
        self.screenshot_path = screenshot_path
        self.optimize_screenshot = optimize_screenshot
        self.screenshot_tonemap = self._normalize_tonemap_mode(screenshot_tonemap)
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
        self.byr_cookie = byr_cookie
        self.byr_alternative_url = byr_alternative_url
        self.imgbox_username = imgbox_username
        self.imgbox_password = imgbox_password
        self.imgbox_thumbnail_size = imgbox_thumbnail_size
        self.imgbox_family_safe = imgbox_family_safe
        self.lsky_hosting_url = lsky_hosting_url
        self.lsky_token = lsky_token
        self.lsky_email = lsky_email
        self.lsky_password = lsky_password

        self.screenshots: list = []

    def collect_screenshots(
        self,
        main_file: Path,
        resolution: str,
        duration: Decimal,
        tracks=None,
    ) -> list:
        """
        If screenshot_path is given, use images from that folder.
        Otherwise, generate screenshots from main_file.
        Then upload them.
        Returns a list of ImageUploaded objects.
        """
        if self.screenshot_count <= 0:
            return

        if self.screenshot_path:
            logger.info("[Screenshots] 使用提供的截图文件夹...")
            self.screenshots = self._upload_screenshots(self.screenshot_path)
        else:
            logger.info("[Screenshots] 生成并上传截图...")
            temp_dir = self._generate_screenshots(
                main_file,
                resolution,
                duration,
                tracks,
            )
            if not temp_dir:
                return
            self.screenshots = self._upload_screenshots(temp_dir)

    def _generate_screenshots(
        self,
        main_file: Path,
        resolution: str,
        duration: Decimal,
        tracks=None,
    ) -> str:
        if not resolution or not duration:
            logger.warning("[Screenshots] 文件无法提取分辨率或时长，无法生成截图")
            return None

        for f in Path(tempfile.gettempdir()).glob(
            f"Differential.screenshots.{version}.*.{self.folder.name}"
        ):
            if f.is_dir():
                if 0 < self.screenshot_count == len(list(f.glob("*.png"))):
                    logger.info("[Screenshots] 发现已生成的{}张截图，跳过截图...".format(self.screenshot_count))
                    return f.absolute()

        tmp_dir = tempfile.mkdtemp(prefix=f"Differential.screenshots.{version}.", suffix=f".{self.folder.name}")
        for i in range(1, self.screenshot_count + 1):
            logger.info(f"正在生成第{i}张截图...")
            timestamp_ms = int(i * duration / (self.screenshot_count + 1))
            output_path = Path(tmp_dir).joinpath(f"{main_file.stem}.thumb_{i:02d}.png")

            args = self._build_ffmpeg_args(
                main_file,
                output_path,
                resolution,
                timestamp_ms,
                tracks,
            )
            execute("ffmpeg", args)

            if self.optimize_screenshot and output_path.exists():
                try:
                    img = Image.open(output_path)
                    img.save(output_path, format="PNG", optimize=True)
                except Exception as e:
                    logger.error(f"Screenshot optimization failed: {e}")

        return tmp_dir

    def _build_ffmpeg_args(
        self,
        main_file: Path,
        output_path: Path,
        resolution: str,
        timestamp_ms: int,
        tracks=None,
    ) -> str:
        video_filter_or_size = f"-s {resolution}"
        if self._should_tonemap(tracks):
            filters = [self._tonemap_filter(tracks)]
            scale_filter = self._scale_filter(resolution)
            if scale_filter:
                filters.append(scale_filter)
            filters.append("format=rgb24")
            video_filter_or_size = f'-vf "{",".join(filters)}"'

        return (
            f'-y -ss {timestamp_ms}ms -skip_frame nokey '
            f'-i "{main_file.absolute()}" '
            f'{video_filter_or_size} -vsync 0 -vframes 1 -c:v png "{output_path}"'
        )

    def _should_tonemap(self, tracks=None) -> bool:
        if self.screenshot_tonemap == "always":
            return True
        if self.screenshot_tonemap == "never":
            return False
        return self._tracks_need_tonemap(tracks)

    @classmethod
    def _available_ffmpeg_filters(cls) -> set:
        if cls._ffmpeg_filter_names is not None:
            return cls._ffmpeg_filter_names

        executable = os.environ.get("FFMPEGPATH") or shutil.which("ffmpeg")
        if not executable:
            cls._ffmpeg_filter_names = set()
            return cls._ffmpeg_filter_names

        try:
            proc = subprocess.run(
                [str(executable), "-hide_banner", "-filters"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except Exception as e:
            logger.warning(f"[Screenshots] 无法检测ffmpeg滤镜列表: {e}")
            cls._ffmpeg_filter_names = set()
            return cls._ffmpeg_filter_names

        names = set()
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and "->" in parts[2]:
                names.add(parts[1])
        cls._ffmpeg_filter_names = names
        return cls._ffmpeg_filter_names

    @classmethod
    def _ffmpeg_supports_filter(cls, filter_name: str) -> bool:
        filters = cls._available_ffmpeg_filters()
        if not filters:
            return filter_name in {"zscale", "scale", "tonemap"}
        return filter_name in filters

    def _tonemap_filter(self, tracks=None) -> str:
        transfer = self._hdr_input_transfer(tracks)
        tonemap = self._tonemap_operator(transfer)
        if self._ffmpeg_supports_filter("zscale"):
            return (
                "zscale="
                "primariesin=bt2020:"
                f"transferin={transfer}:"
                "matrixin=bt2020nc:"
                "transfer=linear:npl=100,"
                "format=gbrpf32le,"
                f"{tonemap},"
                "zscale=primaries=bt709:transfer=bt709:matrix=bt709:range=limited"
            )

        return (
            "scale="
            f"in_transfer={transfer}:"
            "out_transfer=linear:"
            "in_primaries=bt2020:"
            "out_primaries=bt2020:"
            "in_color_matrix=bt2020nc:"
            "out_color_matrix=bt2020nc,"
            "format=gbrpf32le,"
            f"{tonemap},"
            "scale="
            "in_transfer=linear:"
            "out_transfer=bt709:"
            "in_primaries=bt2020:"
            "out_primaries=bt709:"
            "in_color_matrix=bt2020nc:"
            "out_color_matrix=bt709"
        )

    @classmethod
    def _tonemap_operator(cls, transfer: str) -> str:
        if transfer == "arib-std-b67":
            return cls.HLG_TONEMAP
        return cls.PQ_TONEMAP

    @staticmethod
    def _hdr_input_transfer(tracks=None) -> str:
        text = ScreenshotHandler._video_track_text(tracks)
        hlg_tokens = ("hlg", "hybrid log", "arib std-b67", "arib-std-b67")
        if any(token in text for token in hlg_tokens):
            return "arib-std-b67"
        return "smpte2084"

    @staticmethod
    def _normalize_tonemap_mode(value) -> str:
        if isinstance(value, bool):
            return "always" if value else "never"
        return SCREENSHOT_TONEMAP_STATES.get(str(value or "").strip().lower(), "auto")

    @staticmethod
    def _video_track_text(tracks=None) -> str:
        values = []
        for track in tracks or []:
            if getattr(track, "track_type", "") != "Video":
                continue
            for attr in (
                "hdr_format",
                "hdr_format_compatibility",
                "commercial_name",
                "transfer_characteristics",
                "transfer_characteristics_original",
                "color_primaries",
                "colour_primaries",
                "format_profile",
                "codec_id",
                "format",
            ):
                value = getattr(track, attr, None)
                if isinstance(value, (list, tuple)):
                    values.extend(str(item) for item in value if item)
                elif value:
                    values.append(str(value))
        return " ".join(values).lower()

    @staticmethod
    def _tracks_need_tonemap(tracks=None) -> bool:
        text = ScreenshotHandler._video_track_text(tracks)
        hdr_tokens = (
            "dolby vision",
            "dolbyvision",
            "dovi",
            "dvhe",
            "dvh1",
            "hdr",
            "hdr10",
            "hdr10+",
            "pq",
            "perceptual quantization",
            "hlg",
            "hybrid log",
            "smpte st 2084",
            "smpte2084",
            "st 2084",
            "arib std-b67",
        )
        return any(token in text for token in hdr_tokens)

    @staticmethod
    def _scale_filter(resolution: str) -> str:
        parts = str(resolution or "").lower().split("x", 1)
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            logger.warning(f"[Screenshots] 无法将分辨率 {resolution} 转换为ffmpeg scale滤镜")
            return ""
        return f"scale={parts[0]}:{parts[1]}"

    def _upload_screenshots(self, img_dir: str) -> list:
        """
        Upload screenshots from the given directory to the chosen image host.
        Returns a list of ImageUploaded objects.
        """
        images = sorted(get_all_images(img_dir))
        if not images:
            logger.warning("[Screenshots] 未找到可用图片.")
            return []

        uploaded = []
        if self.image_hosting == ImageHosting.HDB:
            uploaded = hdbits_upload(
                images,
                self.hdbits_cookie,
                self.folder.name,
                self.hdbits_thumb_size,
            )
        elif self.image_hosting == ImageHosting.IMGBOX:
            uploaded = imgbox_upload(
                images,
                self.imgbox_username,
                self.imgbox_password,
                self.folder.name,
                self.imgbox_thumbnail_size,
                self.imgbox_family_safe,
                False,
            )
        elif self.image_hosting == ImageHosting.PTPIMG:
            uploaded = ptpimg_upload(images, self.ptpimg_api_key)
        elif self.image_hosting == ImageHosting.CHEVERETO:
            uploaded = chevereto_upload(images, self.chevereto_hosting_url, self.chevereto_api_key, self.chevereto_username, self.chevereto_password)
        elif self.image_hosting == ImageHosting.CLOUDINARY:
            uploaded = cloudinary_upload(images, self.folder.stem, self.cloudinary_cloud_name, self.cloudinary_api_key, self.cloudinary_api_secret)
        elif self.image_hosting == ImageHosting.IMGURL:
            uploaded = imgurl_upload(images, self.imgurl_hosting_url, self.imgurl_api_key)
        elif self.image_hosting == ImageHosting.SMMS:
            uploaded = smms_upload(images, self.smms_api_key)
        elif self.image_hosting == ImageHosting.BYR:
            uploaded = byr_upload( images, self.byr_cookie, self.byr_alternative_url)
        elif self.image_hosting == ImageHosting.LSKY:
            uploaded = lsky_upload(images, self.lsky_hosting_url, self.lsky_token, self.lsky_email, self.lsky_password)
        else:
            logger.error(f"不支持的图片上传方式: {self.image_hosting}")

        return uploaded
