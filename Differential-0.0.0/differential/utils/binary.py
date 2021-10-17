import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


def find_binary(name: str, alternative_names: list = None) -> Optional[Path]:
    if alternative_names is None:
        alternative_names = []

    path = os.environ.get(f"{name.upper()}PATH")
    if path:
        pp = Path(path)
        if not pp.is_file():
            logger.error(f"{p}不是可执行文件！")
            sys.exit(1)
        return pp
    for n in [name] + alternative_names:
        if n in os.listdir(os.getcwd()):
            return Path(os.getcwd()).joinpath(n)
        _which = shutil.which(n)
        if _which:
            return Path(_which)
        if platform.system() == "Windows":
            if f"{n}.exe" in os.listdir(os.getcwd()):
                return Path(os.getcwd()).joinpath(f"{n}.exe")
            _which = shutil.which(f"{n}.exe")
            if _which:
                return Path(_which)

    logger.error(
        f"{name} not found in path, you can specify its binary location "
        f"by setting environment variable: {name.upper()}PATH or put it under the tool folder."
    )
    return None


def execute(binary_name: str, args: str, abort: bool = False) -> str:
    executable = find_binary(binary_name)
    if executable is None:
        if abort:
            sys.exit(1)
        else:
            return ""
    cmd = f'"{executable}" {args}'
    logger.trace(cmd)
    proc = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    logger.trace(proc)
    return "\n".join([proc.stdout.decode(), proc.stderr.decode()])


def ffmpeg(path: Path, extra_args: str = "") -> str:
    return execute("ffmpeg", f'-i "{path.absolute()}" {extra_args}')


def ffprobe(path: Path) -> str:
    return execute("ffprobe", f'-i "{path.absolute()}"')
