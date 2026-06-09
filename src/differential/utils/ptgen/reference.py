import re
from dataclasses import dataclass
from typing import Optional, Pattern, Tuple


@dataclass(frozen=True)
class PTGenReference:
    site: str
    sid: str
    original_url: str


_REFERENCE_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
    (
        "douban_celebrity",
        re.compile(
            r"(?:https?://)?movie\.douban\.com/celebrity/(?P<sid>\d+)/?",
            re.IGNORECASE,
        ),
    ),
    (
        "douban_personage",
        re.compile(
            r"(?:https?://)?www\.douban\.com/personage/(?P<sid>\d+)/?",
            re.IGNORECASE,
        ),
    ),
    (
        "douban",
        re.compile(
            r"(?:https?://)?(?:(?:movie|www)\.)?douban\.com/(?:subject|movie)/(?P<sid>\d+)/?",
            re.IGNORECASE,
        ),
    ),
    (
        "imdb",
        re.compile(
            r"(?:https?://)?(?:www\.)?imdb\.com/title/(?P<sid>tt\d+)",
            re.IGNORECASE,
        ),
    ),
    (
        "bangumi",
        re.compile(
            r"(?:https?://)?(?:bgm\.tv|bangumi\.tv|chii\.in)/subject/(?P<sid>\d+)/?",
            re.IGNORECASE,
        ),
    ),
    (
        "steam",
        re.compile(
            r"(?:https?://)?(?:(?:store\.)?steampowered|steamcommunity)\.com/app/(?P<sid>\d+)/?",
            re.IGNORECASE,
        ),
    ),
    (
        "indienova",
        re.compile(
            r"(?:https?://)?indienova\.com/game/(?P<sid>[^/?#]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "epic",
        re.compile(
            r"(?:https?://)?www\.epicgames\.com/store/[a-zA-Z-]+/product/(?P<sid>[^/?#]+)/?",
            re.IGNORECASE,
        ),
    ),
)


def parse_ptgen_reference(url: str) -> Optional[PTGenReference]:
    candidate = (url or "").strip()
    for site, pattern in _REFERENCE_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return PTGenReference(
                site=site,
                sid=match.group("sid").rstrip("/"),
                original_url=url,
            )
    return None
