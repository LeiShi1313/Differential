import tempfile
from PIL import Image
from loguru import logger
from pathlib import Path
from decimal import Decimal

from differential.version import version
from differential.utils.binary import execute
from differential.constants import ImageHosting
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
)

class ScreenshotHandler:
    """
    Manages creating (ffmpeg) and uploading screenshots
    to a given image host.
    """

    def __init__(
        self,
        folder: Path,
        screenshot_count: int = 0,
        screenshot_path: str = None,
        optimize_screenshot: bool = True,
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
    ):
        self.folder = folder
        self.screenshot_count = screenshot_count
        self.screenshot_path = screenshot_path
        self.optimize_screenshot = optimize_screenshot
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

        self.screenshots: list = []

    def collect_screenshots(self, main_file: Path, resolution: str, duration: Decimal) -> list:
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
            temp_dir = self._generate_screenshots(main_file, resolution, duration)
            if not temp_dir:
                return
            self.screenshots = self._upload_screenshots(temp_dir)

    def _generate_screenshots(self, main_file: Path, resolution: str, duration: Decimal) -> str:
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

            args = (
                f'-y -ss {timestamp_ms}ms -skip_frame nokey '
                f'-i "{main_file.absolute()}" '
                f'-s {resolution} -vsync 0 -vframes 1 -c:v png "{output_path}"'
            )
            execute("ffmpeg", args)

            if self.optimize_screenshot and output_path.exists():
                try:
                    img = Image.open(output_path)
                    img.save(output_path, format="PNG", optimize=True)
                except Exception as e:
                    logger.error(f"Screenshot optimization failed: {e}")

        return tmp_dir

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
        else:
            logger.error(f"不支持的图片上传方式: {self.image_hosting}")

        return uploaded