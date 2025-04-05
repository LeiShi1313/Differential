import argparse
from differential.version import version

PRE_PARSER = argparse.ArgumentParser(add_help=False)
PRE_PARSER.add_argument(
    "--plugin",
    type=str,
    help="使用指定的插件",
    default=None
)
PRE_PARSER.add_argument(
    "--plugin-folder",
    type=str,
    help="使用指定的插件目录",
    default=None
)

PARSER = argparse.ArgumentParser(description="Differential - 差速器 PT快速上传工具")
PARSER.add_argument(
    "-v",
    "--version",
    help="显示差速器当前版本",
    action="version",
    version=f"Differential {version}",
)
PARSER.add_argument(
    "--section", default="", help="指定config的section，差速器配置会依次从默认、插件默认和指定section读取并覆盖"
)
subparsers = PARSER.add_subparsers(help="使用下列插件名字来查看插件的详细用法")