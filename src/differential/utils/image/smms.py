import json
from pathlib import Path
from typing import Optional, List

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded


def smms_upload(images: List[Path], api_key: Optional[str]) -> List[ImageUploaded]:
    if not api_key:
        logger.error("[Screenshots] 未设置SMMS API key")
        return []

    uploaded = []
    for img in images:
        if cached := ImageUploaded.from_pickle(img, ImageHosting.SMMS):
            uploaded.append(cached)
        elif u := _smms_upload(img, api_key):
            uploaded.append(u)
    return uploaded

def _smms_upload(img: Path, api_key: str) -> Optional[ImageUploaded]:
    headers = {'Authorization': api_key}
    files = {'smfile': open(img, 'rb'), 'format': 'json'}
    req = requests.post('https://sm.ms/api/v2/upload', headers=headers, files=files)

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
    if not res.get('success') and res.get('code') != 'image_repeated':
        logger.warning(f"[Screenshots] 上传图片失败: [{res.get('code')}]{res.get('message')}")
        return None
    if res.get('code') == 'image_repeated':
        return res.get('images')
    if 'data' not in res or 'url' not in res['data']:
        logger.warning("[Screenshots] 图片直链获取失败")
        return None
    return ImageUploaded(hosting=ImageHosting.SMMS, image=img, url=res['data']['url'])