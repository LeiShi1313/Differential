import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union


PathLike = Union[str, Path]

MEDIA_EXTENSIONS = {
    ".avi",
    ".iso",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpg",
    ".mpeg",
    ".ts",
    ".webm",
    ".wmv",
}

SUBTITLE_EXTENSIONS = {".ass", ".srt", ".ssa", ".sup", ".vtt"}
NON_MEDIA_EXTENSIONS = {".epub", ".log", ".nfo", ".pdf", ".sh", ".txt", ".zip"}

YEAR_RE = re.compile(r"^(?:18|19|20|21)\d{2}$")
SEASON_RE = re.compile(r"^S(?P<season>\d{1,2})(?:E(?P<episode>\d{1,3}))?$", re.IGNORECASE)
RESOLUTION_RE = re.compile(r"^(?:[1-8]\d{2,3}[pi]|4k|8k)$", re.IGNORECASE)
ASCII_RE = re.compile(r"[A-Za-z]")
BRACKET_RE = re.compile(r"[\[\(（【](.*?)[\]\)）】]")

TECH_TOKENS = {
    "aac",
    "ac3",
    "atmos",
    "av1",
    "avc",
    "baha",
    "bd",
    "bdrip",
    "bluray",
    "cr",
    "criterion",
    "dd",
    "ddp",
    "divx",
    "dsnp",
    "dts",
    "dtsx",
    "dv",
    "dvdrip",
    "flac",
    "hdr",
    "hdr10",
    "hdr10plus",
    "hevc",
    "hdtv",
    "hmax",
    "imax",
    "nf",
    "proper",
    "remux",
    "repack",
    "rerip",
    "sdr",
    "subpl",
    "uhd",
    "vc1",
    "web",
    "webdl",
    "webrip",
    "x264",
    "x265",
}

SERVICE_TOKENS = {
    "amzn",
    "atvp",
    "bili",
    "catchplay",
    "cr",
    "dsnp",
    "friday",
    "hamivideo",
    "hmax",
    "iq",
    "iqiyi",
    "it",
    "itunes",
    "kktv",
    "linetv",
    "myvideo",
    "netflix",
    "nf",
    "now",
    "nowplayer",
    "peacock",
    "stan",
    "tving",
    "u-next",
    "viu",
    "wetv",
    "youku",
}

AMBIGUOUS_SERVICE_TOKENS = {"cr", "iq", "it", "now"}

RELEASE_REGION_TOKENS = {
    "aus",
    "bra",
    "can",
    "cc",
    "cee",
    "chn",
    "cz",
    "esp",
    "eur",
    "fra",
    "gbr",
    "ger",
    "hkg",
    "ita",
    "jpn",
    "kor",
    "nld",
    "nor",
    "spa",
    "twn",
    "usa",
}


@dataclass
class ReleaseHints:
    title_candidates: List[str] = field(default_factory=list)
    year: Optional[int] = None
    year_text: str = ""
    season: Optional[int] = None
    season_text: str = ""
    episode: Optional[int] = None
    episode_text: str = ""


