import base64
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests

from differential.constants import URL_SHORTENER_PATH


TORRENT_UPLOAD_ENDPOINT = f"{URL_SHORTENER_PATH}/torrent"
TORRENT_CONTENT_TYPE = "application/x-bittorrent"


def torrent_file_to_base64(path: Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def upload_torrent(path: Path, endpoint: str = TORRENT_UPLOAD_ENDPOINT, timeout: int = 30) -> str:
    path = Path(path)
    response = requests.post(
        endpoint,
        data=path.read_bytes(),
        headers={"content-type": TORRENT_CONTENT_TYPE},
        timeout=timeout,
    )
    response.raise_for_status()
    return _extract_torrent_url(response, _service_base_url(endpoint))


def _service_base_url(endpoint: str) -> str:
    return endpoint.rstrip("/").removesuffix("/torrent")


def _extract_torrent_url(response: requests.Response, base_url: str) -> str:
    value = _url_value_from_json(response) or response.text.strip()
    url = _normalize_torrent_url(value, base_url)
    if not url:
        raise RuntimeError("torrent upload response did not include a torrent URL")
    return url


def _url_value_from_json(response: requests.Response) -> Optional[str]:
    try:
        data = response.json()
    except ValueError:
        return None
    return _url_value_from_data(data)


def _url_value_from_data(data: Any) -> Optional[str]:
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return None

    for key in (
        "torrentUrl",
        "torrent_url",
        "downloadUrl",
        "download_url",
        "url",
        "href",
        "path",
        "id",
        "key",
        "token",
    ):
        value = data.get(key)
        if value:
            return str(value)

    nested = data.get("data")
    if nested is not None:
        return _url_value_from_data(nested)
    return None


def _normalize_torrent_url(value: str, base_url: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("/"):
        return urljoin(f"{base_url.rstrip('/')}/", value.lstrip("/"))
    if value.startswith("torrent/"):
        return urljoin(f"{base_url.rstrip('/')}/", value)
    return f"{base_url.rstrip('/')}/torrent/{value}"
