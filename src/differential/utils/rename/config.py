from configparser import RawConfigParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from differential.constants import BOOLEAN_STATES
from differential.utils.rename.formatter import normalize_audio_codec, normalize_token, normalize_video_codec
from differential.utils.rename.models import CodecTokenMap


RENAME_CONFIG_NAME = "config.ini"
RENAME_SECTION = "Rename"
CODEC_MAP_SECTION = "RenameCodecMap"

FIELD_ALIASES = {
    "source": "source",
    "uploader": "uploader",
    "type": "release_type",
    "release_type": "release_type",
    "video_codec": "video_codec",
    "audio_codec": "audio_codec",
    "resolution": "resolution",
    "edition": "edition",
    "hdr": "hdr",
    "season": "season",
    "episode": "episode",
    "include_info_sidecars": "include_info_sidecars",
    "folder_only": "folder_only",
    "scan_bdinfo": "scan_bdinfo",
}
BOOLEAN_FIELDS = {"include_info_sidecars", "folder_only", "scan_bdinfo"}
FINAL_DEFAULTS = {
    "include_info_sidecars": False,
    "folder_only": False,
    "scan_bdinfo": True,
}


@dataclass
class RenameConfig:
    path: Optional[Path] = None
    defaults: Dict[str, object] = field(default_factory=dict)
    codec_map: CodecTokenMap = field(default_factory=CodecTokenMap)


def load_rename_config(config_path: Optional[str], cwd: Optional[Path] = None) -> RenameConfig:
    path = _resolve_config_path(config_path, cwd)
    if path is None:
        return RenameConfig()

    parser = RawConfigParser()
    parser.optionxform = str
    with path.open("r", encoding="utf-8") as handle:
        parser.read_file(handle)

    defaults = _parse_rename_defaults(parser)
    codec_map = _parse_codec_map(parser)
    return RenameConfig(path=path, defaults=defaults, codec_map=codec_map)


def apply_rename_config(args, config: RenameConfig) -> None:
    for key, value in config.defaults.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    setattr(args, "rename_config_path", config.path)
    setattr(args, "rename_codec_map", config.codec_map)
    finalize_rename_args(args)


def finalize_rename_args(args) -> None:
    for key, value in FINAL_DEFAULTS.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if not hasattr(args, "rename_codec_map"):
        setattr(args, "rename_codec_map", CodecTokenMap())


def _resolve_config_path(config_path: Optional[str], cwd: Optional[Path]) -> Optional[Path]:
    if config_path:
        path = Path(config_path).expanduser()
        if not path.exists():
            raise ValueError(f"config file does not exist: {path}")
        return path

    base = Path.cwd() if cwd is None else Path(cwd)
    candidate = base / RENAME_CONFIG_NAME
    return candidate if candidate.exists() else None


def _parse_rename_defaults(parser: RawConfigParser) -> Dict[str, object]:
    if not parser.has_section(RENAME_SECTION):
        return {}

    defaults: Dict[str, object] = {}
    for key, value in _section_items(parser, RENAME_SECTION):
        normalized_key = key.strip().lower().replace("-", "_")
        if normalized_key not in FIELD_ALIASES:
            raise ValueError(f"unsupported [{RENAME_SECTION}] config key: {key}")
        field_name = FIELD_ALIASES[normalized_key]
        if field_name in BOOLEAN_FIELDS:
            defaults[field_name] = _parse_bool(value, key)
        else:
            defaults[field_name] = str(value).strip()
    return defaults


def _parse_codec_map(parser: RawConfigParser) -> CodecTokenMap:
    if not parser.has_section(CODEC_MAP_SECTION):
        return CodecTokenMap()

    video: Dict[str, str] = {}
    audio: Dict[str, str] = {}
    for key, value in _section_items(parser, CODEC_MAP_SECTION):
        prefix, source_token = _split_codec_map_key(key)
        target_token = normalize_token(value)
        if prefix == "video":
            video[normalize_video_codec(source_token)] = target_token
        elif prefix == "audio":
            audio[normalize_audio_codec(source_token)] = target_token
        else:
            raise ValueError(f"unsupported [{CODEC_MAP_SECTION}] config key prefix: {key}")
    return CodecTokenMap(video=video, audio=audio)


def _section_items(parser: RawConfigParser, section: str) -> Iterable[Tuple[str, str]]:
    raw_section = parser._sections.get(section, {})
    return ((key, value) for key, value in raw_section.items() if key != "__name__")


def _split_codec_map_key(key: str) -> Tuple[str, str]:
    if "." not in key:
        raise ValueError(f"[{CODEC_MAP_SECTION}] keys must look like video.H.264 or audio.AAC2.0: {key}")
    prefix, source_token = key.split(".", 1)
    prefix = prefix.strip().lower()
    source_token = source_token.strip()
    if not prefix or not source_token:
        raise ValueError(f"invalid [{CODEC_MAP_SECTION}] key: {key}")
    return prefix, source_token


def _parse_bool(value, key: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized not in BOOLEAN_STATES:
        raise ValueError(f"invalid boolean value for [{RENAME_SECTION}] {key}: {value}")
    return BOOLEAN_STATES[normalized]
