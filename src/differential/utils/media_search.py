import html
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
from urllib.parse import quote, urljoin

import requests

from differential.utils.media_name import ParsedMediaName
from differential.utils.ptgen.reference import PTGenReference


DEFAULT_MEDIA_SEARCH_BASE_URL = "https://ptgen.leishi.xyz"
DEFAULT_MEDIA_SEARCH_FIELDS = "title_aliases"
PTGEN_SEARCH_FIELDS = (
    "all",
    "titles",
    "aliases",
    "title_aliases",
    "people",
    "source_ids",
    "metadata",
)


class MediaSearchError(Exception):
    pass


class MediaSelectionError(Exception):
    pass


def normalize_ptgen_fields(fields: Optional[str]) -> Optional[str]:
    value = str(fields or "").strip()
    if not value:
        return None
    parts = [part.strip() for part in value.split(",") if part.strip()]
    invalid = [part for part in parts if part not in PTGEN_SEARCH_FIELDS]
    if invalid:
        valid = ", ".join(PTGEN_SEARCH_FIELDS)
        raise MediaSearchError(f"unsupported PtGen search fields: {', '.join(invalid)}; valid values: {valid}")
    return ",".join(parts)


@dataclass
class MediaSearchResult:
    id: str
    kind: str
    sources: List[str] = field(default_factory=list)
    source_ids: Dict[str, str] = field(default_factory=dict)
    titles: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    year: Optional[int] = None
    release_date: str = ""
    genres: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    cast: List[str] = field(default_factory=list)
    rating_score: Optional[float] = None
    rating_votes: Optional[int] = None
    description: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_hit(cls, hit: Dict[str, Any]) -> "MediaSearchResult":
        return cls(
            id=str(hit.get("id") or ""),
            kind=str(hit.get("kind") or ""),
            sources=_string_list(hit.get("sources")),
            source_ids={str(k): str(v) for k, v in (hit.get("source_ids") or {}).items() if v},
            titles=_string_list(hit.get("titles")),
            aliases=_string_list(hit.get("aliases")),
            year=_optional_int(hit.get("year")),
            release_date=str(hit.get("release_date") or ""),
            genres=_string_list(hit.get("genres")),
            people=_string_list(hit.get("people")),
            directors=_string_list(hit.get("directors")),
            cast=_string_list(hit.get("cast")),
            rating_score=_optional_float(hit.get("rating_score")),
            rating_votes=_optional_int(hit.get("rating_votes")),
            description=str(hit.get("description") or ""),
            raw=hit,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "sources": self.sources,
            "source_ids": self.source_ids,
            "titles": self.titles,
            "aliases": self.aliases,
            "year": self.year,
            "release_date": self.release_date,
            "genres": self.genres,
            "people": self.people,
            "directors": self.directors,
            "cast": self.cast,
            "rating_score": self.rating_score,
            "rating_votes": self.rating_votes,
            "description": self.description,
        }

    @property
    def display_title(self) -> str:
        return self.titles[0] if self.titles else self.id

    @property
    def matchable_titles(self) -> List[str]:
        return _unique_texts(self.titles + self.aliases)


