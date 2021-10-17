import json
from pathlib import Path
from typing import Optional

import requests
from loguru import logger


def ptpimg_upload(img: Path, api_key: str) -> Optional[str]:
    data = {'api_key': api_key}
    files = {'file-upload[0]': open(img, 'rb')}
    req = requests.post('https://ptpimg.me/upload.php', data=data, files=files)

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if not req.ok:
        logger.trace(req.content)
        logger.warning(
            f"上传图片失败: HTTP {req.status_code}, reason: {req.reason}")
        return None
    if len(res) < 1 or 'code' not in res[0] or 'ext' not in res[0]:
        logger.warning(f"图片直链获取失败")
        return None
    return f"https://ptpimg.me/{res[0].get('code')}.{res[0].get('ext')}"