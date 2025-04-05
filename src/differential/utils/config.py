import argparse
from configparser import RawConfigParser

from loguru import logger

from differential.constants import ImageHosting, BOOLEAN_ARGS, BOOLEAN_STATES


def merge_config(args: argparse.Namespace, section: str = '') -> dict:
    merged = {}
    config = None
    if hasattr(args, 'config'):
        config = RawConfigParser()
        with open(args.config, 'r', encoding='utf-8') as f:
            config.read_file(f)

    if config:
        # First use the args in the general section
        for arg in config.defaults().keys():
            merged[arg] = config.defaults()[arg]

        # Then use the args from config file matching the plugin name
        if args.plugin in config.sections():
            for arg in config[args.plugin].keys():
                merged[arg] = config[args.plugin][arg]

        if section:
            if section not in config.sections():
                logger.warning(f"Section {section} not found in config! Skipping...")
            else:
                for arg in config[section].keys():
                    merged[arg] = config[section][arg]

    # Args from command line has the highest priority
    for arg in vars(args):
        merged[arg] = getattr(args, arg)

    # Handling non-str non-int args
    if 'image_hosting' in merged:
        merged['image_hosting'] = ImageHosting.parse(merged['image_hosting'])
    if any(arg in BOOLEAN_ARGS for arg in merged.keys()):
        for arg in BOOLEAN_ARGS:
            if arg in merged and not isinstance(merged[arg], bool):
                # Might be buggy to always assume not recognized args is False
                merged[arg] = BOOLEAN_STATES.get(merged[arg], False)

    # Parse int args
    for arg in merged:
        if isinstance(merged[arg], str) and merged[arg].isdigit():
            merged[arg] = int(merged[arg])
    return merged
