import argparse
from configparser import RawConfigParser
from pathlib import Path

from loguru import logger

from differential.constants import (
    BOOLEAN_ARGS,
    BOOLEAN_STATES,
    ImageHosting,
    SCREENSHOT_TONEMAP_STATES,
)
from differential.plugin_register import REGISTERED_PLUGINS


def parse_screenshot_tonemap(value) -> str:
    if isinstance(value, bool):
        return "always" if value else "never"
    mode = SCREENSHOT_TONEMAP_STATES.get(str(value or "").strip().lower())
    if mode:
        return mode
    logger.warning(f"Unknown screenshot_tonemap value {value!r}; using auto")
    return "auto"


def merge_config(args: argparse.Namespace, section: str = '') -> dict:
    merged = {}
    config = None
    if hasattr(args, 'config'):
        config_path = Path(args.config)
        if config_path.is_file():
            config = RawConfigParser()
            with open(config_path, 'r', encoding='utf-8') as f:
                config.read_file(f)
        elif args.config != 'config.ini':
            raise FileNotFoundError(f"config file does not exist: {args.config}")

    if config:
        allowed_keys = _allowed_config_keys(args)
        # First use the args in the general section
        for arg in config.defaults().keys():
            _validate_config_key(arg, allowed_keys)
            merged[arg] = config.defaults()[arg]

        # Then use the args from config file matching the plugin name
        if args.plugin in config.sections():
            for arg in config[args.plugin].keys():
                _validate_config_key(arg, allowed_keys)
                merged[arg] = config[args.plugin][arg]

        if section:
            if section not in config.sections():
                logger.warning(f"Section {section} not found in config! Skipping...")
            else:
                for arg in config[section].keys():
                    _validate_config_key(arg, allowed_keys)
                    merged[arg] = config[section][arg]

    # Args from command line has the highest priority
    for arg in vars(args):
        merged[arg] = getattr(args, arg)

    # The CLI exposes these as a mutually-exclusive group. If one is present,
    # it should override the other value that may have come from config.
    if getattr(args, "easy_upload", False):
        merged["auto_feed"] = False
    if getattr(args, "auto_feed", False):
        merged["easy_upload"] = False

    # Handling non-str non-int args
    if 'image_hosting' in merged:
        merged['image_hosting'] = ImageHosting.parse(merged['image_hosting'])
    if any(arg in BOOLEAN_ARGS for arg in merged.keys()):
        for arg in BOOLEAN_ARGS:
            if arg in merged and not isinstance(merged[arg], bool):
                merged[arg] = _parse_bool(arg, merged[arg])
    if "screenshot_tonemap" in merged:
        merged["screenshot_tonemap"] = parse_screenshot_tonemap(
            merged["screenshot_tonemap"]
        )

    # Parse int args
    for arg in merged:
        if isinstance(merged[arg], str) and merged[arg].isdigit():
            merged[arg] = int(merged[arg])
    return merged


def _allowed_config_keys(args: argparse.Namespace) -> set[str]:
    allowed = set(vars(args))
    plugin_name = getattr(args, "plugin", "")
    plugin_cls = REGISTERED_PLUGINS.get(plugin_name)
    if plugin_cls:
        parser = argparse.ArgumentParser(add_help=False)
        plugin_cls.add_parser(parser)
        allowed.update(
            action.dest
            for action in parser._actions
            if action.dest and action.dest != argparse.SUPPRESS
        )
    return allowed


def _validate_config_key(key: str, allowed_keys: set[str]) -> None:
    if key not in allowed_keys:
        raise ValueError(f"unsupported config key: {key}")


def _parse_bool(key: str, value) -> bool:
    normalized = str(value).strip().lower()
    if normalized not in BOOLEAN_STATES:
        valid = ", ".join(sorted(BOOLEAN_STATES))
        raise ValueError(f"invalid boolean value for {key}: {value!r}; valid values: {valid}")
    return BOOLEAN_STATES[normalized]
