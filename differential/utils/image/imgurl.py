import json
from pathlib import Path
from typing import Optional, List

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded


def imgurl_upload(images: List[Path], url: Optional[str], api_key: Optional[str]) -> List[ImageUploaded]:
    if not url:
        logger.error("[Screenshots] 未设置imgurl地址")
        return []
    if url.endswith("/"):
        url = url[:-1]

    if not api_key:
        logger.error("[Screenshots] 未设置imgurl API key")

    uploaded = []
    for img in images:
        if cached := ImageUploaded.from_pickle(img, ImageHosting.IMGURL):
            uploaded.append(cached)
        elif u := _imgurl_upload(img, url, api_key):
            uploaded.append(u)

    return uploaded


def _imgurl_upload(img: Path, url: str, api_key: str) -> Optional[ImageUploaded]:
    data = {'token': api_key}
    files = {'file': open(img, 'rb')}
    req = requests.post(f'{url}/api/upload', data=data, files=files)

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if not req.ok:
        logger.trace(req.content)
        logger.warning(
            f"[Screenshots] 上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
            f"{res.get('msg') if 'msg' in res else ''}")
        return None
    if res.get('code') > 200:
        logger.warning(f"[Screenshots] 上传图片失败: [{res.get('code')}]{res.get('msg')}")
        return None
    return ImageUploaded(hosting=ImageHosting.IMGURL, image=img, url=res.get('url'))