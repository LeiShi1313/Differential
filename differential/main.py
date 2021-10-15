import re

from loguru import logger

from differential.version import version
from differential.utils.config import merge_config
from differential.plugins.base import PARSER, REGISTERED_PLUGINS


@logger.catch
def main():
    args = PARSER.parse_args()
    logger.info("Differential 差速器 {}".format(version))
    config = merge_config(args)

    if 'log' in config:
        log = config.pop('log')
        logger.add(log, level="TRACE", backtrace=True, diagnose=True)

    if hasattr(args, 'plugin'):
        plugin = config.pop('plugin')
        try:
            logger.trace(config)
            REGISTERED_PLUGINS[plugin](**config).upload()
        except TypeError as e:
            m = re.search(r'missing \d+ required positional arguments: (.*?)$', str(e))
            if m:
                logger.error("缺少插件必需的参数，请检查输入的参数: {}".format(m.groups()[0]))
            else:
                logger.error(e)
    else:
        PARSER.print_help()


if __name__ == '__main__':
    main()
