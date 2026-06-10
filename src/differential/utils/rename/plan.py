import re
from pathlib import Path
from typing import Optional

from differential.utils.media_name import SUBTITLE_EXTENSIONS
from differential.utils.rename.formatter import build_release_stem
from differential.utils.rename.metadata import normalize_episode, normalize_season
from differential.utils.rename.models import CodecTokenMap, RenameMetadata, RenameOperation, RenamePlan, TechnicalTokens


INFO_SIDECAR_EXTENSIONS = {".nfo", ".txt", ".log"}
SKIP_NAME_RE = re.compile(r"\b(?:sample|trailer|extras?|behind[ ._-]?the[ ._-]?scenes)\b", re.IGNORECASE)
EPISODE_RE = re.compile(r"(?i)(?<![A-Za-z0-9])S(?P<season>\d{1,2})[ ._-]?E(?P<episode>\d{1,3})(?![A-Za-z0-9])")
BARE_EPISODE_RE = re.compile(r"(?i)(?<![A-Za-z0-9])E(?P<episode>\d{1,3})(?![A-Za-z0-9])")
EPISODE_WORD_RE = re.compile(r"(?i)(?<![A-Za-z0-9])Episode[ ._-]*(?P<episode>\d{1,3})(?![A-Za-z0-9])")
CHINESE_EPISODE_RE = re.compile(r"第\s*(?P<episode>\d{1,3})\s*集")
NUMERIC_EPISODE_RE = re.compile(r"^(?P<episode>\d{1,3})(?:[ ._-].*)?$")


class RenamePlanError(Exception):
    pass


def build_rename_plan(
    scan,
    metadata: RenameMetadata,
    tokens: TechnicalTokens,
    include_info_sidecars: bool = False,
    folder_only: bool = False,
    codec_map: Optional[CodecTokenMap] = None,
) -> RenamePlan:
    root = Path(scan.root)
    plan = RenamePlan(root=root, is_bdmv=getattr(scan, "is_bdmv", False))
    base_stem = build_release_stem(metadata, tokens, codec_map=codec_map)
    if not base_stem:
        raise RenamePlanError("generated release name is empty")

    if getattr(scan, "is_direct_file", False):
        if folder_only:
            raise RenamePlanError("--folder-only cannot be used with a direct file input")
        if getattr(scan, "is_bdmv", False):
            plan.warnings.append("BDMV detected inside direct file input; internal files will not be renamed")
        direct_stem = build_release_stem(
            metadata,
            tokens,
            episode=_metadata_episode_marker(metadata) or None,
            codec_map=codec_map,
        )
        _add_file_operation(plan, root, root.with_name(direct_stem + root.suffix))
        validate_plan(plan)
        return plan

    folder_target = root.parent / base_stem
    _add_folder_operation(plan, root, folder_target)

    if folder_only or getattr(scan, "is_bdmv", False):
        if getattr(scan, "is_bdmv", False):
            plan.warnings.append("BDMV detected; internal files will not be renamed")
        validate_plan(plan)
        return plan

    if _is_tv(metadata):
        _add_tv_file_operations(plan, scan, metadata, tokens, include_info_sidecars, codec_map)
    else:
        main_file = Path(scan.main_file)
        _add_file_operation(plan, main_file, main_file.with_name(base_stem + main_file.suffix))
        _add_sidecar_operations(plan, main_file, base_stem, include_info_sidecars)

    validate_plan(plan)
    return plan


def validate_plan(plan: RenamePlan, is_bdmv: Optional[bool] = None) -> None:
    if is_bdmv is None:
        is_bdmv = plan.is_bdmv
    targets = set()
    root = Path(plan.root)
    parent_scope = root.parent if root.is_dir() or root.is_file() else root.parent
    parent_scope_abs = parent_scope.absolute()

    for operation in plan.operations:
        source = Path(operation.source)
        target = Path(operation.target)
        if not source.exists():
            raise RenamePlanError(f"source path does not exist: {source}")
        if source == target:
            raise RenamePlanError(f"no-op rename operation should not be planned: {source}")
        target_key = str(target.absolute())
        if target_key in targets:
            raise RenamePlanError(f"duplicate rename target: {target}")
        targets.add(target_key)
        if target.exists() and source.absolute() != target.absolute():
            raise RenamePlanError(f"target path already exists: {target}")
        try:
            target.absolute().relative_to(parent_scope_abs)
        except ValueError as exc:
            raise RenamePlanError(f"target path is outside the source parent scope: {target}") from exc

        if is_bdmv and operation.kind != "folder" and source != root:
            raise RenamePlanError(f"BDMV plan cannot include internal file rename: {source}")