@dataclass
class ParsedMediaName:
    raw_name: str
    clean_name: str
    title: str
    title_candidates: List[str] = field(default_factory=list)
    year: Optional[int] = None
    year_text: str = ""
    kind_hint: Optional[str] = None
    season: Optional[int] = None
    season_text: str = ""
    episode: Optional[int] = None
    episode_text: str = ""
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)

    @property
    def primary_search_title(self) -> str:
        return next(iter(self.title_candidates), "") or self.title

    def to_dict(self) -> dict:
        return {
            "raw_name": self.raw_name,
            "clean_name": self.clean_name,
            "title": self.title,
            "primary_search_title": self.primary_search_title,
            "title_candidates": self.title_candidates,
            "year": self.year,
            "year_text": self.year_text,
            "kind_hint": self.kind_hint,
            "season": self.season,
            "season_text": self.season_text,
            "episode": self.episode,
            "episode_text": self.episode_text,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


def parse_media_name(path_or_name: PathLike) -> ParsedMediaName:
    raw_name = _name_from_path(path_or_name)
    stem, suffix = _strip_known_extension(raw_name)
    warnings: List[str] = []
    release_hints = _extract_release_hints(stem)

    if suffix.lower() in NON_MEDIA_EXTENSIONS:
        warnings.append(f"unsupported extension: {suffix}")
    elif suffix.lower() in SUBTITLE_EXTENSIONS:
        warnings.append(f"subtitle file extension: {suffix}")

    bracket_titles = _extract_bracket_titles(stem)
    clean_name = _normalize_release_name(stem)
    tokens = clean_name.split()

    season_index, season, episode = _find_season(tokens)
    tech_index = _find_technical_start(tokens)
    year_index, year = _choose_year(tokens, season_index, tech_index)
    if release_hints.season is not None:
        season = release_hints.season
    if release_hints.episode is not None:
        episode = release_hints.episode
    if release_hints.year is not None:
        year = release_hints.year

    cut_indexes = [idx for idx in (season_index, year_index, tech_index) if idx is not None and idx > 0]
    title_end = min(cut_indexes) if cut_indexes else len(tokens)
    title_tokens = tokens[:title_end]
    title_segment = _clean_title(" ".join(title_tokens))
    candidates = _title_candidates(title_segment, bracket_titles)
    candidates = _unique_titles(candidates + release_hints.title_candidates)
    candidates = _order_title_candidates(candidates, release_hints)
    title = _preferred_title(candidates, release_hints) if candidates else title_segment
    kind_hint = "tv" if season is not None or episode is not None else "movie" if year else None

    if not title:
        warnings.append("could not infer title")
    if year is None:
        warnings.append("could not infer release year")
    if not candidates:
        candidates = [title] if title else []

    return ParsedMediaName(
        raw_name=raw_name,
        clean_name=clean_name,
        title=title,
        title_candidates=candidates,
        year=year,
        year_text=release_hints.year_text or (str(year) if year is not None else ""),
        kind_hint=kind_hint,
        season=season,
        season_text=release_hints.season_text or (f"S{season:02d}" if season is not None else ""),
        episode=episode,
        episode_text=release_hints.episode_text or (f"E{episode:02d}" if episode is not None else ""),
        confidence=_confidence(title, year, kind_hint, warnings),
        warnings=warnings,
    )


def _name_from_path(path_or_name: PathLike) -> str:
    text = str(path_or_name).strip().replace("\\", "/").rstrip("/")
    if not text:
        return ""
    try:
        path_exists = Path(text).exists()
    except OSError:
        path_exists = False
    if text.startswith("/") or re.match(r"^[A-Za-z]:/", text) or path_exists:
        return text.rsplit("/", 1)[-1]
    return text


def _strip_known_extension(name: str) -> tuple[str, str]:
    suffix = Path(name).suffix
    if suffix.lower() in MEDIA_EXTENSIONS | SUBTITLE_EXTENSIONS | NON_MEDIA_EXTENSIONS:
        return name[: -len(suffix)], suffix
    return name, ""


def _extract_release_hints(stem: str) -> ReleaseHints:
    scan_text = _normalize_scan_text(stem)
    year_text, year, year_span = _find_year_text(scan_text)
    season_text, season, episode_text, episode, season_span = _find_season_text(scan_text)
    candidates = _compat_title_candidates(stem, scan_text, year_span, season_span)
    return ReleaseHints(
        title_candidates=candidates,
        year=year,
        year_text=year_text,
        season=season,
        season_text=season_text,
        episode=episode,
        episode_text=episode_text,
    )


def _normalize_scan_text(text: str) -> str:
    text = str(text or "").replace("&apos;", "'")
    text = re.sub(r"\{[^}]*\}", " ", text)
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"[‐‑‒–—]+", "-", text)
    text = re.sub(r"[\"“”‘’]+", "", text)
    text = text.replace("：", ":")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _find_year_text(text: str) -> tuple[str, Optional[int], tuple[int, int]]:
    year_pattern = r"(?:18|19|20)\d{2}"
    range_match = re.search(
        rf"(?<![A-Za-z0-9])({year_pattern})\s*-\s*({year_pattern})(?![A-Za-z0-9])",
        text,
    )
    if range_match:
        year_text = f"{range_match.group(1)}-{range_match.group(2)}"
        return year_text, int(range_match.group(1)), range_match.span(0)

    date_match = re.search(rf"(?<![A-Za-z0-9])({year_pattern})[ .-]\d{{1,2}}[ .-]\d{{1,2}}(?![A-Za-z0-9])", text)
    if date_match:
        return date_match.group(1), int(date_match.group(1)), date_match.span(0)

    matches = list(re.finditer(rf"(?<![A-Za-z0-9])({year_pattern})(?![A-Za-z0-9])", text))
    if not matches:
        return "", None, (-1, -1)

    match = matches[-1] if len(matches) > 1 else matches[0]
    return match.group(1), int(match.group(1)), match.span(1)