class MediaSearchClient:
    def __init__(
        self,
        base_url: str = DEFAULT_MEDIA_SEARCH_BASE_URL,
        timeout: int = 15,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.session = session or requests.Session()

    def search(
        self,
        q: str,
        limit: int = 10,
        offset: int = 0,
        kind: Optional[str] = None,
        year: Optional[int] = None,
        source: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> List[MediaSearchResult]:
        params: Dict[str, Any] = {
            "q": q,
            "limit": max(1, min(int(limit), 100)),
            "offset": max(0, int(offset)),
        }
        if kind:
            params["kind"] = kind
        if year is not None:
            params["year"] = year
        if source:
            params["source"] = source
        normalized_fields = normalize_ptgen_fields(fields)
        if normalized_fields:
            params["fields"] = normalized_fields

        try:
            response = self.session.get(
                urljoin(self.base_url, "api/search"),
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise MediaSearchError(f"media search request failed: {exc}") from exc
        if not response.ok:
            raise MediaSearchError(
                f"media search HTTP {response.status_code}: {response.reason}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise MediaSearchError("media search returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise MediaSearchError("media search returned non-object JSON")
        if data.get("message") == "index is still building":
            raise MediaSearchError("media search index is still building")

        hits = data.get("hits") or []
        if not isinstance(hits, list):
            raise MediaSearchError("media search response has invalid hits")
        return [MediaSearchResult.from_hit(hit) for hit in hits if isinstance(hit, dict)]

    def search_parsed(
        self,
        parsed: ParsedMediaName,
        limit: int = 10,
        ptgen_source: Optional[str] = None,
        ptgen_fields: str = DEFAULT_MEDIA_SEARCH_FIELDS,
        search_hint: str = "",
        search_query: str = "",
    ) -> List[MediaSearchResult]:
        candidates = _searchable_parsed_titles(parsed)
        collected: Dict[str, MediaSearchResult] = {}
        order: Dict[str, int] = {}

        for query in _search_queries(candidates[:5], search_hint, search_query):
            query_results: List[MediaSearchResult] = []
            for kind in _kind_attempts(parsed.kind_hint):
                for year in _year_attempts(parsed, kind):
                    try:
                        hits = self.search(
                            query,
                            limit=limit,
                            kind=kind,
                            year=year,
                            source=ptgen_source,
                            fields=ptgen_fields,
                        )
                    except MediaSearchError:
                        raise
                    for hit in hits:
                        if hit.id and hit.id not in collected:
                            order[hit.id] = len(order)
                            collected[hit.id] = hit
                            query_results.append(hit)
            if _has_confident_candidate(query_results, parsed):
                break

        ranked = list(collected.values())
        ranked.sort(key=lambda result: (-score_media_result(result, parsed), order.get(result.id, 0)))
        ranked = _dedupe_equivalent_results(ranked)
        return ranked[:limit]


def select_media_result(
    results: Sequence[MediaSearchResult],
    parsed: ParsedMediaName,
    non_interactive: bool = False,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> MediaSearchResult:
    if not results:
        raise MediaSelectionError("no media search results")
    if non_interactive:
        return auto_select_media_result(results, parsed)

    output_func("Media search matches:")
    for idx, result in enumerate(results, start=1):
        output_func(format_media_result(result, idx, parsed))

    while True:
        choice = input_func(f"Select media [1-{len(results)}, q to abort]: ").strip()
        if choice.lower() in {"q", "quit", "exit"}:
            raise MediaSelectionError("media selection aborted")
        if choice.isdigit():
            selected = int(choice)
            if 1 <= selected <= len(results):
                return results[selected - 1]
        output_func("Invalid selection.")


def auto_select_media_result(
    results: Sequence[MediaSearchResult],
    parsed: ParsedMediaName,
) -> MediaSearchResult:
    ranked = _dedupe_equivalent_results(
        sorted(results, key=lambda result: score_media_result(result, parsed), reverse=True)
    )
    if not ranked:
        raise MediaSelectionError("no media search results")

    top = ranked[0]
    top_score = score_media_result(top, parsed)
    runner_up_score = score_media_result(ranked[1], parsed) if len(ranked) > 1 else -999

    if not _has_exact_title(top, parsed):
        raise MediaSelectionError(_ambiguous_message("top result title is not an exact match", ranked, parsed))
    if parsed.year is not None and top.year != parsed.year:
        raise MediaSelectionError(_ambiguous_message("top result year does not match", ranked, parsed))
    if parsed.kind_hint and not _kind_matches(parsed.kind_hint, top.kind):
        raise MediaSelectionError(_ambiguous_message("top result kind does not match", ranked, parsed))
    if top_score < 80 or top_score - runner_up_score < 15:
        raise MediaSelectionError(_ambiguous_message("media match is ambiguous", ranked, parsed))

    return top


def result_to_ptgen_reference(result: MediaSearchResult) -> PTGenReference:
    for source in _source_preference(result.kind):
        sid = result.source_ids.get(source)
        if sid:
            return PTGenReference(source, sid, source_url(source, sid) or result.id)

    for source in result.sources:
        sid = result.source_ids.get(source)
        if sid:
            return PTGenReference(source, sid, source_url(source, sid) or result.id)

    if "-" in result.id:
        source, sid = result.id.split("-", 1)
        return PTGenReference(source, sid, source_url(source, sid) or result.id)

    raise MediaSelectionError(f"cannot build PtGen reference from result: {result.id}")


def source_url(source: str, sid: str) -> str:
    if source == "douban":
        return f"https://movie.douban.com/subject/{quote(sid)}/"
    if source == "imdb":
        return f"https://www.imdb.com/title/{quote(sid)}/"
    if source == "bangumi":
        return f"https://bgm.tv/subject/{quote(sid)}/"
    if source == "steam":
        return f"https://store.steampowered.com/app/{quote(sid)}/"
    if source == "epic":
        return f"https://www.epicgames.com/store/product/{quote(sid)}/"
    if source == "indienova":
        return f"https://indienova.com/game/{quote(sid)}"
    return ""


def format_media_result(
    result: MediaSearchResult,
    index: int,
    parsed: Optional[ParsedMediaName] = None,
) -> str:
    titles = result.display_title
    aliases = [title for title in result.matchable_titles if title != result.display_title]
    if aliases:
        titles = f"{titles} / {' / '.join(aliases[:2])}"

    score = f" score={score_media_result(result, parsed)}" if parsed else ""
    rating = ""
    if result.rating_score is not None:
        votes = f", {result.rating_votes} votes" if result.rating_votes else ""
        rating = f" rating={result.rating_score}{votes}"
    people = _unique_texts(result.directors + result.cast + result.people)
    people_text = f" people={', '.join(people[:4])}" if people else ""
    ids = ", ".join(f"{source}:{sid}" for source, sid in result.source_ids.items())
    ids_text = f" ids=[{ids}]" if ids else ""
    year = result.year if result.year is not None else "?"
    kind = result.kind or "?"
    return f"{index}. {titles} ({year}, {kind}) [{result.id}]{ids_text}{rating}{people_text}{score}"


def score_media_result(result: MediaSearchResult, parsed: Optional[ParsedMediaName]) -> int:
    if not parsed:
        return 0

    score = 0
    parsed_keys = {_match_key(title) for title in _matchable_parsed_titles(parsed)}
    result_keys = {_match_key(title) for title in result.matchable_titles if title}

    if parsed_keys & result_keys:
        score += 60
    elif any(_loose_title_match(parsed_key, result_key) for parsed_key in parsed_keys for result_key in result_keys):
        score += 35

    if parsed.year is not None:
        if result.year == parsed.year:
            score += 25
        elif result.year is not None and abs(result.year - parsed.year) == 1:
            score += 8
        elif result.year is not None:
            score -= 35

    if parsed.kind_hint:
        if _kind_matches(parsed.kind_hint, result.kind):
            score += 15
        elif result.kind:
            score -= 15

    score += _season_match_score(result, parsed)

    for idx, source in enumerate(_source_preference(result.kind)):
        if source in result.source_ids:
            score += max(1, 6 - idx)
            break

    if result.rating_votes:
        score += min(5, int(math.log10(max(result.rating_votes, 1))))

    return score


def _kind_attempts(kind_hint: Optional[str]) -> List[Optional[str]]:
    if kind_hint == "tv":
        return ["tv", "anime", None]
    if kind_hint == "movie":
        return ["movie", None]
    return [None]


def _year_attempts(parsed: ParsedMediaName, kind: Optional[str]) -> List[Optional[int]]:
    years: List[Optional[int]] = [parsed.year]
    if parsed.kind_hint == "tv" or kind == "anime":
        years.append(None)
    return _unique_values(years)


def _search_queries(
    candidates: Sequence[str],
    search_hint: str,
    search_query: str = "",
) -> List[str]:
    override = str(search_query or "").strip()
    if override:
        return [override]

    hint = str(search_hint or "").strip()
    queries = []
    for candidate in candidates:
        title = str(candidate or "").strip()
        if not title:
            continue
        query = f"{title} {hint}".strip() if hint else title
        queries.append(query)
    return _unique_texts(queries)


def _source_preference(kind: str) -> List[str]:
    if kind == "anime":
        return ["bangumi", "douban", "imdb"]
    if kind == "game":
        return ["steam", "epic", "indienova"]
    return ["douban", "imdb", "bangumi", "steam", "epic", "indienova"]


def _kind_matches(kind_hint: str, result_kind: str) -> bool:
    if not result_kind or result_kind == "work":
        return True
    if kind_hint == result_kind:
        return True
    return kind_hint == "tv" and result_kind == "anime"


def _has_exact_title(result: MediaSearchResult, parsed: ParsedMediaName) -> bool:
    parsed_keys = {_match_key(title) for title in _matchable_parsed_titles(parsed)}
    result_keys = {_match_key(title) for title in result.matchable_titles if title}
    return bool(parsed_keys & result_keys) or _has_season_title_match(result, parsed, parsed_keys)


def _has_confident_candidate(
    results: Sequence[MediaSearchResult],
    parsed: ParsedMediaName,
) -> bool:
    for result in results:
        if not _has_exact_title(result, parsed):
            continue
        if parsed.year is not None and result.year != parsed.year:
            continue
        if parsed.kind_hint and not _kind_matches(parsed.kind_hint, result.kind):
            continue
        if score_media_result(result, parsed) >= 80:
            return True
    return False


def _loose_title_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    shorter, longer = sorted((left, right), key=len)
    return len(shorter) >= 5 and shorter in longer


def _ambiguous_message(
    reason: str,
    results: Sequence[MediaSearchResult],
    parsed: ParsedMediaName,
) -> str:
    summary = "\n".join(format_media_result(result, idx, parsed) for idx, result in enumerate(results[:5], start=1))
    return f"{reason}; refusing non-interactive auto-selection.\n{summary}"


def _string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [html.unescape(str(item)) for item in value if item]
    if value:
        return [html.unescape(str(value))]
    return []


def _optional_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique_texts(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        text = html.unescape(str(value or "")).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _unique_values(values: Iterable[Any]) -> List[Any]:
    result: List[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _searchable_parsed_titles(parsed: ParsedMediaName) -> List[str]:
    values = list(parsed.title_candidates or [])
    if parsed.title:
        values.append(parsed.title)
    return _unique_texts(title for title in values if _is_useful_parsed_title(title, parsed))


def _matchable_parsed_titles(parsed: ParsedMediaName) -> List[str]:
    values = [parsed.primary_search_title, parsed.title] + list(parsed.title_candidates or [])
    return _unique_texts(title for title in values if _is_useful_parsed_title(title, parsed))


def _is_useful_parsed_title(title: str, parsed: ParsedMediaName) -> bool:
    text = str(title or "").strip()
    key = _match_key(text)
    if not key:
        return False

    protected_keys = {
        _match_key(value)
        for value in (parsed.primary_search_title, parsed.title)
        if value
    }
    if key in protected_keys:
        return True

    if re.fullmatch(r"(?:18|19|20|21)\d{2}", key):
        return False
    if parsed.year_text and key == _match_key(parsed.year_text):
        return False
    if key in {"complete", "proper", "repack", "rerip"}:
        return False
    if re.fullmatch(r"s\d{1,2}(?:e\d{1,3})?|e\d{1,3}|v\d+", key):
        return False

    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    release_noise = {
        "1080p",
        "1080i",
        "2160p",
        "720p",
        "aac",
        "ac3",
        "atmos",
        "avc",
        "bluray",
        "complete",
        "ddp",
        "dts",
        "dv",
        "h264",
        "h265",
        "hdr",
        "hevc",
        "remux",
        "uhd",
        "webdl",
        "webrip",
        "x264",
        "x265",
    }
    if any(token in release_noise for token in tokens):
        return False
    return True


def _dedupe_equivalent_results(results: Sequence[MediaSearchResult]) -> List[MediaSearchResult]:
    deduped: List[MediaSearchResult] = []
    for result in results:
        if any(_equivalent_media_result(result, existing) for existing in deduped):
            continue
        deduped.append(result)
    return deduped


def _equivalent_media_result(left: MediaSearchResult, right: MediaSearchResult) -> bool:
    if left.id and left.id == right.id:
        return True
    for source, sid in left.source_ids.items():
        if sid and right.source_ids.get(source) == sid:
            return True
    if left.year is not None and left.year == right.year and _result_kinds_compatible(left.kind, right.kind):
        shared_title_keys = {
            _match_key(title)
            for title in left.matchable_titles
            if title
        } & {
            _match_key(title)
            for title in right.matchable_titles
            if title
        }
        if any(len(key) >= 8 for key in shared_title_keys):
            return True
    return False


def _result_kinds_compatible(left: str, right: str) -> bool:
    if not left or not right or left == right:
        return True
    return {left, right} == {"tv", "anime"}


def _season_match_score(result: MediaSearchResult, parsed: ParsedMediaName) -> int:
    if parsed.season is None:
        return 0
    seasons = _result_seasons(result)
    if not seasons:
        return 0
    return 18 if parsed.season in seasons else -35


def _has_season_title_match(
    result: MediaSearchResult,
    parsed: ParsedMediaName,
    parsed_keys: set[str],
) -> bool:
    if parsed.season is None or parsed.season not in _result_seasons(result):
        return False
    stripped_result_keys = {
        _strip_season_markers_to_key(title)
        for title in result.matchable_titles
        if title
    }
    return bool(parsed_keys & stripped_result_keys)


def _result_seasons(result: MediaSearchResult) -> set[int]:
    seasons: set[int] = set()
    for title in result.matchable_titles:
        seasons.update(_season_numbers_from_text(title))
    return seasons


def _season_numbers_from_text(text: str) -> set[int]:
    seasons: set[int] = set()
    value = str(text or "")
    for match in re.finditer(r"(?i)(?:^|[^A-Za-z0-9])S(\d{1,2})(?![A-Za-z0-9])", value):
        seasons.add(int(match.group(1)))
    for match in re.finditer(r"(?i)\bSeason\s*(\d{1,2})\b", value):
        seasons.add(int(match.group(1)))
    for match in re.finditer(r"(?i)\b(\d{1,2})(?:st|nd|rd|th)\s+season\b", value):
        seasons.add(int(match.group(1)))
    for match in re.finditer(r"第\s*(\d{1,2}|[一二三四五六七八九十]+)\s*季", value):
        season = _chinese_or_int(match.group(1))
        if season:
            seasons.add(season)
    return seasons


def _strip_season_markers_to_key(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"(?i)(?:^|[^A-Za-z0-9])S\d{1,2}(?![A-Za-z0-9])", " ", value)
    value = re.sub(r"(?i)\bSeason\s*\d{1,2}\b", " ", value)
    value = re.sub(r"(?i)\b\d{1,2}(?:st|nd|rd|th)\s+season\b", " ", value)
    value = re.sub(r"第\s*(?:\d{1,2}|[一二三四五六七八九十]+)\s*季", " ", value)
    return _match_key(value)


def _chinese_or_int(value: str) -> int:
    if value.isdigit():
        return int(value)
    digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if value == "十":
        return 10
    if value.startswith("十"):
        return 10 + digits.get(value[-1], 0)
    if value.endswith("十"):
        return digits.get(value[0], 0) * 10
    if "十" in value:
        left, right = value.split("十", 1)
        return digits.get(left, 1) * 10 + digits.get(right, 0)
    return digits.get(value, 0)


def _match_key(title: str) -> str:
    text = html.unescape(str(title or "")).lower()
    text = re.sub(r"&[a-z]+;", " ", text)
    return "".join(ch for ch in text if ch.isalnum())


def results_to_json(
    parsed: ParsedMediaName,
    results: Sequence[MediaSearchResult],
    selected: Optional[MediaSearchResult] = None,
    reference: Optional[PTGenReference] = None,
) -> str:
    payload = {
        "parsed": parsed.to_dict(),
        "results": [result.to_dict() for result in results],
        "selected": selected.to_dict() if selected else None,
        "reference": (
            {
                "site": reference.site,
                "sid": reference.sid,
                "url": reference.original_url,
            }
            if reference
            else None
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