def _add_tv_file_operations(
    plan: RenamePlan,
    scan,
    metadata: RenameMetadata,
    tokens: TechnicalTokens,
    include_info_sidecars: bool,
    codec_map: Optional[CodecTokenMap],
) -> None:
    media_files = [Path(path) for path in getattr(scan, "media_files", []) if not _should_skip(path)]
    planned = 0
    for media_file in media_files:
        marker = _episode_marker(media_file, metadata)
        if not marker:
            continue
        stem = build_release_stem(metadata, tokens, episode=marker, codec_map=codec_map)
        _add_file_operation(plan, media_file, media_file.with_name(stem + media_file.suffix))
        _add_sidecar_operations(plan, media_file, stem, include_info_sidecars)
        planned += 1

    if planned == 0:
        plan.warnings.append("TV episode identity is unclear; only the folder will be renamed")


def _add_sidecar_operations(
    plan: RenamePlan,
    media_file: Path,
    new_stem: str,
    include_info_sidecars: bool,
) -> None:
    old_stem = media_file.stem
    allowed = set(SUBTITLE_EXTENSIONS)
    if include_info_sidecars:
        allowed.update(INFO_SIDECAR_EXTENSIONS)

    for sidecar in sorted(media_file.parent.iterdir(), key=lambda path: path.name.lower()):
        if not sidecar.is_file() or sidecar == media_file:
            continue
        suffix = sidecar.suffix.lower()
        if suffix not in allowed:
            continue
        preserved = _sidecar_preserved_suffix(sidecar, old_stem, include_info_sidecars)
        if preserved is None:
            continue
        _add_file_operation(plan, sidecar, sidecar.with_name(new_stem + preserved + sidecar.suffix))


def _sidecar_preserved_suffix(sidecar: Path, old_stem: str, include_info_sidecars: bool) -> Optional[str]:
    sidecar_stem = sidecar.name[: -len(sidecar.suffix)] if sidecar.suffix else sidecar.name
    if sidecar_stem == old_stem:
        return ""
    if sidecar.suffix.lower() in INFO_SIDECAR_EXTENSIONS and not include_info_sidecars:
        return None
    prefix = old_stem + "."
    if sidecar_stem.startswith(prefix):
        return sidecar_stem[len(old_stem) :]
    return None


def _add_file_operation(plan: RenamePlan, source: Path, target: Path) -> None:
    if source != target:
        plan.operations.append(RenameOperation(source=source, target=target, kind="file"))


def _add_folder_operation(plan: RenamePlan, source: Path, target: Path) -> None:
    if source != target:
        plan.operations.append(RenameOperation(source=source, target=target, kind="folder"))


def _episode_marker(path: Path, metadata: RenameMetadata) -> str:
    name = path.name
    match = EPISODE_RE.search(name)
    if match:
        return f"S{int(match.group('season')):02d}E{int(match.group('episode')):02d}"

    if metadata.season:
        bare = BARE_EPISODE_RE.search(name)
        if bare:
            return f"{normalize_season(metadata.season)}{normalize_episode(bare.group('episode'))}"

        word = EPISODE_WORD_RE.search(name)
        if word:
            return f"{normalize_season(metadata.season)}{normalize_episode(word.group('episode'))}"

        chinese = CHINESE_EPISODE_RE.search(name)
        if chinese:
            return f"{normalize_season(metadata.season)}{normalize_episode(chinese.group('episode'))}"

        numeric = NUMERIC_EPISODE_RE.match(path.stem)
        if numeric and _is_plausible_episode_number(numeric.group("episode")):
            return f"{normalize_season(metadata.season)}{normalize_episode(numeric.group('episode'))}"

    if metadata.season and metadata.episode:
        return _metadata_episode_marker(metadata)
    return ""


def _metadata_episode_marker(metadata: RenameMetadata) -> str:
    if metadata.season and metadata.episode:
        return f"{normalize_season(metadata.season)}{normalize_episode(metadata.episode)}"
    return ""


def _is_tv(metadata: RenameMetadata) -> bool:
    return metadata.kind == "tv" or bool(metadata.season or metadata.episode)


def _should_skip(path: Path) -> bool:
    return bool(SKIP_NAME_RE.search(Path(path).name))


def _is_plausible_episode_number(value: str) -> bool:
    try:
        number = int(value)
    except ValueError:
        return False
    return 1 <= number <= 200
