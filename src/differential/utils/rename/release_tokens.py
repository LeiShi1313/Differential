import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Dict, List, Tuple

from differential.utils.rename.formatter import (
    normalize_audio_codec,
    normalize_hdr,
    normalize_resolution,
    normalize_token,
    normalize_type,
    normalize_uploader,
    normalize_video_codec,
)


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

SOURCE_ALIASES: Dict[str, str] = {
    "APPLETV": "ATVP",
    "APPLETVPLUS": "ATVP",
    "DISNEY": "DSNP",
    "DISNEYPLUS": "DSNP",
    "ITUNES": "IT",
    "NETFLIX": "NF",
    "NOWPLAYER": "NOW",
    "PEACOCK": "PCOK",
}

TYPE_PATTERNS = (
    (re.compile(r"\bUHD[ ._-]?Blu[ ._-]?Ray\b", re.IGNORECASE), "UHD.BluRay"),
    (re.compile(r"\bBlu[ ._-]?Ray\b", re.IGNORECASE), "BluRay"),
    (re.compile(r"\bWEB[ ._-]?DL\b", re.IGNORECASE), "WEB-DL"),
    (re.compile(r"\bWEB[ ._-]?Rip\b", re.IGNORECASE), "WEBRip"),
    (re.compile(r"\bHDTV\b", re.IGNORECASE), "HDTV"),
    (re.compile(r"\bBDMV\b", re.IGNORECASE), "BDMV"),
    (re.compile(r"\bREMUX\b", re.IGNORECASE), "REMUX"),
)

HDR_PATTERNS = (
    (re.compile(r"\bDoVi\b|\bDOVI\b|\bDolby[ ._-]?Vision\b", re.IGNORECASE), "DV"),
    (re.compile(r"\bHDR10\+\b|\bHDR10[ ._-]?Plus\b", re.IGNORECASE), "HDR10Plus"),
    (re.compile(r"\bHDR10\b", re.IGNORECASE), "HDR10"),
    (re.compile(r"\bHDR\b", re.IGNORECASE), "HDR"),
    (re.compile(r"\bHLG\b", re.IGNORECASE), "HLG"),
    (re.compile(r"\bSDR\b", re.IGNORECASE), "SDR"),
)

EDITION_PATTERNS = (
    (re.compile(r"\bCriterion\b", re.IGNORECASE), "Criterion"),
    (re.compile(r"\bDirector'?s[ ._-]?Cut\b|\bDC\b", re.IGNORECASE), "DirectorCut"),
    (re.compile(r"\bExtended\b", re.IGNORECASE), "Extended"),
    (re.compile(r"\bRemastered\b", re.IGNORECASE), "Remastered"),
)

RESOLUTION_RE = re.compile(r"(?<![A-Za-z0-9])(?:[1-8]\d{2,3}[pi]|4k|8k)(?![A-Za-z0-9])", re.IGNORECASE)

VIDEO_PATTERNS = (
    (re.compile(r"\bH[ ._-]?265\b", re.IGNORECASE), "H265"),
    (re.compile(r"\bH[ ._-]?264\b", re.IGNORECASE), "H264"),
    (re.compile(r"\bHEVC\b", re.IGNORECASE), "HEVC"),
    (re.compile(r"\bAVC\b", re.IGNORECASE), "AVC"),
    (re.compile(r"\bx265\b", re.IGNORECASE), "x265"),
    (re.compile(r"\bx264\b", re.IGNORECASE), "x264"),
    (re.compile(r"\bAV1\b", re.IGNORECASE), "AV1"),
)

DTS_HD_MA_RE = re.compile(
    r"\bDTS[ ._-]?HD[ ._-]?M(?:A|aster[ ._-]?Audio)?(?:[ ._-]?(?P<ch>[257](?:[ ._-]?[01])))?",
    re.IGNORECASE,
)
TRUEHD_RE = re.compile(
    r"\b(?:TrueHD|Dolby[ ._-]?TrueHD)(?:[ ._-]?(?P<ch>[257](?:[ ._-]?[01])))?(?:[ ._-]?(?P<atmos>Atmos))?",
    re.IGNORECASE,
)
DDP_RE = re.compile(
    r"\b(?:DDP|DD\+|EAC3|E[ ._-]?AC[ ._-]?3|Dolby[ ._-]?Digital[ ._-]?Plus)"
    r"(?:[ ._-]?(?P<ch>[257](?:[ ._-]?[01])))?(?:[ ._-]?(?P<atmos>Atmos))?",
    re.IGNORECASE,
)
DD_RE = re.compile(
    r"\b(?:DD|AC3|Dolby[ ._-]?Digital)(?:[ ._-]?(?P<ch>[257](?:[ ._-]?[01])))?",
    re.IGNORECASE,
)
AAC_RE = re.compile(r"\bAAC(?:[ ._-]?(?P<ch>[257](?:[ ._-]?[01])))?", re.IGNORECASE)
FLAC_RE = re.compile(r"\bFLAC\b", re.IGNORECASE)
LPCM_RE = re.compile(r"\bLPCM\b|\bPCM\b", re.IGNORECASE)
DTS_RE = re.compile(r"\bDTS(?:[ ._-]?(?P<ch>[257](?:[ ._-]?[01])))?", re.IGNORECASE)

TECHNICAL_UPLOADER_KEYS = {
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
}


@dataclass(frozen=True)
class ParsedReleaseTokens:
    source: str = ""
    release_type: str = ""
    resolution: str = ""
    video_codec: str = ""
    hdr: str = ""
    audio_codec: str = ""
    edition: str = ""
    release_group: str = ""
    uploader: str = ""
    season_end: int = 0
    episode_end: int = 0
    part: int = 0
    warnings: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        payload = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name == "warnings":
                if value:
                    payload[field.name] = list(value)
            elif value:
                payload[field.name] = value
        return payload


