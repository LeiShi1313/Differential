import re
from pathlib import Path
from typing import Optional

import requests
from loguru import logger

from differential.utils.image import ImageUploaded


def byr_upload(img: Path, authorization: str, url: Optional[str] = None) -> Optional[ImageUploaded]:
    headers = {'authorization': f'{authorization if authorization.startswith("Basic") else "Basic "+authorization}'}
    params = {'command': 'QuickUpload', 'type': 'Images', 'CKEditor': 'descr', 'CKEditorFuncNum': 2}
    files = {'upload': open(img, 'rb')}

    req = requests.post(f"{'https://byr.pt' if not url else url}/ckfinder/core/connector/php/connector.php", params=params, files=files, headers=headers)

    if not req.ok:
        logger.trace(req.content)
        logger.warning(f"上传图片失败: HTTP {req.status_code}, reason: {req.reason}")
        return None
    if url:
        m = re.search(r"\'({}.*?)\'".format(url), req.text)
    else:
        m = re.search(r"\'(https://byr.usx.leishi.io.*?)\'", req.text)
    if not m:
        logger.trace(req.content)
        logger.warning(f"图片直链获取失败")
        return None
    return ImageUploaded(m.groups()[0])
