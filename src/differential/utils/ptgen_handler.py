from loguru import logger
from typing import Any, Dict, Optional, Sequence

from differential.utils.ptgen.base import PTGenData
from differential.utils.ptgen.imdb import IMDBData
from differential.utils.ptgen.douban import DoubanData
from differential.utils.ptgen.formatter import build_ptgen_format
from differential.utils.ptgen.parser import parse_ptgen
from differential.utils.ptgen.providers import (
    DEFAULT_PTGEN_PROVIDERS,
    PTGenProvider,
    PTGenProviderError,
)
from differential.utils.ptgen.reference import PTGenReference, parse_ptgen_reference

import requests


FAILURE_FORMAT = "PTGen获取失败，请自行获取相关内容"


def normalize_ptgen_payload(data: Dict[str, Any], reference: PTGenReference) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise PTGenProviderError("provider returned non-object JSON")

    payload = dict(data)
    site = str(payload.get("site") or reference.site)
    sid = str(payload.get("sid") or reference.sid)

    if site != reference.site or sid != reference.sid:
        raise PTGenProviderError(
            f"provider returned mismatched data: expected {reference.site}/{reference.sid}, got {site}/{sid}"
        )

    if payload.get("success") is False:
        raise PTGenProviderError(payload.get("error") or "provider returned success=false")

    payload["site"] = site
    payload["sid"] = sid
    payload["success"] = True if payload.get("success") is None else payload["success"]
    payload["format"] = build_ptgen_format(payload)
    return payload

class PTGenHandler:
    """
    Handles fetching information from PtGen archive providers.
    """

    def __init__(
        self,
        url: str,
        providers: Sequence[PTGenProvider] = DEFAULT_PTGEN_PROVIDERS,
        timeout: int = 15,
    ):
        self.url = url
        self.providers = tuple(providers)
        self.timeout = timeout
        self.session = requests.Session()

        self._ptgen: Optional[PTGenData] = None
        self._douban: Optional[DoubanData] = None
        self._imdb: Optional[IMDBData] = None

    def fetch_ptgen_info(self):
        """
        Public method to fetch PtGen data and optional IMDB data.
        """
        reference = parse_ptgen_reference(self.url)
        if not reference:
            self._ptgen = PTGenData(
                success=False,
                error=f"不支持的PTGen链接: {self.url}",
                format=FAILURE_FORMAT,
            )
            logger.warning(f"[PTGen] 不支持的链接: {self.url}")
            return (self._ptgen, self._douban, self._imdb)

        return self.fetch_ptgen_reference(reference)

    def fetch_ptgen_reference(self, reference: PTGenReference):
        """
        Fetch PtGen data from an already-selected reference.
        """
        self.url = reference.original_url
        self._ptgen = None
        self._douban = None
        self._imdb = None

        self._ptgen = self._request_ptgen_info(reference)
        if self._ptgen.success:
            if self._ptgen.site != "imdb":
                if self._ptgen.site == "douban":
                    self._douban = self._ptgen
                imdb_link = getattr(self._ptgen, "imdb_link", None)
                if imdb_link:
                    self._imdb = self._try_fetch_imdb(imdb_link)
            else:
                self._imdb = self._ptgen
        return (self._ptgen, self._douban, self._imdb)

    def _request_ptgen_info(self, reference: PTGenReference) -> PTGenData:
        last_error = ""
        for provider in self.providers:
            logger.debug(
                f"[PTGen] 正在从 {provider.name} 获取 {reference.site}/{reference.sid}"
            )
            try:
                raw_data = provider.fetch(reference, self.session, self.timeout)
                payload = normalize_ptgen_payload(raw_data, reference)
                ptgen = parse_ptgen(payload)
                if not ptgen.success:
                    last_error = ptgen.error or "PTGen解析失败"
                    logger.warning(f"[PTGen] {provider.name} 获取失败: {last_error}")
                    continue

                logger.info(f"[PTGen] {provider.name} 获取成功: {ptgen}")
                return ptgen
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[PTGen] {provider.name} 获取失败: {last_error}")

        return PTGenData(
            site=reference.site,
            sid=reference.sid,
            success=False,
            error=last_error or "所有PTGen provider均获取失败",
            format=FAILURE_FORMAT,
        )

    def _try_fetch_imdb(self, imdb_link: str) -> IMDBData:
        """
        Attempt to fetch IMDB info from PtGen providers for the provided IMDB link.
        """
        reference = parse_ptgen_reference(imdb_link)
        if not reference:
            logger.warning(f"[IMDB] 不支持的链接: {imdb_link}")
            return IMDBData(format=FAILURE_FORMAT)

        ptgen = self._request_ptgen_info(reference)
        if isinstance(ptgen, IMDBData):
            return ptgen

        return IMDBData(
            site=reference.site,
            sid=reference.sid,
            success=False,
            error=ptgen.error,
            format=ptgen.format or FAILURE_FORMAT,
        )
