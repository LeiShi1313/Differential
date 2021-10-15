import re
import json
import argparse
from pathlib import Path
from urllib.parse import quote

from loguru import logger

from differential.plugins.base import Base
from differential.utils.browser import open_link
from differential.utils.mediainfo import get_track_attr


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

    def upload(self):
        self._prepare()
        if self.easy_upload:
            torrent_info = self.torrentInfo
            if self.trim_description:
                # 直接打印简介部分来绕过浏览器的链接长度限制
                torrent_info["description"] = ""
            logger.trace(f"torrent_info: {torrent_info}")
            link = f"{self.upload_url}#torrentInfo={quote(json.dumps(torrent_info))}"
            logger.trace(f"已生成自动上传链接：{link}")
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
