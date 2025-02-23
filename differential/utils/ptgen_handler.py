import requests
from loguru import logger
from typing import Optional, Union

from differential.utils.ptgen.base import PTGenData
from differential.utils.ptgen.imdb import IMDBData
from differential.utils.ptgen.douban import DoubanData
from differential.utils.ptgen.parser import parse_ptgen

class PTGenHandler:
    """
    Handles fetching information from PTGen (and optionally IMDB).
    """

    def __init__(self, url: str, ptgen_url: str, second_ptgen_url: str, ptgen_retry: int):
        self.url = url
        self.ptgen_url = ptgen_url
        self.second_ptgen_url = second_ptgen_url
        self.ptgen_retry = ptgen_retry

        self._ptgen: Optional[PTGenData] = None
        self._douban: Optional[DoubanData] = None
        self._imdb: Optional[IMDBData] = None

    def fetch_ptgen_info(self):
        """
        Public method to fetch PTGen (and optional IMDB) data,
        with retry logic switching between ptgen_url and second_ptgen_url.
        """
        attempts_left = 2 * self.ptgen_retry
        while attempts_left > 0:
            use_second = attempts_left <= self.ptgen_retry
            self._ptgen = self._request_ptgen_info(use_second=use_second)
            if self._ptgen.success:
                return (self._ptgen, self._douban, self._imdb)
            attempts_left -= 1

        return (self._ptgen, self._douban, self._imdb)

    def _request_ptgen_info(self, use_second: bool = False) -> PTGenData:
        ptgen_url = self.second_ptgen_url if use_second else self.ptgen_url
        logger.debug(f"[PTGen] 正在从 {ptgen_url} 获取 {self.url}")
        params = {"url": self.url}

        try:
            resp = requests.get(ptgen_url, params=params, timeout=15)
            if not resp.ok:
                logger.trace(resp.content)
                logger.warning(f"[PTGen] HTTP {resp.status_code} - {resp.reason}")
                return PTGenData()

            ptgen = parse_ptgen(resp.json())
            if not ptgen.success:
                logger.trace(resp.json())
                logger.warning(f"[PTGen] 获取失败: {ptgen.error}")
                return ptgen
            
            if ptgen.site != "imdb":
                if ptgen.site == 'douban':
                    self._douban = ptgen
                if hasattr(ptgen, "imdb_link"):
                    self._imdb = self._try_fetch_imdb(ptgen.imdb_link)
            else:
                self._imdb = ptgen

            logger.info(f"[PTGen] 获取成功: {ptgen}")
            return ptgen
        except requests.RequestException as e:
            logger.warning(f"[PTGen] 请求异常: {e}")
            return PTGenData()

    def _try_fetch_imdb(self, imdb_link: str) -> IMDBData:
        """
        Attempt to fetch IMDB info from PTGen for the provided IMDB link.
        Returns a dict or empty if failed.
        """
        try:
            req = requests.get(self.ptgen_url, params={"url": imdb_link}, timeout=15)
            if req.ok and req.json().get("success"):
                return IMDBData.from_dict(req.json())
        except Exception as e:
            logger.warning(f"[IMDB] 请求异常: {e}")
        return IMDBData()