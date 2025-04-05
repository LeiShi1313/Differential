import re
import json
from pathlib import Path
from typing import Optional, List

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded

sessions = {}

def chevereto_upload(images: List[Path], url: Optional[str], api_key: Optional[str], username: Optional[str], password: Optional[str]) -> List[ImageUploaded]:
    if not url:
        logger.error("Chevereto地址未提供，请设置chevereto_hosting_url")
        return []

    if url.endswith("/"):
        url = url[:-1]

    uploaded = []
    for img in images:
        if cached := ImageUploaded.from_pickle(img, ImageHosting.CHEVERETO):
            uploaded.append(cached)
        elif api_key:
            if u := chevereto_api_upload(img, url, api_key):
                uploaded.append(u)
        elif username and password:
            if u := chevereto_username_upload(img, url, username, password):
                uploaded.append(u)
        else:
            logger.error( "Chevereto的API或用户名或密码未设置，请检查chevereto-username/chevereto-password设置")
    return uploaded

def chevereto_api_upload(img: Path, url: str, api_key: str) -> Optional[ImageUploaded]:
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
    return ImageUploaded(hosting=ImageHosting.CHEVERETO, image=img, url=res['image']['url'])


def chevereto_cookie_upload(img: Path, url: str, cookie: str, auth_token: str) -> Optional[ImageUploaded]:
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
    if 'status_code' in res and res.get('status_code') != 200:
        logger.warning(f"上传图片失败: [{res['status_code']}] {res.get('status_txt')}")
        return None 
    if 'image' not in res or 'url' not in res['image']:
        logger.warning(f"图片直链获取失败")
        return None
    return ImageUploaded(hosting=ImageHosting.CHEVERETO, image=img, url=res['image']['url'])


def with_session(func):
    def wrapper(img: Path, url: str, username: str, password: str):
        if (username, password) not in sessions:
            session = requests.Session()
            req = session.get(url)
            m = re.search(r'auth_token.*?\"(\w+)\"', req.text)
            if not m:
                logger.warning("未找到auth_token，请重试")
                return
            auth_token = m.groups()[0]
            data = {'auth_token': auth_token, 'login-subject': username, 'password': password, 'keep-login': 1}
            logger.info("正在登录Chevereto...")
            req = session.post(f"{url}/login", data=data)
            if not req.ok:
                logger.warning("Chevereto登录失败，请重试")
                return
            sessions[(username, password)] = (session, auth_token)
        else:
            session, auth_token = sessions.get((username, password))
        return func(session, img, url, auth_token)
    return wrapper


@with_session
def chevereto_username_upload(session: requests.Session, img: Path, url: str, auth_token: str) -> Optional[ImageUploaded]:
    data = {'type': 'file', 'action': 'upload', 'nsfw': 0, 'auth_token': auth_token}
    files = {'source': open(img, 'rb')}
    req = session.post(f'{url}/json', data=data, files=files)

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
    if 'status_code' in res and res.get('status_code') != 200:
        logger.warning(f"上传图片失败: [{res['status_code']}] {res.get('status_txt')}")
        return None 
    if 'image' not in res or 'url' not in res['image']:
        logger.warning(f"图片直链获取失败")
        return None
    return ImageUploaded(hosting=ImageHosting.CHEVERETO, image=img, url=res['image']['url'])