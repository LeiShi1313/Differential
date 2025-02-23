import json
from pathlib import Path
from typing import Optional, List

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded


def ptpimg_upload(imgs: List[Path], api_key: str) -> List[ImageUploaded]:
    uploaded = []
    for img in imgs:
        if cached := ImageUploaded.from_pickle(img, ImageHosting.PTPIMG):
            uploaded.append(cached)
        elif u := _ptpimg_upload(img, api_key):
            uploaded.append(u)
    return uploaded


def _ptpimg_upload(img: Path, api_key: str) -> Optional[ImageUploaded]:
    files = {'file-upload[0]': open(img, 'rb')}
    req = requests.post('https://ptpimg.me/upload.php', data={'api_key': api_key}, files=files)

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if not req.ok:
        logger.trace(req.content)
        logger.warning(
            f"[Screenshots] 上传图片失败: HTTP {req.status_code}, reason: {req.reason}")
        return None
    if len(res) < 1 or 'code' not in res[0] or 'ext' not in res[0]:
        logger.warning("[Screenshots] 图片直链获取失败")
        return None
    return ImageUploaded(hosting=ImageHosting.PTPIMG, image=img, url=f"https://ptpimg.me/{res[0].get('code')}.{res[0].get('ext')}")