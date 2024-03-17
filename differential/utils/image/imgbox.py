import os
import re
import random
from pathlib import Path
from typing import Optional, List
from string import ascii_letters, digits

import requests
from loguru import logger
from lxml.html import fromstring

from differential.utils.image.types import ImageUploaded


def get_csrf_token(session) -> Optional[str]:
    req = session.get('https://imgbox.com')
    if req.ok:
        m = re.search(r"content=\"(.*?)\" name=\"csrf-token\"", req.text)
        if m:
            return m.groups()[0]
    return None


def get_token(session, csrf_token: str, gallery_title: Optional[str], allow_comment: bool = False) -> dict:
    headers = {
        'X-CSRF-Token': csrf_token,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'
    }
    data = {
        "gallery": "true" if gallery_title is not None else "false",
        # TODO: need to test when gallery title is None
        "gallery_title": gallery_title,
        "comments_enabled": str(int(allow_comment)),
    }
    req = session.post("https://imgbox.com/ajax/token/generate", data=data, headers=headers, json=True)
    if req.ok and req.json().get("ok"):
        return req.json()
    return {}

def login(session, username, password, csrf_token):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'
    }
    data = {
        "utf8": "✓",
        "authenticity_token": csrf_token,
        "user[login]": username,
        "user[password]": password
    }
    logger.info("正在登录imgbox...")
    req = session.post("https://imgbox.com/login", data=data, headers=headers)
    if len(req.history) and req.history[-1].status_code == 302:
        logger.info("登录成功")
        return
    logger.warning("登录失败，使用匿名模式上传")
        

def imgbox_upload(
    imgs: List[Path],
    usernmae: str = None,
    password: str = None,
    gallery_title: str = None,
    thumbnail_size: str = "300r",
    is_family_safe: bool = True,
    allow_comment: bool = False,
) -> List[ImageUploaded]:
    session = requests.Session()
    csrf_token = get_csrf_token(session)
    if usernmae and password:
        login(session, usernmae, password, csrf_token)
    token = get_token(session, csrf_token, gallery_title, allow_comment)
    if not token:
        logger.warning("获取token失败")
        return []

    headers = {
        'X-CSRF-Token': csrf_token,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'
    }
    urls = []
    for count, img in enumerate(imgs):
        data = {
            "token_id": str(token.get("token_id")),
            "token_secret": token.get("token_secret"),
            "content_type": str(int(is_family_safe)),
            "thumbnail_size": thumbnail_size,
            "gallery_id": token.get("gallery_id"),
            "gallery_secret": token.get("gallery_secret"),
            "comments_enabled": str(int(allow_comment)),
        }
        files = {
            "files[]": open(img, "rb"),
        }
        req = session.post(
            "https://imgbox.com/upload/process",
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
        urls.append(req.json())

    logger.info(f"Imgbox图床链接：https://imgbox.com/upload/edit/{token.get('token_id')}/{token.get('token_secret')}")
    return [
        ImageUploaded(
            url.get("files", [{}])[0].get("original_url"),
            url.get("files", [{}])[0].get("thumbnail_url"),
        )
        for url in urls
    ]
