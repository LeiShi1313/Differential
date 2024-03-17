import re
import json
import hashlib
from time import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests
from loguru import logger

from differential.utils.image.types import ImageUploaded


def cloudinary_upload(img: Path, folder: str, cloud_name: str, api_key: str, api_secret: str) -> Optional[ImageUploaded]:
    data = {
        'folder': folder,
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
        logger.warning(f"上传图片失败: [{req.status_code}] {res['error'].get('message')}")
        return None
    if 'url' not in res or 'secure_url' not in res:
        logger.warning(f"图片直链获取失败")
        return None
    return ImageUploaded(res['secure_url'] if 'secure_url' in res else res['url'])