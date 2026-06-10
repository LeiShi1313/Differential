import argparse
import json
import sys
from pathlib import Path

from differential.utils.rename.apply import apply_plan
from differential.utils.media_name import parse_media_name
from differential.utils.rename.config import apply_rename_config, finalize_rename_args, load_rename_config
from differential.utils.rename.formatter import first_non_empty
from differential.utils.rename.metadata import fetch_url_metadata, manual_metadata, normalize_episode, normalize_season
from differential.utils.rename.models import TechnicalTokens
from differential.utils.rename.plan import RenamePlanError, build_rename_plan
from differential.utils.rename.prompt import choose_optional, confirm_apply, print_plan
from differential.utils.rename.scan import scan_media
from differential.utils.rename.tokens import suggest_tokens


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rename media release folders using Differential scan and PtGen data.")
    parser.add_argument("path", help="Media folder or media file to rename")
    parser.add_argument("-c", "--config", help="Config file; default uses ./config.ini when it exists")
    parser.add_argument("-u", "--url", help="Douban, IMDb, or PtGen-supported URL")
    parser.add_argument("--title", help="Manual canonical title")
    parser.add_argument("--year", help="Manual release year")
    parser.add_argument("--season", help="Manual season token, e.g. S01")
    parser.add_argument("--episode", help="Manual episode token, e.g. E03")
    parser.add_argument("--source", help="Optional source token, e.g. NF or AMZN")
    parser.add_argument("--uploader", help="Optional uploader/release group")
    parser.add_argument("--type", dest="release_type", help="Optional release type, e.g. WEB-DL or REMUX")
    parser.add_argument("--video-codec", help="Override inferred video codec")
    parser.add_argument("--audio-codec", help="Override inferred audio codec")
    parser.add_argument("--resolution", help="Override inferred resolution")
    parser.add_argument("--edition", help="Optional edition token")
    parser.add_argument("--hdr", help="Optional HDR token")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and never rename files")
    parser.add_argument("--yes", action="store_true", help="Apply without prompts")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable plan")
    sidecar_group = parser.add_mutually_exclusive_group()
    sidecar_group.add_argument(
        "--include-info-sidecars",
        action="store_true",
        default=None,
        help="Rename exact-stem .nfo, .txt, and .log sidecars",
    )
    sidecar_group.add_argument(
        "--no-include-info-sidecars",
        action="store_false",
        dest="include_info_sidecars",
        default=None,
        help="Do not rename exact-stem .nfo, .txt, and .log sidecars",
    )
    folder_group = parser.add_mutually_exclusive_group()
    folder_group.add_argument("--folder-only", action="store_true", default=None, help="Rename only the top folder")
    folder_group.add_argument(
        "--no-folder-only",
        action="store_false",
        dest="folder_only",
        default=None,
        help="Rename the top folder and planned media files",
    )
    bdinfo_group = parser.add_mutually_exclusive_group()
    bdinfo_group.add_argument(
        "--scan-bdinfo",
        action="store_true",
        dest="scan_bdinfo",
        default=None,
        help="Scan BDInfo while planning",
    )
    bdinfo_group.add_argument(
        "--no-scan-bdinfo",
        action="store_false",
        dest="scan_bdinfo",
        default=None,
        help="Skip BDInfo scan while planning",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_rename_config(args.config)
        apply_rename_config(args, config)
        validate_args(args, parser)
        plan, scan = build_plan_from_args(args)
        if args.dry_run:
            return _finish_without_apply(args, plan)
        if args.yes:
            applied = apply_plan(plan)
            return _finish_after_apply(args, plan, applied)
        print_plan(plan)
        if not confirm_apply():
            print("Aborted.")
            return 1
        applied = apply_plan(plan)
        return _finish_after_apply(args, plan, applied)
    except (RenamePlanError, ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        if "scan" in locals() and getattr(scan, "handler", None):
            scan.handler.cleanup()


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    has_url = bool(args.url)
    has_manual = bool(args.title and args.year)
    if has_url and (args.title or args.year):
        parser.error("use either --url or --title --year, not both")
    if has_url and has_manual:
        parser.error("use either --url or --title --year, not both")
    if not has_url and not has_manual:
        parser.error("provide either --url or --title --year")
    if bool(args.title) != bool(args.year) and not args.url:
        parser.error("--title and --year must be provided together")


def build_plan_from_args(args: argparse.Namespace):
    finalize_rename_args(args)
    path = Path(args.path)
    if not path.exists():
        raise RenamePlanError(f"input path does not exist: {path}")

    scan = scan_media(path, scan_bdinfo=args.scan_bdinfo)
    metadata = _metadata_from_args(args)
    suggestions = suggest_tokens(path)
    tokens = _tokens_from_args(args, scan, suggestions, prompts_allowed=should_prompt(args))
    plan = build_rename_plan(
        scan,
        metadata,
        tokens,
        include_info_sidecars=args.include_info_sidecars,
        folder_only=args.folder_only,
        codec_map=args.rename_codec_map,
    )
    return plan, scan


def should_prompt(args: argparse.Namespace) -> bool:
    return (
        not args.yes
        and not args.json
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    )


def _metadata_from_args(args: argparse.Namespace):
    if args.title and args.year:
        season, episode = _season_episode_from_args_or_path(args)
        return manual_metadata(args.title, args.year, season, episode)

    metadata, _ptgen, _douban, _imdb = fetch_url_metadata(args.url)
    season, episode = _season_episode_from_args_or_path(args)
    if season:
        metadata.season = normalize_season(season)
        metadata.kind = "tv"
    if episode:
        metadata.episode = normalize_episode(episode)
        metadata.kind = "tv"
    if not metadata.title:
        raise RenamePlanError("could not determine title from metadata")
    if not metadata.year:
        raise RenamePlanError("could not determine year from metadata")
    return metadata


def _season_episode_from_args_or_path(args: argparse.Namespace) -> tuple[str, str]:
    if args.season or args.episode:
        return args.season or "", args.episode or ""
    parsed = parse_media_name(args.path)
    return parsed.season_text or "", parsed.episode_text or ""


def _tokens_from_args(args: argparse.Namespace, scan, suggestions, prompts_allowed: bool) -> TechnicalTokens:
    source = args.source or ""
    uploader = args.uploader or ""
    if prompts_allowed and not source:
        source = choose_optional("source", suggestions.sources)
    if prompts_allowed and not uploader:
        uploader = choose_optional("uploader", suggestions.uploaders)

    release_type = first_non_empty(
        [
            args.release_type or "",
            scan.release_type or "",
            _first(suggestions.release_types),
        ]
    )
    if prompts_allowed and not (args.release_type or scan.release_type) and suggestions.release_types:
        release_type = choose_optional("type", suggestions.release_types)

    hdr = first_non_empty([args.hdr or "", scan.hdr or "", _first(suggestions.hdr)])
    edition = first_non_empty([args.edition or "", _first(suggestions.editions)])

    return TechnicalTokens(
        resolution=args.resolution or scan.resolution or "",
        source=source,
        release_type=release_type,
        video_codec=args.video_codec or scan.video_codec or "",
        hdr=hdr,
        audio_codec=args.audio_codec or scan.audio_codec or "",
        edition=edition,
        uploader=uploader,
    )


def _finish_without_apply(args: argparse.Namespace, plan) -> int:
    if args.json:
        print(_json_payload(plan, applied=[]))
    else:
        print_plan(plan)
    return 0


def _finish_after_apply(args: argparse.Namespace, plan, applied) -> int:
    if args.json:
        print(_json_payload(plan, applied=applied))
    else:
        print(f"Applied {len(applied)} rename operation(s).")
    return 0


def _json_payload(plan, applied) -> str:
    payload = plan.to_dict()
    payload["applied"] = [operation.to_dict() for operation in applied]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _first(values) -> str:
    return next(iter(values), "") if values else ""


if __name__ == "__main__":
    raise SystemExit(main())