def _find_season_text(text: str) -> tuple[str, Optional[int], str, Optional[int], tuple[int, int]]:
    candidates: List[tuple[int, int, str, Optional[int], str, Optional[int], tuple[int, int]]] = []

    season_match = re.search(
        r"(?i)(?<![A-Za-z0-9])S(?P<season>\d{1,2})"
        r"(?:(?P<range_sep>[-+])(?P<season_to_prefix>S?)(?P<season_to>\d{1,2}))?"
        r"(?:(?:[ ._-]*)(?P<ep_prefix>E)(?P<episode>\d{1,3})"
        r"(?:(?P<ep_sep>[-+])(?P<ep_prefix_to>E)?(?P<episode_to>\d{1,3}))?"
        r"(?P<episode_part>[A-Z])?)?",
        text,
    )
    if season_match:
        season_value = int(season_match.group("season"))
        season_text = f"S{season_match.group('season')}"
        if season_match.group("range_sep") == "-":
            season_to = season_match.group("season_to")
            if season_to:
                season_text = f"{season_text}-{season_match.group('season_to_prefix') or ''}{season_to}"
        episode_text = ""
        episode = None
        if season_match.group("episode"):
            episode = int(season_match.group("episode"))
            episode_text = f"E{season_match.group('episode')}"
            if season_match.group("episode_to"):
                episode_text = f"{episode_text}-E{season_match.group('episode_to')}"
        candidates.append(
            (season_match.start(), 0, season_text, season_value, episode_text, episode, season_match.span(0))
        )

    episode_match = re.search(
        r"(?i)(?<![A-Za-z0-9])(?P<prefix>EP?|Ep)(?P<episode>\d{1,3})"
        r"(?:[- ._]+(?P<prefix_to>EP?|Ep)?(?P<episode_to>\d{1,3}))?(?![A-Za-z0-9])",
        text,
    )
    if episode_match:
        prefix = episode_match.group("prefix")
        episode = int(episode_match.group("episode"))
        episode_text = f"{prefix}{episode_match.group('episode')}"
        if episode_match.group("episode_to"):
            prefix_to = episode_match.group("prefix_to") or prefix
            episode_text = f"{episode_text}-{prefix_to}{episode_match.group('episode_to')}"
        candidates.append((episode_match.start(), 1, "S01", 1, episode_text, episode, episode_match.span(0)))

    chinese_match = re.search(
        r"第?\s*(?P<season>\d{1,2}|[一二三四五六七八九十]+)\s*季"
        r"(?:\s*第\s*(?P<episode>\d{1,3}|[一二三四五六七八九十]+)\s*集)?",
        text,
    )
    if chinese_match:
        season_raw = chinese_match.group("season")
        season = _chinese_or_int(season_raw)
        episode_raw = chinese_match.group("episode")
        episode = _chinese_or_int(episode_raw) if episode_raw else None
        season_text = f"S{season_raw if season_raw.isdigit() else str(season).zfill(2)}"
        episode_text = f"E{episode_raw if episode_raw and episode_raw.isdigit() else episode}" if episode else ""
        candidates.append((chinese_match.start(), 0, season_text, season, episode_text, episode, chinese_match.span(0)))

    if candidates:
        _start, _priority, season_text, season, episode_text, episode, span = min(
            candidates,
            key=lambda candidate: (candidate[0], candidate[1]),
        )
        return season_text, season, episode_text, episode, span

    return "", None, "", None, (-1, -1)


def _chinese_or_int(value: Optional[str]) -> int:
    if not value:
        return 0
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


def _compat_title_candidates(
    stem: str,
    scan_text: str,
    year_span: tuple[int, int],
    season_span: tuple[int, int],
) -> List[str]:
    candidates: List[str] = []
    bracket_titles = _compat_bracket_titles(stem)
    candidates.extend(bracket_titles)
    candidates.extend(_outside_bracket_candidates(stem))
    whole_without_prefix = _strip_known_prefixes(_strip_technical_tail(scan_text))
    whole_without_format = re.sub(r"(?i)\b(?:FLAC|WAV|APE|DSD\d*)\b.*$", "", whole_without_prefix).strip()
    candidates.append(whole_without_format)

    working = scan_text
    cut_at = _first_positive_span_start(year_span, season_span, _usable_tech_span(scan_text))
    if cut_at is not None:
        working = scan_text[:cut_at]
    else:
        working = _strip_technical_tail(scan_text)

    working = _strip_known_prefixes(working)
    working = _strip_title_noise(working)
    candidates.append(working)
    candidates.extend(_split_script_candidates(working))
    candidates.extend(_span_tail_candidates(scan_text, year_span))
    candidates.extend(_span_tail_candidates(scan_text, season_span))

    remainder_candidates = _split_script_candidates(scan_text)
    candidates.extend(remainder_candidates)

    return _unique_titles(_normalize_candidate_title(candidate) for candidate in candidates)


def _compat_bracket_titles(stem: str) -> List[str]:
    titles: List[str] = []
    for value in _bracket_blocks(stem):
        normalized = _normalize_candidate_title(_cut_alternative_title(value))
        if normalized and not _is_noise_title(normalized):
            titles.append(normalized)
    return titles


def _outside_bracket_candidates(stem: str) -> List[str]:
    outside = _normalize_scan_text(_remove_bracket_blocks(stem))
    outside = _strip_known_prefixes(outside)
    raw = _strip_technical_tail(outside)
    raw = _cut_alternative_title(raw)
    cleaned = _strip_title_noise(raw)
    no_format = re.sub(r"(?i)\b(?:FLAC|WAV|APE|DSD\d*)\b.*$", "", raw).strip()
    return _unique_titles([raw, no_format, cleaned] + _split_script_candidates(cleaned))


def _bracket_blocks(text: str) -> List[str]:
    blocks: List[str] = []
    pairs = {"[": "]", "(": ")", "【": "】", "（": "）"}
    closing = set(pairs.values())
    stack: List[tuple[str, int]] = []
    for idx, char in enumerate(str(text or "")):
        if char in pairs:
            stack.append((pairs[char], idx))
        elif char in closing and stack:
            expected, start = stack.pop()
            if char == expected and not stack:
                blocks.append(text[start + 1 : idx])
    return blocks


