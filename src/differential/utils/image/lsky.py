import re
import json
from pathlib import Path
from typing import Optional, List

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded

tokens = {}


def lsky_upload(
    images: List[Path],
    url: Optional[str],
    token: Optional[str],
    email: Optional[str],
    password: Optional[str],
) -> List[ImageUploaded]:
    if not url:
        logger.error("Lsky Pro地址未提供，请设置lsky_hosting_url")
        return []

    if url.endswith("/"):
        url = url[:-1]

    uploaded = []
    for img in images:
        if cached := ImageUploaded.from_pickle(img, ImageHosting.LSKY):
            uploaded.append(cached)
        elif token:
            if u := lsky_api_upload(img, url, token):
                uploaded.append(u)
        elif email and password:
            token = get_token(email, password, url)
            if u := lsky_api_upload(img, url, token):
                uploaded.append(u)
        else:
            logger.error(
                "Lsky Pro的Token或邮箱或密码未设置，请检查lsky-token/lsky-email/lsky-password设置"
            )
    return uploaded


def lsky_api_upload(img: Path, url: str, token: str) -> Optional[ImageUploaded]:
    if not token.startswith("Bearer "):
        token = f"Bearer {token}"
    headers = {"Authorization": token, "Accept": "application/json"}
    files = {"file": open(img, "rb")}
    logger.info(f"正在上传图片: {img.name}")
    req = requests.post(f"{url}/api/v1/upload", headers=headers, files=files)

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if not req.ok:
        logger.trace(req.content)
        logger.warning(
            f"上传图片失败: HTTP {req.status_code}, reason: {req.reason} "
            f"{res['message'] if 'message' in res else ''}"
        )
        return None
    if not res["status"]:
        logger.warning(f"上传图片失败: {res['message']}")
        return None
    if (
        "data" not in res
        or "links" not in res["data"]
        or "url" not in res["data"]["links"]
    ):
        logger.warning("图片直链获取失败")
        return None
    return ImageUploaded(
        hosting=ImageHosting.LSKY,
        image=img,
        url=res["data"]["links"]["url"],
        thumb=res["data"]["links"].get("thumbnail_url", None),
    )


def get_token(email: str, password: str, url: str) -> str:
    if (email, password) not in tokens:
        session = requests.Session()
        data = {"email": email, "password": password}
        logger.info("正在获取API Token...")
        req = session.post(f"{url}/api/v1/tokens", data=data)
        if not req.ok:
            logger.warning("Lsky Pro登录失败，请重试")
            return
        res = req.json()
        if "data" not in res or "token" not in res["data"]:
            logger.warning("Lsky Pro登录失败，请检查邮箱和密码")
            return
        tokens[(email, password)] = res["data"]["token"]
    return tokens[(email, password)]
