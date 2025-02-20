import re
import sys
from pathlib import Path

from loguru import logger

from differential.version import version
from differential.commands import PRE_PARSER, PARSER
from differential.utils.config import merge_config
from differential.plugin_register import REGISTERED_PLUGINS
from differential.plugin_loader import load_plugins_from_dir, load_plugin_from_file

@logger.catch
def main():
    known_args, remaining_argv = PRE_PARSER.parse_known_args()
    load_plugins_from_dir(Path(__file__).resolve().parent.joinpath("plugins"))
    if known_args.plugin:
        load_plugin_from_file(known_args.plugin)
    elif known_args.plugin_folder:
        load_plugins_from_dir(known_args.plugin_folder)

    args = PARSER.parse_args(remaining_argv)
    logger.info("Differential 差速器 {}".format(version))
    config = merge_config(args, args.section)

    if 'log' in config:
        log = config.pop('log')
        logger.add(log, level="TRACE", backtrace=True, diagnose=True)

    logger.debug("Config: {}".format(config))
    if hasattr(args, 'plugin'):
        plugin = config.pop('plugin')
        try:
            logger.trace(config)
            REGISTERED_PLUGINS[plugin](**config).upload()
        except TypeError as e:
            m = re.search(r'missing \d+ required positional argument[s]{0,1}: (.*?)$', str(e))
            if m:
                logger.error("缺少插件必需的参数，请检查输入的参数: {}".format(m.groups()[0]))
                return
            raise e
    else:
        PARSER.print_help()


if __name__ == '__main__':
    main()
