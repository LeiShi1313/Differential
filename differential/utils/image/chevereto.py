import json
from pathlib import Path
from typing import Optional

import requests
from loguru import logger


def chevereto_api_upload(img: Path, url: str, api_key: str) -> Optional[str]:
    data = {'key': api_key}
    files = {'source': open(img, 'rb')}
    req = requests.post(f'{url}/api/1/upload', data=data, files=files)

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if not req.ok:
        logger.trace(req.content)
        logger.warning(
            f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
            f"{res['error'].get('message') if 'error' in res else ''}")
        return None
    if 'error' in res:
        logger.warning(f"上传图片失败: [{res['error'].get('code')}]{res['error'].get('message')}")
        return None
    if 'image' not in res or 'url' not in res['image']:
        logger.warning(f"图片直链获取失败")
        return None
    return res['image']['url']


def chevereto_cookie_upload(img: Path, url: str, cookie: str, auth_token: str) -> Optional[str]:
    headers = {'cookie': cookie}
    data = {'type': 'file', 'action': 'upload', 'nsfw': 0, 'auth_token': auth_token}
    files = {'source': open(img, 'rb')}
    req = requests.post(f'{url}/json', data=data, files=files, headers=headers)

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if not req.ok:
        logger.trace(req.content)
        logger.warning(
            f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
            f"{res['error'].get('message') if 'error' in res else ''}")
        return None
    if 'error' in res:
        logger.warning(f"上传图片失败: [{res['error'].get('code')}] {res['error'].get('context')} {res['error'].get('message')}")
        return None
    if res.get('status_code') != 200:
        logger.warning(f"上传图片失败: [{res['status_code']}] {res.get('status_txt')}")
        return None 
    if 'image' not in res or 'url' not in res['image']:
        logger.warning(f"图片直链获取失败")
        return None
    return res['image']['url']