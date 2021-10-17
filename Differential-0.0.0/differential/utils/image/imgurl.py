import json
from pathlib import Path
from typing import Optional

import requests
from loguru import logger


def imgurl_upload(img: Path, url: str, api_key: str) -> Optional[str]:
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
            f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
            f"{res.get('msg') if 'msg' in res else ''}")
        return None
    if res.get('code') > 200:
        logger.warning(f"上传图片失败: [{res.get('code')}]{res.get('msg')}")
        return None
    return res.get('url')