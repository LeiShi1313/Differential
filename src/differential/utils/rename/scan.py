from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from differential.utils.media_name import MEDIA_EXTENSIONS
from differential.utils.mediainfo_handler import MediaInfoHandler
from differential.utils.rename.formatter import normalize_audio_codec, normalize_resolution, normalize_video_codec


@dataclass
class RenameScan:
    root: Path
    main_file: Path
    media_files: List[Path] = field(default_factory=list)
    is_bdmv: bool = False
    is_direct_file: bool = False
    resolution: str = ""
    video_codec: str = ""
    audio_codec: str = ""
    hdr: str = ""
    release_type: str = ""
    handler: Optional[MediaInfoHandler] = None


def scan_media(path: Path, scan_bdinfo: bool = True) -> RenameScan:
    path = Path(path)
    handler = MediaInfoHandler(
        folder=path,
        create_folder=False,
        use_short_bdinfo=False,
        scan_bdinfo=scan_bdinfo,
    )
    main_file = handler.find_mediainfo()
    root = path
    media_files = [path] if path.is_file() else _find_media_files(path)
    resolution = handler.resolution or ""
    return RenameScan(
        root=root,
        main_file=main_file,
        media_files=media_files,
        is_bdmv=handler.is_bdmv,
        is_direct_file=path.is_file(),
        resolution=resolution,
        video_codec=extract_video_codec(handler.tracks),
        audio_codec=extract_audio_codec(handler.tracks),
        hdr=extract_hdr(handler.tracks),
        release_type=_disc_release_type(resolution) if handler.is_bdmv else "",
        handler=handler,
    )


def extract_video_codec(tracks) -> str:
    for track in tracks:
        if getattr(track, "track_type", "") != "Video":
            continue
        encoded_library = getattr(track, "encoded_library_name", None)
        if encoded_library:
            normalized_library = normalize_video_codec(encoded_library)
            if normalized_library in {"x264", "x265"}:
                return normalized_library
        for attr in ("commercial_name", "format", "codec_id"):
            value = getattr(track, attr, None)
            if value:
                normalized = normalize_video_codec(value)
                if normalized:
                    return normalized
    return ""


def extract_audio_codec(tracks) -> str:
    candidates = []
    for track in tracks:
        if getattr(track, "track_type", "") != "Audio":
            continue
        base = ""
        if getattr(track, "format_info", None) == "Audio Coding 3":
            base = "AC3"
        elif getattr(track, "format_info", None) == "Free Lossless Audio Codec":
            base = "FLAC"
        else:
            for attr in ("commercial_name", "format", "format_info"):
                value = getattr(track, attr, None)
                if value:
                    base = normalize_audio_codec(value)
                    if base:
                        break
        channels = _audio_channels(track)
        if base:
            codec = _with_channels(base, channels)
            if _has_atmos(track) and "Atmos" not in codec:
                codec = f"{codec}.Atmos"
            candidates.append((_audio_rank(codec), codec))
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return ""


def extract_hdr(tracks) -> str:
    values = []
    for track in tracks:
        if getattr(track, "track_type", "") != "Video":
            continue
        for attr in (
            "hdr_format",
            "commercial_name",
            "transfer_characteristics",
            "color_primaries",
        ):
            value = getattr(track, attr, None)
            if value:
                values.append(str(value))
    text = " ".join(values).lower()
    if "dolby vision" in text or "dovi" in text:
        if "hdr" in text:
            return "DV.HDR"
        return "DV"
    if "hdr10+" in text or "hdr10plus" in text:
        return "HDR10Plus"
    if "hdr10" in text:
        return "HDR10"
    if "hdr" in text or "smpte st 2084" in text:
        return "HDR"
    return ""


def _audio_channels(track: Any) -> str:
    for attr in ("channel_s", "channels"):
        value = getattr(track, attr, None)
        normalized = _normalize_channels(value)
        if normalized:
            return normalized
    other = getattr(track, "other_channel_s", None)
    if other:
        for value in other:
            normalized = _normalize_channels(value)
            if normalized:
                return normalized
    return ""


def _normalize_channels(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if "7.1" in text or text == "8":
        return "7.1"
    if "5.1" in text or text == "6":
        return "5.1"
    if "2.0" in text or text == "2":
        return "2.0"
    if "1.0" in text or text == "1":
        return "1.0"
    return ""


def _with_channels(base: str, channels: str) -> str:
    if not channels:
        return base
    if base in {"AAC", "AC3", "DD", "DDP", "DTS", "TrueHD", "DTS-HD.MA", "FLAC", "LPCM"}:
        return f"{base}{channels}"
    return base


def _has_atmos(track: Any) -> bool:
    values = []
    for attr in ("commercial_name", "format", "format_info", "title"):
        value = getattr(track, attr, None)
        if value:
            values.append(str(value))
    return "atmos" in " ".join(values).lower()


def _audio_rank(codec: str) -> int:
    text = codec.lower()
    if "truehd" in text and "atmos" in text:
        return 100
    if "dts-hd.ma" in text:
        return 90
    if "truehd" in text:
        return 85
    if "ddp" in text and "atmos" in text:
        return 80
    if "dts" in text:
        return 70
    if "ddp" in text:
        return 60
    if "ac3" in text or "dd" in text:
        return 50
    if "aac" in text:
        return 40
    if "flac" in text:
        return 35
    if "lpcm" in text or "pcm" in text:
        return 30
    return 10


def _disc_release_type(resolution: str) -> str:
    return "UHD.BluRay" if normalize_resolution(resolution) == "2160p" else "BluRay"


def _find_media_files(root: Path) -> List[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
        ),
        key=lambda path: path.as_posix().lower(),
    )
