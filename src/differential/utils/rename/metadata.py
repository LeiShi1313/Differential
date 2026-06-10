import re
from typing import Optional, Tuple

from differential.utils.ptgen.base import DataType, PTGenData
from differential.utils.ptgen.douban import DoubanData
from differential.utils.ptgen.imdb import IMDBData
from differential.utils.ptgen_handler import PTGenHandler
from differential.utils.rename.models import RenameMetadata


ASCII_RE = re.compile(r"[A-Za-z]")


def manual_metadata(title: str, year, season: str = "", episode: str = "") -> RenameMetadata:
    return RenameMetadata(
        title=str(title or "").strip(),
        year=str(year or "").strip(),
        kind="tv" if season or episode else "movie",
        season=normalize_season(season),
        episode=normalize_episode(episode),
    )


def fetch_url_metadata(url: str) -> Tuple[RenameMetadata, PTGenData, Optional[DoubanData], Optional[IMDBData]]:
    handler = PTGenHandler(url=url)
    ptgen, douban, imdb = handler.fetch_ptgen_info()
    return metadata_from_ptgen(ptgen, douban, imdb), ptgen, douban, imdb


def metadata_from_ptgen(
    ptgen: PTGenData,
    douban: Optional[DoubanData] = None,
    imdb: Optional[IMDBData] = None,
    season: str = "",
    episode: str = "",
) -> RenameMetadata:
    title = choose_title(ptgen, douban, imdb)
    year = choose_year(ptgen, douban, imdb)
    kind = choose_kind(ptgen, douban, imdb, season, episode)
    return RenameMetadata(
        title=title,
        year=year,
        kind=kind,
        season=normalize_season(season),
        episode=normalize_episode(episode),
    )


def choose_title(
    ptgen: PTGenData,
    douban: Optional[DoubanData] = None,
    imdb: Optional[IMDBData] = None,
) -> str:
    if imdb and imdb.name:
        return str(imdb.name).strip()

    if douban:
        if douban.foreign_title:
            return str(douban.foreign_title).strip()
        for value in list(douban.aka or []) + list(douban.trans_title or []) + list(douban.this_title or []):
            if _looks_english(value):
                return str(value).strip()
        if douban.chinese_title:
            return str(douban.chinese_title).strip()

    text = str(ptgen or "").strip()
    if text and not text.startswith("Unknown"):
        return text
    return ""


def choose_year(
    ptgen: PTGenData,
    douban: Optional[DoubanData] = None,
    imdb: Optional[IMDBData] = None,
) -> str:
    for value in (
        getattr(imdb, "year", None),
        getattr(douban, "year", None),
        getattr(ptgen, "year", None),
    ):
        if value:
            match = re.search(r"(?:18|19|20|21)\d{2}", str(value))
            if match:
                return match.group(0)
            return str(value).strip()
    return ""


def choose_kind(
    ptgen: PTGenData,
    douban: Optional[DoubanData] = None,
    imdb: Optional[IMDBData] = None,
    season: str = "",
    episode: str = "",
) -> str:
    if season or episode:
        return "tv"
    for data in (imdb, douban, ptgen):
        data_type = getattr(data, "type_", None)
        if data_type == DataType.TV_SERIES:
            return "tv"
        if data_type == DataType.MOVIE:
            return "movie"
    if douban and getattr(douban, "episodes", None):
        return "tv"
    return "movie"


def normalize_season(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"(\d{1,2})", text)
    if match:
        return f"S{int(match.group(1)):02d}"
    return text.upper()


def normalize_episode(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"(\d{1,3})", text)
    if match:
        return f"E{int(match.group(1)):02d}"
    return text.upper()


def _looks_english(value: str) -> bool:
    text = str(value or "")
    return bool(ASCII_RE.search(text))
