import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from differential.utils.rename.formatter import normalize_token, normalize_type, normalize_uploader


SOURCE_TOKENS = {
    "AMZN",
    "ATVP",
    "BILI",
    "CR",
    "DSNP",
    "HMAX",
    "HULU",
    "IQ",
    "IT",
    "KKTV",
    "NF",
    "NOW",
    "PCOK",
    "STAN",
    "TVING",
    "VIU",
    "WEB",
    "HDTV",
}

TYPE_PATTERNS = (
    (re.compile(r"\bREMUX\b", re.IGNORECASE), "REMUX"),
    (re.compile(r"\bWEB[ ._-]?DL\b", re.IGNORECASE), "WEB-DL"),
    (re.compile(r"\bWEB[ ._-]?Rip\b", re.IGNORECASE), "WEBRip"),
    (re.compile(r"\bHDTV\b", re.IGNORECASE), "HDTV"),
    (re.compile(r"\bUHD[ ._-]?Blu[ ._-]?Ray\b", re.IGNORECASE), "UHD.BluRay"),
    (re.compile(r"\bBlu[ ._-]?Ray\b", re.IGNORECASE), "BluRay"),
)

HDR_PATTERNS = (
    (re.compile(r"\bDoVi\b|\bDolby[ ._-]?Vision\b", re.IGNORECASE), "DV"),
    (re.compile(r"\bHDR10\+\b", re.IGNORECASE), "HDR10Plus"),
    (re.compile(r"\bHDR10\b", re.IGNORECASE), "HDR10"),
    (re.compile(r"\bHDR\b", re.IGNORECASE), "HDR"),
)

EDITION_PATTERNS = (
    (re.compile(r"\bCriterion\b", re.IGNORECASE), "Criterion"),
    (re.compile(r"\bDirector'?s[ ._-]?Cut\b|\bDC\b", re.IGNORECASE), "DirectorCut"),
    (re.compile(r"\bExtended\b", re.IGNORECASE), "Extended"),
    (re.compile(r"\bRemastered\b", re.IGNORECASE), "Remastered"),
)


@dataclass
class TokenSuggestions:
    sources: List[str] = field(default_factory=list)
    uploaders: List[str] = field(default_factory=list)
    release_types: List[str] = field(default_factory=list)
    editions: List[str] = field(default_factory=list)
    hdr: List[str] = field(default_factory=list)


def suggest_tokens(path_or_name) -> TokenSuggestions:
    name = Path(path_or_name).name if isinstance(path_or_name, Path) else str(path_or_name or "")
    return TokenSuggestions(
        sources=_suggest_sources(name),
        uploaders=_suggest_uploaders(name),
        release_types=_suggest_types(name),
        editions=_suggest_by_patterns(name, EDITION_PATTERNS),
        hdr=_suggest_by_patterns(name, HDR_PATTERNS),
    )


def _suggest_sources(name: str) -> List[str]:
    tokens = re.split(r"[^A-Za-z0-9+]+", name)
    found = []
    for token in tokens:
        upper = token.upper()
        if upper in SOURCE_TOKENS:
            found.append(upper)
    return _unique(found)


def _suggest_uploaders(name: str) -> List[str]:
    candidates = []
    suffix_match = re.search(r"-([A-Za-z0-9][A-Za-z0-9._@+]{1,40})$", name)
    if suffix_match:
        candidates.append(normalize_uploader(suffix_match.group(1)))

    at_match = re.search(r"@([A-Za-z0-9][A-Za-z0-9._+-]{1,40})$", name)
    if at_match:
        candidates.append(normalize_uploader(at_match.group(1)))

    return _unique(candidate for candidate in candidates if candidate)


def _suggest_types(name: str) -> List[str]:
    normalized = [normalize_type(value) for value in _suggest_by_patterns(name, TYPE_PATTERNS)]
    if "REMUX" in normalized and "UHD.BluRay" in normalized:
        return _unique(["UHD.BluRay.REMUX"] + normalized)
    if "REMUX" in normalized and "BluRay" in normalized:
        return _unique(["BluRay.REMUX"] + normalized)
    return _unique(normalized)


def _suggest_by_patterns(name: str, patterns) -> List[str]:
    found = []
    for pattern, value in patterns:
        if pattern.search(name):
            found.append(normalize_token(value))
    return _unique(found)


def _unique(values) -> List[str]:
    result = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