def _remove_bracket_blocks(text: str) -> str:
    pairs = {"[": "]", "(": ")", "【": "】", "（": "）"}
    closing = set(pairs.values())
    stack: List[tuple[str, int]] = []
    remove: List[tuple[int, int]] = []
    for idx, char in enumerate(str(text or "")):
        if char in pairs:
            stack.append((pairs[char], idx))
        elif char in closing and stack:
            expected, start = stack.pop()
            if char == expected and not stack:
                remove.append((start, idx + 1))

    result = str(text or "")
    for start, end in reversed(remove):
        result = result[:start] + " " + result[end:]
    return result


def _cut_alternative_title(text: str) -> str:
    text = str(text or "").split("[", 1)[0]
    parts = re.split(r"\s*(?:/|\bAKA\b)\s*", text, maxsplit=1, flags=re.IGNORECASE)
    return parts[0]


def _span_tail_candidates(text: str, span: tuple[int, int]) -> List[str]:
    if span[1] <= 0 or span[1] >= len(text):
        return []
    tail = _strip_technical_tail(text[span[1] :])
    tail = _strip_known_prefixes(tail)
    tail = _strip_title_noise(tail)
    return _unique_titles([tail] + _split_script_candidates(tail))


def _first_positive_span_start(*spans: tuple[int, int]) -> Optional[int]:
    starts = [start for start, _end in spans if start > 0]
    return min(starts) if starts else None


def _tech_span(text: str) -> tuple[int, int]:
    match = re.search(
        r"(?i)\b(?:UHD|BluRay|Blu-ray|BDRip|BDMV|BDISO|DVD|DVD9|DVD5|WEB-?DL|WEBRip|HDTV|"
        r"HDTVRip|Netflix|HULU|AMZN|ATVP|DSNP|NF|HMAX|2160p|1080[pi]|720p|576i|480i|"
        r"x26[45]|H\.?26[45]|HEVC|AVC|FLAC|AAC|DTS|DDP|LPCM|TrueHD|Remux|REPACK)\b",
        text,
    )
    return match.span(0) if match else (-1, -1)


def _usable_tech_span(text: str) -> tuple[int, int]:
    span = _tech_span(text)
    if span[0] <= 3:
        return (-1, -1)
    return span


def _strip_technical_tail(text: str) -> str:
    span = _usable_tech_span(text)
    if span[0] > 0:
        return text[: span[0]]
    return text


def _strip_known_prefixes(text: str) -> str:
    text = re.sub(r"(?i)^\s*[\[(]?(?:CCTV\d+(?:HD|K)?\+?|RTHK\d+|BTV|HunanTV|Jade|Top\d+|No\.\s*\d+_?|BDMV|BD-?\d+|CC_?)[\])]?\s*", "", text)
    text = re.sub(r"(?i)^\s*[\[(]?(?:TV|NPMS|Moozzi2|Hi-Res|WARP\d+)[\])]?\s+", "", text)
    text = re.sub(r"^\s*\d{4}[ .-]\d{1,2}[ .-]\d{1,2}\s+", "", text)
    return text.strip()


def _strip_title_noise(text: str) -> str:
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"(?i)^.*?\bCast\s*&?\s*crew\s+User\s+reviews\s+IMDbPro\s+", "", text)
    text = re.sub(r"(?i)\bS\d{1,2}(?:[-+]S?\d{1,2})?(?:[ ._-]*E\d{1,3}(?:[-+]E?\d{1,3})?[A-Z]?)?\b.*$", "", text)
    text = re.sub(r"(?i)\bEP?\d{1,3}(?:[- ._]+EP?\d{1,3})?\b.*$", "", text)
    text = re.sub(r"(?i)\b(?:Director'?s Cut|Theatrical Version|Extended Version|REMASTERED|Classic|Unrated)\b.*$", "", text)
    text = re.sub(r"(?:导演剪辑加长版|导演剪切版|导演剪辑版|导演版|加长版|4K修复版|修复版|DC)\b.*$", "", text)
    text = re.sub(r"(?i)\bTV\s*\+\s*SP\b.*$", "", text)
    text = re.sub(r"(?i)\b(?:\d+CD|CD|DVD|Disc\s*\d+|Disk\s*\d+|BD\d+|FLAC|WAV|APE整轨|DSD\s*\d*)\b.*$", "", text)
    text = re.sub(r"(?:全\d+集|\d+集全|国语|国粤双语|中英字幕|中文字幕|简繁中字|双语中字|剧场版|[^ ]*周年纪念版).*$", "", text)
    text = re.sub(r"(?i)\b(?:\d+K)?修复版\b.*$", "", text)
    text = re.sub(r"(?:3D港版|[^ ]*港版).*$", "", text)
    text = re.sub(r"(?i)\bPart\s+\d+\s*$", "", text)
    text = re.sub(r"[\s(]+(?:18|19|20)\d{2}\s*$", "", text)
    return text.strip(" ._-()[]{}")


def _split_script_candidates(text: str) -> List[str]:
    normalized = _normalize_candidate_title(text)
    if not normalized:
        return []
    tokens = normalized.split()
    native_spans = _native_spans(tokens)
    ascii_spans = _ascii_latin_spans(tokens)
    cleaned_ascii = [_strip_candidate_release_suffix(span) for span in ascii_spans]
    stripped_ascii = [re.sub(r"^\d+\s+(?=[A-Za-z])", "", span).strip() for span in ascii_spans + cleaned_ascii]
    return _unique_titles(native_spans + ascii_spans + cleaned_ascii + stripped_ascii)


