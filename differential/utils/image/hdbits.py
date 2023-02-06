import os
import re
import random
from pathlib import Path
from typing import Optional, List
from string import ascii_letters, digits

import requests
from loguru import logger
from lxml.html import fromstring

from differential.utils.image import ImageUploaded


def get_uploadid(cookie: str) -> str:
    req = requests.get("https://img.hdbits.org", headers={"cookie": cookie})
    m = re.search(r"uploadid=([a-zA-Z0-9]{15})", req.text)
    if m:
        return m.groups()[0]
    return ""


def hdbits_upload(
    imgs: List[Path], cookie: str, galleryname: str = None, thumb_size: str = "w300"
) -> List[ImageUploaded]:
    uploadid = get_uploadid(cookie)
    if not uploadid:
        logger.warning("获取uploadid失败")
        return []
    headers = {
        "cookie": cookie,
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36"
        }
    params = {"uploadid": uploadid}

    for count, img in enumerate(imgs):
        data = {
            "name": img.name,
            "thumbsize": thumb_size,
            "galleryoption": 1,
            "galleryname": galleryname if galleryname else uploadid,
            "existgallery": 1,
        }
        files = {
            "file": open(img, "rb"),
        }
        req = requests.post(
            f"https://img.hdbits.org/upload.php?uploadid={uploadid}",
            data=data,
            files=files,
            headers=headers,
        )

        if not req.ok:
            logger.trace(req.content)
            logger.warning(f"上传图片失败: HTTP {req.status_code}, reason: {req.reason}")
            return None
        elif req.json().get("error"):
            logger.trace(req.content)
            logger.warning(
                f"上传图片失败: Code {req.json()['error'].get('code')}, message: {req.json()['error]'].get('message')}"
            )
            return None
        logger.info(f"第{count+1}张截图上传成功")

    req = requests.get(f"https://img.hdbits.org/done/{uploadid}", headers=headers)
    if not req.ok:
        logger.trace(req.content)
        logger.warning(f"图片直链获取失败: HTTP {req.status_code}, reason: {req.reason}")
        return None
    root = fromstring(req.content)
    textareas = root.xpath("*//textarea")
    if not textareas:
        logger.warning(f"图片直链获取失败: {root}")
        return None
    urls = textareas[1].text.split("\n")
    thumbs = textareas[2].text.split("\n")
    if len(urls) != len(thumbs):
        logger.warning(f"图片直链获取失败: {root}")
        return None

    return [
        ImageUploaded(
            urls[i],
            thumbs[i].replace("i.hdbits.org", "t.hdbits.org").replace(".png", ".jpg"),
        )
        for i in range(len(urls))
    ]
