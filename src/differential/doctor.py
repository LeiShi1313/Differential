import argparse
import platform
import shutil
import webbrowser
from configparser import RawConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from differential.constants import ImageHosting
from differential.plugin_register import REGISTERED_PLUGINS
from differential.utils.config import merge_config
from differential.utils.mediainfo_handler import BDINFO_BINARY_NAMES, BDINFO_ENV_VAR, _bundled_bdinfo_path


@dataclass(frozen=True)
class Diagnostic:
    name: str
    status: str
    message: str


def run_doctor(args: argparse.Namespace) -> int:
    diagnostics = collect_diagnostics(args)
    for diagnostic in diagnostics:
        print(f"[{diagnostic.status.upper()}] {diagnostic.name}: {diagnostic.message}")
    return 1 if any(diagnostic.status == "fail" for diagnostic in diagnostics) else 0


def collect_diagnostics(args: argparse.Namespace) -> list[Diagnostic]:
    diagnostics = [
        _check_binary("ffmpeg", "ffmpeg"),
        _check_binary("mediainfo", "mediainfo"),
        _check_bdinfo(),
        _check_browser(),
    ]
    config_diagnostic, merged_config = _check_config(args)
    diagnostics.append(config_diagnostic)
    diagnostics.append(_check_image_host_config(merged_config))
    return diagnostics


def _check_binary(name: str, command: str) -> Diagnostic:
    path = shutil.which(command)
    if path:
        return Diagnostic(name, "ok", path)
    return Diagnostic(name, "fail", f"{command} not found in PATH")


def _check_bdinfo() -> Diagnostic:
    env_path = _bdinfo_env_path()
    if env_path is not None:
        if env_path.is_file():
            return Diagnostic("BDInfo", "ok", f"{BDINFO_ENV_VAR}={env_path}")
        return Diagnostic("BDInfo", "fail", f"{BDINFO_ENV_VAR} points to a missing file: {env_path}")

    for name in BDINFO_BINARY_NAMES:
        cwd_candidate = Path.cwd().joinpath(name)
        if cwd_candidate.is_file():
            return Diagnostic("BDInfo", "ok", str(cwd_candidate))

        path = shutil.which(name)
        if path:
            return Diagnostic("BDInfo", "ok", path)

    bundled = _bundled_bdinfo_path()
    if platform.system() == "Windows" and bundled.is_file():
        return Diagnostic("BDInfo", "ok", f"bundled {bundled}")

    if bundled.is_file():
        mono = shutil.which("mono")
        if mono:
            return Diagnostic("BDInfo", "ok", f"Mono fallback: {mono}")
        return Diagnostic("BDInfo", "fail", "native BDInfo not found and Mono fallback is unavailable")

    return Diagnostic("BDInfo", "fail", "BDInfo binary not found")


def _bdinfo_env_path() -> Optional[Path]:
    import os

    value = os.environ.get(BDINFO_ENV_VAR)
    return Path(value) if value else None


def _check_browser() -> Diagnostic:
    try:
        browser = webbrowser.get()
    except webbrowser.Error as exc:
        return Diagnostic("browser", "warn", f"no browser available: {exc}")
    if isinstance(browser, webbrowser.GenericBrowser):
        return Diagnostic("browser", "warn", "only a generic browser launcher is available")
    return Diagnostic("browser", "ok", browser.name or browser.__class__.__name__)


def _check_config(args: argparse.Namespace) -> tuple[Diagnostic, Optional[dict]]:
    config_path = Path(args.config)
    plugin = getattr(args, "doctor_plugin", "") or ""
    section = getattr(args, "doctor_section", "") or ""

    if not config_path.is_file():
        if args.config == "config.ini":
            return Diagnostic("config", "warn", "config.ini not found; skipped config validation"), None
        return Diagnostic("config", "fail", f"config file does not exist: {config_path}"), None

    if not plugin:
        try:
            parser = RawConfigParser()
            with open(config_path, "r", encoding="utf-8") as config_file:
                parser.read_file(config_file)
        except Exception as exc:
            return Diagnostic("config", "fail", str(exc)), None
        return Diagnostic("config", "warn", "syntax OK; provide a plugin name to validate keys"), None

    if plugin not in REGISTERED_PLUGINS:
        return Diagnostic("config", "fail", f"unknown plugin: {plugin}"), None

    try:
        plugin_name = REGISTERED_PLUGINS[plugin].__name__
        merged = merge_config(argparse.Namespace(config=str(config_path), plugin=plugin_name), section)
    except Exception as exc:
        return Diagnostic("config", "fail", str(exc)), None

    message = f"{config_path}"
    if section:
        message += f" section={section}"
    return Diagnostic("config", "ok", message), merged


def _check_image_host_config(config: Optional[dict]) -> Diagnostic:
    if config is None:
        return Diagnostic("image host config", "warn", "skipped")

    image_hosting = config.get("image_hosting")
    if not image_hosting:
        return Diagnostic("image host config", "warn", "image_hosting is not configured")

    if isinstance(image_hosting, str):
        try:
            image_hosting = ImageHosting.parse(image_hosting)
        except ValueError as exc:
            return Diagnostic("image host config", "fail", str(exc))

    missing = _missing_image_host_keys(image_hosting, config)
    if missing:
        return Diagnostic(
            "image host config",
            "fail",
            f"{image_hosting.value} missing required config: {', '.join(missing)}",
        )
    return Diagnostic("image host config", "ok", image_hosting.value)


def _missing_image_host_keys(image_hosting: ImageHosting, config: dict) -> list[str]:
    if image_hosting == ImageHosting.PTPIMG:
        return _missing(config, ["ptpimg_api_key"])
    if image_hosting == ImageHosting.HDB:
        return _missing(config, ["hdbits_cookie"])
    if image_hosting == ImageHosting.CHEVERETO:
        missing = _missing(config, ["chevereto_hosting_url"])
        if not config.get("chevereto_api_key") and not (
            config.get("chevereto_username") and config.get("chevereto_password")
        ):
            missing.append("chevereto_api_key or chevereto_username+chevereto_password")
        return missing
    if image_hosting == ImageHosting.IMGURL:
        return _missing(config, ["imgurl_hosting_url", "imgurl_api_key"])
    if image_hosting == ImageHosting.SMMS:
        return _missing(config, ["smms_api_key"])
    if image_hosting == ImageHosting.BYR:
        return _missing(config, ["byr_cookie"])
    if image_hosting == ImageHosting.CLOUDINARY:
        return _missing(config, ["cloudinary_cloud_name", "cloudinary_api_key", "cloudinary_api_secret"])
    if image_hosting == ImageHosting.LSKY:
        missing = _missing(config, ["lsky_hosting_url"])
        if not config.get("lsky_token") and not (config.get("lsky_email") and config.get("lsky_password")):
            missing.append("lsky_token or lsky_email+lsky_password")
        return missing
    return []


def _missing(config: dict, keys: list[str]) -> list[str]:
    return [key for key in keys if not config.get(key)]