def _strip_candidate_release_suffix(text: str) -> str:
    tokens = str(text or "").split()
    while tokens:
        key = _token_key(tokens[-1])
        if YEAR_RE.match(key) or key in RELEASE_REGION_TOKENS or RESOLUTION_RE.match(key):
            tokens.pop()
            continue
        break
    return " ".join(tokens).strip()


def _normalize_candidate_title(text: str) -> str:
    text = str(text or "").replace("&apos;", "'")
    text = text.replace("：", ":")
    text = re.sub(r"(?i)\bWEB[ ._-]?DL\b", "WEBDL", text)
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"[-‐‑‒–—]+", " ", text)
    text = re.sub(r"[/\\]+", " ", text)
    text = re.sub(r"[\[\]\(\)（）【】{}]+", " ", text)
    text = re.sub(r"[,:;|]+", " ", text)
    text = re.sub(r"[\"“”‘’]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return _clean_title(text)


def _is_noise_title(text: str) -> bool:
    key = _token_key(text)
    if not key:
        return True
    if key in TECH_TOKENS or (key in SERVICE_TOKENS and key not in AMBIGUOUS_SERVICE_TOKENS):
        return True
    if key in RELEASE_REGION_TOKENS:
        return True
    if key in {"bdmv", "movie", "disc", "vol", "flac", "wav", "ape", "mkv", "tv", "npms"}:
        return True
    if RESOLUTION_RE.match(key):
        return True
    if re.match(r"^(?:vol|bd|disc|dvd|cd)\d*", key):
        return True
    return False


def _extract_bracket_titles(name: str) -> List[str]:
    titles: List[str] = []
    for match in BRACKET_RE.finditer(name):
        text = _clean_title(match.group(1))
        if text and _looks_like_title_text(text):
            titles.append(text)
    return _unique_titles(titles)


def _normalize_release_name(name: str) -> str:
    text = BRACKET_RE.sub(lambda match: f" {match.group(1)} ", name)
    text = text.replace("&apos;", "'")
    text = text.replace("HDR10+", "HDR10Plus")
    text = re.sub(r"(?i)\bDD\+(\d)", r"DDP\1", text)
    text = re.sub(r"(?i)\bH[ ._-]?26([45])\b", r"H26\1", text)
    text = re.sub(r"(?i)\bDTS[ ._-]?HD\b", "DTSHD", text)
    text = re.sub(r"(?i)\bWEB[ ._-]?DL\b", "WEBDL", text)
    text = re.sub(r"(?i)\bBlu[ ._-]?ray\b", "BluRay", text)
    text = re.sub(r"(?i)\bUHD[ ._-]?BluRay\b", "UHD BluRay", text)
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"[-‐‑‒–—]+", " ", text)
    text = re.sub(r"[,:;|/\\]+", " ", text)
    text = re.sub(r"[\"“”‘’]+", "", text)
    return _clean_title(text)


