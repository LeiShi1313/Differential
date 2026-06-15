import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from differential.utils.media_name import strip_known_extension
from differential.utils.rename.formatter import normalize_uploader


@dataclass(frozen=True)
class ReleaseGroupConfig:
    groups: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ReleaseGroupMatch:
    value: str = ""
    source: str = ""
    confidence: str = ""
    raw: str = ""
    warnings: Tuple[str, ...] = ()


def match_release_group(path_or_name, config: ReleaseGroupConfig = None) -> ReleaseGroupMatch:
    name = _name_from_path(path_or_name)
    config = config or ReleaseGroupConfig()
    warnings = list(config.warnings)
    custom_groups = _custom_group_map(config.groups)

    for raw in _custom_candidates(name):
        value = custom_groups.get(_group_key(raw))
        if value:
            return ReleaseGroupMatch(value=value, source="custom", confidence="high", raw=raw, warnings=tuple(warnings))

    for raw in _suffix_candidates(name):
        if _is_technical_group_candidate(raw):
            continue
        return ReleaseGroupMatch(
            value=normalize_uploader(raw),
            source="suffix",
            confidence="medium",
            raw=raw,
            warnings=tuple(warnings),
        )

    return ReleaseGroupMatch(warnings=tuple(warnings))


def _custom_candidates(name: str) -> List[str]:
    candidates = _suffix_candidates(name)
    final_token = _final_token(name)
    if final_token:
        candidates.append(final_token)
    return _unique(candidates)


def _suffix_candidates(name: str) -> List[str]:
    candidates = []

    hyphen_index = name.rfind("-")
    if _is_suffix_delimiter(name, hyphen_index):
        candidates.append((hyphen_index, name[hyphen_index + 1 :]))

    at_index = name.rfind("@")
    if _is_suffix_delimiter(name, at_index):
        candidates.append((at_index, name[at_index + 1 :]))

    candidates.sort(reverse=True)
    return [normalize_uploader(candidate) for _index, candidate in candidates if normalize_uploader(candidate)]


def _is_suffix_delimiter(name: str, index: int) -> bool:
    if index <= 0 or index >= len(name) - 1:
        return False
    # A release-group delimiter must be after the last token separator. This
    # prevents the hyphen inside tokens such as WEB-DL from becoming a group.
    last_token_separator = max(name.rfind("."), name.rfind(" "), name.rfind("_"))
    return index > last_token_separator


def _final_token(name: str) -> str:
    tokens = [token for token in re.split(r"[^A-Za-z0-9+]+", name) if token]
    return normalize_uploader(tokens[-1]) if tokens else ""


def _custom_group_map(groups: Tuple[str, ...]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for group in groups:
        normalized = normalize_uploader(group)
        if not normalized:
            continue
        result[_group_key(normalized)] = normalized
    return result


def _is_technical_group_candidate(value: str) -> bool:
    key = _group_key(value)
    if key in {
        "dl",
        "rip",
        "hd",
        "ma",
        "hdr",
        "hdr10",
        "hdr10plus",
        "dv",
        "dovi",
        "hevc",
        "h264",
        "h265",
        "x264",
        "x265",
        "avc",
        "aac",
        "ac3",
        "dd",
        "ddp",
        "dts",
        "dtshd",
        "dtshdma",
        "truehd",
    }:
        return True
    if key.startswith("hdma") or key.startswith("ma"):
        return True
    if key.startswith(("ddp", "dts", "truehd")) and re.search(r"\d[._-]?\d$", value):
        return True
    return False


def _group_key(value: str) -> str:
    return re.sub(r"[\s._@+-]+", "", str(value or "").lower())


def _name_from_path(path_or_name) -> str:
    if isinstance(path_or_name, Path):
        name = path_or_name.name
        return strip_known_extension(name)[0]
    text = str(path_or_name or "").strip().replace("\\", "/").rstrip("/")
    name = text.rsplit("/", 1)[-1] if "/" in text else text
    return strip_known_extension(name)[0]


def _unique(values) -> List[str]:
    result = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
