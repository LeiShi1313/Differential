import re
from typing import Iterable, Optional

from differential.utils.rename.models import CodecTokenMap, RenameMetadata, TechnicalTokens


ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DOTS_RE = re.compile(r"\.{2,}")
SPACE_RE = re.compile(r"\s+")


VIDEO_CODEC_MAP = {
    "avc": "AVC",
    "h264": "H264",
    "x264": "x264",
    "hevc": "HEVC",
    "h265": "H265",
    "x265": "x265",
    "mpeg2": "MPEG-2",
    "vc1": "VC-1",
    "av1": "AV1",
}

AUDIO_CODEC_MAP = {
    "aac": "AAC",
    "aac20": "AAC",
    "ac3": "AC3",
    "dd": "DD",
    "dd+": "DDP",
    "ddp": "DDP",
    "ddp51": "DDP5.1",
    "dolbydigitalpluswithdolbyatmos": "DDP",
    "dolbydigitalplus": "DDP",
    "dolbydigital": "DD",
    "truehd": "TrueHD",
    "dolbytruehdwithdolbyatmos": "TrueHD",
    "dolbytruehd": "TrueHD",
    "atmos": "Atmos",
    "dts": "DTS",
    "dtshdma": "DTS-HD.MA",
    "dtshdmasteraudio": "DTS-HD.MA",
    "flac": "FLAC",
    "lpcm": "LPCM",
}

TYPE_MAP = {
    "webdl": "WEB-DL",
    "webrip": "WEBRip",
    "bluray": "BluRay",
    "uhdbluray": "UHD.BluRay",
    "uhdblurayremux": "UHD.BluRay.REMUX",
    "blurayremux": "BluRay.REMUX",
    "remux": "REMUX",
    "hdtv": "HDTV",
    "encode": "Encode",
}

HDR_MAP = {
    "dv": "DV",
    "dovi": "DV",
    "dolbyvision": "DV",
    "hdr": "HDR",
    "hdr10": "HDR10",
    "hdr10+": "HDR10Plus",
    "hdr10plus": "HDR10Plus",
    "dvhdr": "DV.HDR",
}


def build_release_stem(
    metadata: RenameMetadata,
    tokens: TechnicalTokens,
    episode: Optional[str] = None,
    codec_map: Optional[CodecTokenMap] = None,
) -> str:
    title = normalize_title(metadata.title)
    season_or_episode = normalize_token(episode or metadata.season or "")
    year = normalize_token(str(metadata.year or ""))
    video_codec = normalize_video_codec(tokens.video_codec)
    audio_codec = normalize_audio_codec(tokens.audio_codec)
    if codec_map:
        video_codec = apply_codec_token_map(video_codec, codec_map.video)
        audio_codec = apply_codec_token_map(audio_codec, codec_map.audio)
    parts = [
        title,
        season_or_episode,
        year,
        normalize_token(tokens.edition),
        normalize_resolution(tokens.resolution),
        normalize_token(tokens.source).upper(),
        normalize_type(tokens.release_type),
        video_codec,
        normalize_hdr(tokens.hdr),
        audio_codec,
    ]
    stem = ".".join(part for part in parts if part)
    stem = _clean_dotted(stem)
    uploader = normalize_uploader(tokens.uploader)
    if uploader:
        stem = f"{stem}-{uploader}" if stem else uploader
    return stem


def normalize_title(title: str) -> str:
    cleaned = _strip_illegal(str(title or ""))
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(r"[\[\]{}()（）【】]+", " ", cleaned)
    cleaned = SPACE_RE.sub(" ", cleaned).strip(" .")
    cleaned = cleaned.replace(" ", ".")
    return _clean_dotted(cleaned)


def normalize_token(value: str) -> str:
    cleaned = _strip_illegal(str(value or ""))
    cleaned = cleaned.strip(" ._-")
    cleaned = SPACE_RE.sub(".", cleaned)
    return _clean_dotted(cleaned)


def normalize_uploader(value: str) -> str:
    cleaned = normalize_token(value)
    return cleaned.lstrip("-@")


def normalize_resolution(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lower = text.lower()
    if re.fullmatch(r"\d{3,4}[pi]", lower):
        return lower
    match = re.fullmatch(r"(\d{3,5})x(\d{3,5})", lower)
    if match:
        width = int(match.group(1))
        height = int(match.group(2))
        suffix = "p"
        if width >= 3000 or height >= 1500:
            return "2160p"
        if width >= 1800 or height >= 760:
            return "1080p"
        if width >= 1200 or height >= 540:
            return "720p"
        if height in {480, 576, 720, 1080, 2160, 4320}:
            return f"{height}{suffix}"
    if lower == "4k":
        return "2160p"
    if lower == "8k":
        return "4320p"
    return normalize_token(text)


def normalize_type(value: str) -> str:
    text = _key(value)
    if not text:
        return ""
    return TYPE_MAP.get(text, normalize_token(value))


def normalize_video_codec(value: str) -> str:
    text = _key(value)
    if not text:
        return ""
    return VIDEO_CODEC_MAP.get(text, normalize_token(value))


def normalize_audio_codec(value: str) -> str:
    text = _key(value)
    if not text:
        return ""
    return AUDIO_CODEC_MAP.get(text, normalize_token(value))


def normalize_hdr(value: str) -> str:
    text = _key(value)
    if not text:
        return ""
    return HDR_MAP.get(text, normalize_token(value))


def apply_codec_token_map(value: str, mapping: dict) -> str:
    if not value or not mapping:
        return value
    mapped = mapping.get(value)
    if mapped is None:
        mapped = mapping.get(_key(value))
    if mapped is None:
        return value
    return normalize_token(mapped)


def first_non_empty(values: Iterable[str]) -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def _strip_illegal(value: str) -> str:
    return ILLEGAL_FILENAME_CHARS.sub(" ", value)


def _clean_dotted(value: str) -> str:
    value = re.sub(r"\s*\.\s*", ".", value)
    value = DOTS_RE.sub(".", value)
    return value.strip(" .")


def _key(value: str) -> str:
    return re.sub(r"[\s._-]+", "", str(value or "").strip().lower()).strip()