def _find_season(tokens: Sequence[str]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    for idx, token in enumerate(tokens):
        match = SEASON_RE.match(_token_key(token))
        if match:
            season = int(match.group("season"))
            episode = match.group("episode")
            return idx, season, int(episode) if episode else None
    return None, None, None


def _find_technical_start(tokens: Sequence[str]) -> Optional[int]:
    for idx, token in enumerate(tokens):
        if idx == 0:
            continue
        if _is_technical_at(tokens, idx):
            return idx
    return None


def _is_technical_at(tokens: Sequence[str], idx: int) -> bool:
    token = _token_key(tokens[idx])
    if RESOLUTION_RE.match(token):
        return True
    if token in TECH_TOKENS or token in SERVICE_TOKENS:
        if token in AMBIGUOUS_SERVICE_TOKENS:
            return _has_immediate_technical_tail(tokens, idx)
        return True
    if re.match(r"^(?:ddp|dd|dts|aac|truehd|flac)\d", token):
        return True
    if re.match(r"^(?:10bit|8bit|60fps|50fps)$", token):
        return True
    return False


def _has_immediate_technical_tail(tokens: Sequence[str], idx: int) -> bool:
    for token in tokens[idx + 1 : idx + 3]:
        key = _token_key(token)
        if RESOLUTION_RE.match(key) or key in TECH_TOKENS:
            return True
        if re.match(r"^(?:ddp|dd|dts|aac|truehd|flac)\d", key):
            return True
        if re.match(r"^(?:10bit|8bit|60fps|50fps)$", key):
            return True
    return False


def _choose_year(
    tokens: Sequence[str],
    season_index: Optional[int],
    tech_index: Optional[int],
) -> tuple[Optional[int], Optional[int]]:
    content_end = tech_index if tech_index is not None else len(tokens)
    candidates = []
    for idx, token in enumerate(tokens[:content_end]):
        key = _token_key(token)
        if YEAR_RE.match(key):
            candidates.append((idx, int(key)))

    if not candidates:
        return None, None

    scored = []
    later_year_exists = len(candidates) > 1
    for idx, year in candidates:
        score = 0
        if idx > 0:
            score += 1
        if idx == 0 and later_year_exists:
            score -= 6
        if tech_index is not None and 0 < tech_index - idx <= 5:
            score += 3
        if idx == content_end - 1:
            score += 2
        if season_index is not None:
            distance = abs(idx - season_index)
            if distance <= 2:
                score += 3
            if idx > season_index:
                score += 1
        if idx > 0 and _has_title_token(tokens[:idx]):
            score += 2
        scored.append((score, idx, year))

    score, idx, year = max(scored, key=lambda item: (item[0], item[1]))
    if score < 1:
        return None, None
    return idx, year


def _has_title_token(tokens: Iterable[str]) -> bool:
    return any(_looks_like_title_text(token) for token in tokens)


def _title_candidates(title_segment: str, bracket_titles: Sequence[str]) -> List[str]:
    if not title_segment:
        return _unique_titles(bracket_titles)

    raw_candidates: List[str] = []
    tokens = title_segment.split()
    aka_indexes = [idx for idx, token in enumerate(tokens) if token.upper() in {"AKA", "ALIAS"}]
    for idx in aka_indexes:
        raw_candidates.append(" ".join(tokens[idx + 1 :]))
        raw_candidates.append(" ".join(tokens[:idx]))

    ascii_latin_spans = _ascii_latin_spans(tokens)
    native_spans = _native_spans(tokens)
    native_titles = [title for title in bracket_titles + native_spans if _has_non_ascii_title_char(title)]

    if native_titles and ascii_latin_spans:
        raw_candidates.extend(native_titles)
        raw_candidates.append(title_segment)
        raw_candidates.extend(ascii_latin_spans)
        raw_candidates.extend(bracket_titles)
        raw_candidates.extend(native_spans)
    else:
        raw_candidates.append(title_segment)
        raw_candidates.extend(bracket_titles)
        raw_candidates.extend(ascii_latin_spans)
        raw_candidates.extend(native_spans)

    return _unique_titles(_clean_title(candidate) for candidate in raw_candidates)


def _ascii_latin_spans(tokens: Sequence[str]) -> List[str]:
    spans: List[str] = []
    current: List[str] = []
    for token in tokens:
        if _has_non_ascii_title_char(token):
            if current:
                spans.append(" ".join(current))
                current = []
            continue
        if _has_title_char(token) or token in {"&", "+", "#"}:
            current.append(token)
        elif current:
            spans.append(" ".join(current))
            current = []
    if current:
        spans.append(" ".join(current))
    return [span for span in spans if _looks_like_title_text(span)]


def _native_spans(tokens: Sequence[str]) -> List[str]:
    spans: List[str] = []
    current: List[str] = []
    for token in tokens:
        if _has_non_ascii_title_char(token):
            current.append(token)
        elif current:
            spans.append(" ".join(current))
            current = []
    if current:
        spans.append(" ".join(current))
    return [span for span in spans if _looks_like_title_text(span)]


def _unique_titles(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        title = _clean_title(value)
        if not title:
            continue
        key = _title_key(title)
        if key in seen:
            continue
        seen.add(key)
        result.append(title)
    return result


def _order_title_candidates(candidates: Sequence[str], hints: ReleaseHints) -> List[str]:
    candidates = list(candidates)
    return [
        candidate
        for _index, candidate in sorted(
            enumerate(candidates),
            key=lambda item: (
                0 if _title_noise_score(item[1], hints) == 0 else 1,
                _search_language_priority(item[1]),
                _leading_number_stripped_rank(item[1], candidates),
                _title_noise_score(item[1], hints),
                item[0],
            ),
        )
    ]


def _search_language_priority(candidate: str) -> int:
    if _has_non_ascii_title_char(candidate):
        return 1 if _has_latin_title_char(candidate) else 0
    return 2


def _preferred_title(candidates: Sequence[str], hints: ReleaseHints) -> str:
    if not candidates:
        return ""

    candidates = list(candidates)
    canonical = [
        (index, candidate)
        for index, candidate in enumerate(candidates)
        if _is_latin_title_candidate(candidate) and _title_noise_score(candidate, hints) == 0
    ]
    if canonical:
        return min(
            canonical,
            key=lambda item: (_aka_alias_rank(item[1], candidates), _latin_fragment_rank(item[1], candidates, hints), item[0]),
        )[1]

    short_alias = [
        (index, candidate)
        for index, candidate in enumerate(candidates)
        if _is_short_upper_latin_alias_candidate(candidate, candidates)
    ]
    if short_alias:
        return short_alias[0][1]

    low_noise_latin = [
        (index, candidate)
        for index, candidate in enumerate(candidates)
        if _is_latin_title_candidate(candidate)
        and _title_noise_score(candidate, hints) <= 4
        and not _candidate_has_year_token(candidate)
    ]
    if low_noise_latin:
        return min(
            low_noise_latin,
            key=lambda item: (_aka_alias_rank(item[1], candidates), _latin_fragment_rank(item[1], candidates, hints), item[0]),
        )[1]

    return min(
        enumerate(candidates),
        key=lambda item: (_title_noise_score(item[1], hints), item[0]),
    )[1]


def _leading_number_stripped_rank(candidate: str, candidates: Sequence[str]) -> int:
    if len(candidate.split()) < 2:
        return 0

    candidate_key = _title_key(candidate)
    for other in candidates:
        if other == candidate:
            continue
        stripped = re.sub(r"^\d{2,4}\s+", "", other).strip()
        if stripped != other and _title_key(stripped) == candidate_key:
            return 1
    return 0


def _is_short_upper_latin_alias_candidate(candidate: str, candidates: Sequence[str]) -> bool:
    text = str(candidate or "").strip()
    token_keys = [_token_key(token) for token in text.split()]
    if not token_keys or len(token_keys) > 2:
        return False
    if any(YEAR_RE.match(token) for token in token_keys):
        return False
    if any(token in {"dc", "v1", "v2"} for token in token_keys):
        return False
    if any(token in TECH_TOKENS or token in SERVICE_TOKENS or token in RELEASE_REGION_TOKENS for token in token_keys):
        return False
    if not _is_latin_title_candidate(text):
        return False
    if text != text.upper():
        return False
    if len(_title_key(text)) < 2:
        return False
    return any(_has_non_ascii_title_char(other) and _title_key(text) in _title_key(other) for other in candidates)


def _latin_fragment_rank(candidate: str, candidates: Sequence[str], hints: ReleaseHints) -> int:
    words = candidate.split()
    if len(words) > 2:
        return 0

    candidate_key = _title_key(candidate)
    for other in candidates:
        other_words = other.split()
        if len(other_words) <= len(words) + 1:
            continue
        if not _is_latin_title_candidate(other) or _title_noise_score(other, hints) != 0:
            continue
        if candidate_key and candidate_key in _title_key(other):
            return 1
    return 0


def _aka_alias_rank(candidate: str, candidates: Sequence[str]) -> int:
    candidate_key = _title_key(candidate)
    for other in candidates:
        parts = re.split(r"(?i)\bAKA\b|\bALIAS\b", other, maxsplit=1)
        if len(parts) != 2:
            continue
        alias = _normalize_candidate_title(parts[1])
        if candidate_key and _title_key(alias) == candidate_key:
            return 0
    return 1


def _candidate_has_year_token(candidate: str) -> bool:
    return any(YEAR_RE.match(_token_key(token)) for token in candidate.split())


def _title_noise_score(candidate: str, hints: ReleaseHints) -> int:
    penalty = 0
    key = _title_key(candidate)
    token_count = len(candidate.split())
    token_keys = [_token_key(token) for token in candidate.split()]

    for marker in (hints.episode_text, hints.season_text):
        if marker and _title_key(marker) in key:
            penalty += 8
    if re.search(r"(?i)(?:^|\s)S\d{1,2}(?:[-+]S?\d{1,2})?(?:\s*E\d{1,3})?", candidate):
        penalty += 8
    if re.search(r"(?i)(?:^|\s)E\d{1,3}(?:[-\s]+E?\d{1,3})?", candidate):
        penalty += 8
    if re.search(r"(?:第?\d{1,2}季|第\d{1,3}集)", candidate):
        penalty += 8

    year_values = [hints.year_text]
    if hints.year_text and "-" in hints.year_text:
        year_values.extend(part for part in hints.year_text.split("-") if part)
    for value in year_values:
        if value and re.search(rf"(?:^|\s){re.escape(value)}$", candidate):
            penalty += 5 if token_count > 1 else 0
        elif value and re.search(rf"(?:^|\s){re.escape(value)}(?:\s|$)", candidate) and token_count > 2:
            penalty += 3
        elif value and candidate.endswith(value) and len(candidate) > len(value):
            penalty += 5

    if any(token in TECH_TOKENS or (token in SERVICE_TOKENS and token not in AMBIGUOUS_SERVICE_TOKENS) for token in token_keys):
        penalty += 10
    if any(RESOLUTION_RE.match(token) for token in token_keys):
        penalty += 10
    if any(token in {"aka", "alias"} for token in token_keys):
        penalty += 6
    if any(token in {"director", "directors", "cut", "remastered", "complete"} for token in token_keys):
        penalty += 5
    if re.search(r"(?i)\bVol(?:ume)?\s*\d", candidate):
        penalty += 12
    if re.search(r"(?i)\bCast\s*&?\s*crew\s+User\s+reviews\s+IMDbPro\b", candidate):
        penalty += 15
    if any(token in {"cctv1", "cctv5", "cctv8hd", "cctv9", "btv", "hunantv", "litv"} for token in token_keys):
        penalty += 12
    if any(re.match(r"^rthk\d+$", token) for token in token_keys):
        penalty += 12
    if any(token in {"guoyu", "shuangyu", "zhongzi", "zhongyingzimu"} for token in token_keys):
        penalty += 6
    if re.search(r"(?:中字|字幕|双语|国粤|国语|英语|日语|韩语|德语|法语|西班牙语|土耳其语|藏语|港版|修复版|纪念版)", candidate):
        penalty += 6
    if re.search(r"(?:导演剪辑加长版|导演剪切版|导演剪辑版|导演版|加长版)", candidate):
        penalty += 6
    if token_count == 1 and _token_key(candidate) in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        penalty += 15
    if token_count == 1 and re.match(r"^[A-Z0-9+._-]{2,8}$", candidate):
        penalty += 12
    if _is_repeated_phrase(candidate):
        penalty += 8
        words = candidate.split()
        if len(words) == 2 and YEAR_RE.match(_token_key(words[0])) and _token_key(words[0]) == _token_key(words[1]):
            penalty += 8
    leading_year = re.match(r"^((?:18|19|20)\d{2})\s+", candidate)
    if leading_year and leading_year.group(1) in year_values:
        penalty += 4
    if re.search(r"\b\d{3,4}x\d{3,4}\b", candidate, flags=re.IGNORECASE):
        penalty += 10
    if token_count > 14:
        penalty += 4
    return penalty


def _is_repeated_phrase(candidate: str) -> bool:
    words = candidate.split()
    if len(words) < 2 or len(words) % 2:
        return False
    midpoint = len(words) // 2
    return [word.lower() for word in words[:midpoint]] == [word.lower() for word in words[midpoint:]]


def _is_latin_title_candidate(text: str) -> bool:
    candidate = str(text or "")
    return _has_latin_title_char(candidate) and not _has_non_ascii_title_char(candidate)


def _has_latin_title_char(text: str) -> bool:
    for ch in str(text or ""):
        if not ch.isalpha():
            continue
        if ord(ch) <= 127 or "LATIN" in unicodedata.name(ch, ""):
            return True
    return False


def _looks_like_title_text(text: str) -> bool:
    if _has_non_ascii_title_char(text):
        return True
    key = _token_key(text)
    if not key:
        return False
    if key in TECH_TOKENS or key in RELEASE_REGION_TOKENS:
        return False
    if key in SERVICE_TOKENS and key not in AMBIGUOUS_SERVICE_TOKENS:
        return False
    if RESOLUTION_RE.match(key):
        return False
    return bool(_has_title_char(text))


def _has_title_char(text: str) -> bool:
    return any(ch.isalpha() or ch.isdigit() for ch in str(text or ""))


def _has_non_ascii_title_char(text: str) -> bool:
    for ch in str(text or ""):
        if not (ch.isalpha() or ch.isdigit()) or ord(ch) <= 127:
            continue
        name = unicodedata.name(ch, "")
        if "LATIN" not in name and "ROMAN NUMERAL" not in name:
            return True
    return False


def _confidence(
    title: str,
    year: Optional[int],
    kind_hint: Optional[str],
    warnings: Sequence[str],
) -> float:
    score = 0.2
    if title:
        score += 0.3
    if year:
        score += 0.3
    if kind_hint:
        score += 0.1
    if not warnings:
        score += 0.1
    else:
        score -= min(0.25, len(warnings) * 0.08)
    return max(0.0, min(1.0, round(score, 2)))


def _token_key(token: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", token).lower()


def _title_key(title: str) -> str:
    return "".join(ch.lower() for ch in str(title or "") if ch.isalnum())


def _clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or ""))
    text = text.strip(" _-")
    text = _restore_title_abbreviations(text)
    text = _restore_spaced_acronyms(text)
    if _ends_with_dotted_acronym(text) or _ends_with_title_suffix_abbreviation(text):
        return text
    return text.strip(".")


def _restore_title_abbreviations(text: str) -> str:
    text = str(text or "")
    prefix_abbreviations = {
        "dr": "Dr.",
        "mr": "Mr.",
        "mrs": "Mrs.",
        "ms": "Ms.",
        "prof": "Prof.",
    }
    suffix_abbreviations = {
        "jr": "Jr.",
        "sr": "Sr.",
    }

    def replace_prefix(match: re.Match[str]) -> str:
        return f"{match.group('lead')}{prefix_abbreviations[match.group('abbr').lower()]} "

    def replace_suffix(match: re.Match[str]) -> str:
        return f" {suffix_abbreviations[match.group('abbr').lower()]}"

    text = re.sub(
        r"(?i)(?P<lead>^|\s)(?P<abbr>dr|mr|mrs|ms|prof)\s+(?=[A-Za-z0-9])",
        replace_prefix,
        text,
    )
    text = re.sub(r"(?i)(?P<lead>^|\s)(?:ph\s*d|p\s*h\s*d)(?=\s|$)", r"\g<lead>PhD", text)
    return re.sub(r"(?i)\s+(?P<abbr>jr|sr)$", replace_suffix, text)


def _restore_spaced_acronyms(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return ".".join(match.group(1).split()) + "."

    return re.sub(r"(?<!\S)((?:[A-Z]\s+){1,7}[A-Z])$", replace, str(text or ""))


def _ends_with_dotted_acronym(text: str) -> bool:
    return bool(re.search(r"(?:^|\s)(?:[A-Z]\.){2,8}$", str(text or "")))


def _ends_with_title_suffix_abbreviation(text: str) -> bool:
    return bool(re.search(r"(?i)(?:^|\s)(?:Jr|Sr)\.$", str(text or "")))