def parse_release_tokens(path_or_name) -> ParsedReleaseTokens:
    name = _name_from_path(path_or_name)
    uploader = _find_uploader(name)
    return ParsedReleaseTokens(
        source=_first(find_sources(name)),
        release_type=_first(find_release_types(name)),
        resolution=_first(find_resolutions(name)),
        video_codec=_first(find_video_codecs(name)),
        hdr=_first(find_hdr_values(name)),
        audio_codec=_first(find_audio_codecs(name)),
        edition=_first(find_editions(name)),
        release_group=uploader,
        uploader=uploader,
    )


def find_sources(name: str) -> List[str]:
    found = []
    for token in re.split(r"[^A-Za-z0-9+]+", name):
        upper = token.upper()
        mapped = SOURCE_ALIASES.get(upper, upper)
        if mapped in SOURCE_TOKENS:
            found.append(mapped)
    return _unique(found)


def find_release_types(name: str) -> List[str]:
    normalized = [normalize_type(value) for value in _find_by_patterns(name, TYPE_PATTERNS)]
    if "REMUX" in normalized and "UHD.BluRay" in normalized:
        return _unique(["UHD.BluRay.REMUX"] + normalized)
    if "REMUX" in normalized and "BluRay" in normalized:
        return _unique(["BluRay.REMUX"] + normalized)
    return _unique(normalized)


def find_resolutions(name: str) -> List[str]:
    return _unique(normalize_resolution(match.group(0)) for match in RESOLUTION_RE.finditer(name))


def find_video_codecs(name: str) -> List[str]:
    return _unique(normalize_video_codec(value) for value in _find_by_patterns(name, VIDEO_PATTERNS))


def find_hdr_values(name: str) -> List[str]:
    found = _unique(normalize_hdr(value) for value in _find_by_patterns(name, HDR_PATTERNS))
    if "DV" in found and "HDR" in found:
        return _unique(["DV.HDR"] + found)
    return found


def find_audio_codecs(name: str) -> List[str]:
    candidates = []
    match = DTS_HD_MA_RE.search(name)
    if match:
        candidates.append(_codec_with_channel("DTS-HD.MA", match.group("ch")))

    match = TRUEHD_RE.search(name)
    if match:
        token = _codec_with_channel("TrueHD", match.group("ch"))
        if match.group("atmos"):
            token = f"{token}.Atmos"
        candidates.append(token)

    match = DDP_RE.search(name)
    if match:
        token = _codec_with_channel("DDP", match.group("ch"))
        if match.group("atmos"):
            token = f"{token}.Atmos"
        candidates.append(token)

    match = DTS_RE.search(name)
    if match:
        candidates.append(_codec_with_channel("DTS", match.group("ch")))

    match = DD_RE.search(name)
    if match:
        candidates.append(_codec_with_channel("DD", match.group("ch")))

    match = AAC_RE.search(name)
    if match:
        candidates.append(_codec_with_channel("AAC", match.group("ch")))

    if FLAC_RE.search(name):
        candidates.append("FLAC")
    if LPCM_RE.search(name):
        candidates.append("LPCM")
    return _unique(normalize_audio_codec(candidate) for candidate in candidates)


def find_editions(name: str) -> List[str]:
    return _unique(normalize_token(value) for value in _find_by_patterns(name, EDITION_PATTERNS))


def find_uploaders(name: str) -> List[str]:
    uploader = _find_uploader(name)
    return [uploader] if uploader else []


def _find_uploader(name: str) -> str:
    hyphen_match = re.search(r"-([A-Za-z0-9][A-Za-z0-9._@+]{1,40})$", name)
    if hyphen_match:
        candidate = normalize_uploader(hyphen_match.group(1))
        if candidate and not _is_technical_uploader_candidate(candidate):
            return candidate

    at_match = re.search(r"@([A-Za-z0-9][A-Za-z0-9._+-]{1,40})$", name)
    if at_match:
        candidate = normalize_uploader(at_match.group(1))
        if candidate and not _is_technical_uploader_candidate(candidate):
            return candidate
    return ""


def _is_technical_uploader_candidate(value: str) -> bool:
    key = re.sub(r"[\s._@+-]+", "", str(value or "").lower())
    if key in TECHNICAL_UPLOADER_KEYS:
        return True
    if key.startswith("hdma") or key.startswith("ma"):
        return True
    if key.startswith(("ddp", "dts", "truehd")) and re.search(r"\d[._-]?\d$", value):
        return True
    return False


def _find_by_patterns(name: str, patterns) -> List[str]:
    found = []
    for pattern, value in patterns:
        if pattern.search(name):
            found.append(value)
    return found


def _codec_with_channel(codec: str, channel: str) -> str:
    channel_token = _normalize_channel(channel)
    if not channel_token:
        return codec
    separator = "." if codec.endswith(".MA") else ""
    return f"{codec}{separator}{channel_token}"


def _normalize_channel(channel: str) -> str:
    if not channel:
        return ""
    digits = re.sub(r"\D", "", channel)
    if len(digits) == 2:
        return f"{digits[0]}.{digits[1]}"
    return normalize_token(channel)


def _name_from_path(path_or_name) -> str:
    if isinstance(path_or_name, Path):
        return path_or_name.name
    text = str(path_or_name or "").strip().replace("\\", "/").rstrip("/")
    return text.rsplit("/", 1)[-1] if "/" in text else text


def _first(values: List[str]) -> str:
    return values[0] if values else ""


def _unique(values) -> List[str]:
    result = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
