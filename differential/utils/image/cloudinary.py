import re
import json
import hashlib
from time import time
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlencode

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded


def cloudinary_upload(images: List[Path], folder_name: str, cloud_name: Optional[str], api_key: Optional[str], api_secret: Optional[str]):
    if not cloud_name or not api_key or not api_secret:
        logger.error( "Cloudinary的参数未设置，请检查cloudinary_cloud_name/cloudinary_api_key/cloudinary_api_secret设置")
        return []

    uploaded = []
    for img in images:
        if cached := ImageUploaded.from_pickle(img, ImageHosting.CLOUDINARY):
            uploaded.append(cached)
        elif u := _cloudinary_upload(img, folder_name, cloud_name, api_key, api_secret):
            uploaded.append(u)

    return uploaded


def _cloudinary_upload(img: Path, folder_name: str, cloud_name: str, api_key: str, api_secret: str) -> Optional[ImageUploaded]:
    data = {
        'folder': folder_name,
        'timestamp': int(time()),
        'use_filename': 'true',
    }
    serialized = '&'.join(f"{k}={v}" for k, v in data.items()) + api_secret
    data['signature'] = hashlib.sha1(serialized.encode('utf-8')).hexdigest()
    data['api_key'] = api_key
    files = {
        'file': open(img, "rb"),
    }

    req = requests.post(f'https://api.cloudinary.com/v1_1/{cloud_name}/image/upload', data=data, files=files)
    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}

    if 'error' in res:
        logger.warning(f"[Screenshots] 上传图片失败: [{req.status_code}] {res['error'].get('message')}")
        return None
    if 'url' not in res or 'secure_url' not in res:
        logger.warning(f"[Screenshots] 图片直链获取失败")
        return None
    return ImageUploaded(hosting=ImageHosting.CLOUDINARY, image=img, url=res['secure_url'] if 'secure_url' in res else res['url'])