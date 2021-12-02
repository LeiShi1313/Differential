import os
import re
import sys
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


def find_binary(name: str, alternative_names: list = None) -> Optional[Path]:
    if alternative_names is None:
        alternative_names = []

    if Path(name).is_file():
        return name

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

def build_cmd(binary_name: str, args: str, abort: bool = False) -> str:
    executable = find_binary(binary_name)
    if executable is None:
        if abort:
            sys.exit(1)
        else:
            return ""
    cmd = f'"{executable}" {args}'
    logger.trace(cmd)
    return cmd

def execute_with_output(binary_name: str, args: str, abort: bool = False) -> int:
    cmd = build_cmd(binary_name, args, abort)
    return_code = 0

    def _execute():
        proc = subprocess.Popen(cmd, shell=True, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     universal_newlines=True)
        for stdout in iter(proc.stdout.readline, ""):
            yield stdout
        proc.stdout.close()
        return_code = proc.wait()
    prev = ''
    for out in iter(_execute()):
        out = out.strip()
        if re.sub('(\d| )', '', out) != re.sub('(\d| )', '', prev):
            print(out)
        else:
            print(out, end='\r')
        sys.stdout.flush()
        prev = out
    if return_code != 0:
        logger.warning(f"{binary_name} exit with return code {return_code}")
    return return_code
    

def execute(binary_name: str, args: str, abort: bool = False) -> str:
    cmd = build_cmd(binary_name, args, abort)
    proc = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.trace(proc)
    ret = "\n".join([proc.stdout.decode(), proc.stderr.decode()])
    if proc.returncode != 0:
        logger.warning(f"{binary_name} exit with return code {proc.returncode}:\n{ret}")
    return ret


def ffmpeg(path: Path, extra_args: str = "") -> str:
    return execute("ffmpeg", f'-i "{path.absolute()}" {extra_args}')


def ffprobe(path: Path) -> str:
    return execute("ffprobe", f'-i "{path.absolute()}"')
