import re
from pathlib import Path
from typing import Optional, List

import requests
from loguru import logger

from differential.constants import ImageHosting
from differential.utils.image.types import ImageUploaded

# TODO
'''
curl 'https://byr.pt/uploadimage.php' \
  -H 'accept: */*' \
  -H 'accept-language: en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh-TW;q=0.6,zh-HK;q=0.5,zh;q=0.4' \
  -H 'cache-control: no-cache' \
  -H 'content-type: multipart/form-data; boundary=----WebKitFormBoundarygRHsEgLAfIfe4S9U' \
  -b 'auth_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJuYmYiOjE3NDAzMjIxMjYuNTg3NTI0LCJleHAiOjE3NDAzMjMwMjYuNTg3NTcyLCJqdGkiOiJjNGJlYzJjOS05MTVlLTQwMDktYThjZi0yZWVjYzA3ZjMyMGMiLCJpYXQiOjE3NDAzMjIxMjYuNTg3NTI0LCJpc3MiOiJzZXNzaW9uIiwiYXVkIjoiYWU5NTNkMTQtYmM5NC00MGU3LWIyM2UtOTc2Y2Q4YTQyMmI0Iiwic3ViIjoiMzQ4MzU4In0.6ErGJ-w5W0i0HYXn9q7rnyw4lWpmaenKhnVsC2uEpvI; session_id=ae953d14-bc94-40e7-b23e-976cd8a422b4; refresh_token=415f22cb5b989416d3d428ccb1e276d341e5dfd8a3a496e664fafb9ab1d7c7e6' \
  -H 'dnt: 1' \
  -H 'origin: https://byr.pt' \
  -H 'pragma: no-cache' \
  -H 'priority: u=1, i' \
  -H 'referer: https://byr.pt/upload.php' \
  -H 'sec-ch-ua: "Chromium";v="133", "Not(A:Brand";v="99"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36' \
  --data-raw $'------WebKitFormBoundarygRHsEgLAfIfe4S9U\r\nContent-Disposition: form-data; name="file"; filename="00839uABgy1hqs8jueiqzj32553717rh.jpg"\r\nContent-Type: image/jpeg\r\n\r\n\r\n------WebKitFormBoundarygRHsEgLAfIfe4S9U\r\nContent-Disposition: form-data; name="type"\r\n\r\ntorrent\r\n------WebKitFormBoundarygRHsEgLAfIfe4S9U--\r\n'
  '''

def byr_upload(images: List[Path], cookie: Optional[str], url: Optional[str] = None) -> List[ImageUploaded]:
    if not cookie:
        logger.error("[Screenshots] 未设置byr_cookie")
        return []
    if url and url.endswith("/"):
        url = url[:-1]
    
    uploaded = []
    for img in images:
        if cached := ImageUploaded.from_pickle(img, ImageHosting.BYR):
            uploaded.append(cached)
        elif u := _byr_upload(img, cookie, url):
            uploaded.append(u)
    return uploaded

def _byr_upload(img: Path, cookie: str, url: Optional[str] = None) -> Optional[ImageUploaded]:
    headers = {'cookie': cookie}
    data = {'type': 'torrent'}
    files = {'file': open(img, 'rb')}

    req = requests.post(f"{'https://byr.pt' if not url else url}/uploadimage.php", data=data, files=files, headers=headers)

    if not req.ok:
        logger.trace(req.content)
        logger.warning(f"上传图片失败: HTTP {req.status_code}, reason: {req.reason}")
        return None

    try:
        res = req.json()
        logger.trace(res)
    except json.decoder.JSONDecodeError:
        res = {}
    if location := res.get('location'):
        return ImageUploaded(hosting=ImageHosting.BYR, image=img, url=f"https://byr.pt{location}")
    logger.warning("[Screenshots] 上传图片失败: 未获取到图片地址")
