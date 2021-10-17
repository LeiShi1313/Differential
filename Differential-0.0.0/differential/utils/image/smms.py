import json
from pathlib import Path
from typing import Optional

import requests
from loguru import logger

def smms_upload(img: Path, api_key: str) -> Optional[str]:
    data = {'Authorization': api_key}
    files = {'smfile': open(img, 'rb'), 'format': 'json'}
    req = requests.post('https://sm.ms/api/v2/upload', data=data, files=files)

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if not req.ok:
        logger.trace(req.content)
        logger.warning(
            f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
            f"{res.get('msg') if 'msg' in res else ''}")
        return None
    if not res.get('success') and res.get('code') != 'image_repeated':
        logger.warning(f"上传图片失败: [{res.get('code')}]{res.get('message')}")
        return None
    if res.get('code') == 'image_repeated':
        return res.get('images')
    if 'data' not in res or 'url' not in res['data']:
        logger.warning(f"图片直链获取失败")
        return None
    return res['data']['url']