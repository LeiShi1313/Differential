import re
from pathlib import Path
from typing import Optional, List

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded


def get_csrf_token(session) -> Optional[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"
    }
    req = session.get("https://imgbox.com", headers=headers)
    if req.ok:
        if m := re.search(r"content=\"(.*?)\" name=\"csrf-token\"", req.text):
            return m.groups()[0]
    return None


def get_token(
    session, csrf_token: str, gallery_title: Optional[str], allow_comment: bool = False
) -> dict:
    headers = {
        "X-CSRF-Token": csrf_token,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36",
    }
    data = {
        "gallery": "true" if gallery_title is not None else "false",
        # TODO: need to test when gallery title is None
        "gallery_title": gallery_title,
        "comments_enabled": str(int(allow_comment)),
    }
    req = session.post(
        "https://imgbox.com/ajax/token/generate", data=data, headers=headers, json=True
    )
    if req.ok and req.json().get("ok"):
        return req.json()
    return {}


def login(session, username, password, csrf_token):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"
    }
    data = {
        "utf8": "✓",
        "authenticity_token": csrf_token,
        "user[login]": username,
        "user[password]": password,
    }
    logger.info("[Screenshots] 正在登录imgbox...")
    req = session.post("https://imgbox.com/login", data=data, headers=headers)
    if len(req.history) and req.history[-1].status_code == 302:
        logger.info("[Screenshots] 登录成功")
        return
    logger.warning("[Screenshots] 登录失败，使用匿名模式上传")


def imgbox_upload(
    imgs: List[Path],
    usernmae: str = None,
    password: str = None,
    gallery_title: str = None,
    thumbnail_size: str = "300r",
    is_family_safe: bool = True,
    allow_comment: bool = False,
) -> List[ImageUploaded]:
    uploaded: List[Union[ImageUploaded, None]] = [None] * len(imgs)
    for idx, img in enumerate(imgs):
        if cached := ImageUploaded.from_pickle(img, ImageHosting.IMGBOX):
            uploaded[idx] = cached

    if any(x is None for x in uploaded):
        session = requests.Session()
        csrf_token = get_csrf_token(session)
        if not csrf_token:
            logger.warning("[Screenshots] 获取csrf token失败")
            return []
        if usernmae and password:
            login(session, usernmae, password, csrf_token)
        token = get_token(session, csrf_token, gallery_title, allow_comment)
        if not token:
            logger.warning("[Screenshots] 获取token失败")
            return []

        headers = {
            "X-CSRF-Token": csrf_token,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36",
        }
        for idx, img in enumerate(imgs):
            if uploaded[idx]:
                continue
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
                logger.warning(
                    f"[Screenshots] 上传图片失败: HTTP {req.status_code}, reason: {req.reason}"
                )
                continue
            elif req.json().get("error"):
                logger.trace(req.content)
                logger.warning(
                    f"[Screenshots] 上传图片失败: Code {req.json()['error'].get('code')}, message: {req.json()['error]'].get('message')}"
                )
                continue
            uploaded[idx] = ImageUploaded(
                hosting=ImageHosting.IMGBOX,
                image=imgs[idx],
                url=req.json().get("files", [{}])[0].get("original_url"),
                thumb=req.json().get("files", [{}])[0].get("thumbnail_url"),
            )
            logger.info(f"[Screenshots] 第{idx+1}张截图上传成功")

    return [u for u in uploaded if isinstance(u, ImageUploaded)]
