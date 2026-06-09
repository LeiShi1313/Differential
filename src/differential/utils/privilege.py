import shutil
import subprocess
import sys
from typing import List

from loguru import logger


def _run(cmd: List[str], *, capture: bool) -> subprocess.CompletedProcess:
    logger.trace(" ".join(cmd))
    try:
        if capture:
            return subprocess.run(cmd, text=True, capture_output=True)
        return subprocess.run(cmd)
    except FileNotFoundError as e:
        return subprocess.CompletedProcess(cmd, 127, stderr=str(e))


def _sudo_auth_required(proc: subprocess.CompletedProcess) -> bool:
    stderr = (proc.stderr or "").lower()
    auth_markers = (
        "a password is required",
        "password is required",
        "a terminal is required to read the password",
        "no tty present",
    )
    denial_markers = (
        "not in the sudoers file",
        "may not run sudo",
        "is not allowed to run sudo",
        "permission denied",
    )
    return any(marker in stderr for marker in auth_markers) and not any(
        marker in stderr for marker in denial_markers
    )


def _log_failure(action: str, proc: subprocess.CompletedProcess) -> None:
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    details = "\n".join(part for part in (stdout, stderr) if part)
    logger.warning(f"{action}失败，退出码：{proc.returncode}" + (f"\n{details}" if details else ""))


def _finish(action: str, proc: subprocess.CompletedProcess, abort: bool) -> subprocess.CompletedProcess:
    if proc.returncode != 0:
        _log_failure(action, proc)
        if abort:
            sys.exit(proc.returncode)
    return proc


def run_with_sudo_fallback(
    cmd: List[str],
    *,
    action: str,
    abort: bool = True,
) -> subprocess.CompletedProcess:
    proc = _run(cmd, capture=True)
    if proc.returncode == 0:
        return proc

    if shutil.which("sudo") is None:
        logger.error(f"{action}需要 sudo 权限，但未找到 sudo。")
        return _finish(action, proc, abort)

    sudo_proc = _run(["sudo", "-n", *cmd], capture=True)
    if sudo_proc.returncode == 0:
        return sudo_proc

    if not _sudo_auth_required(sudo_proc):
        return _finish(action, sudo_proc, abort)

    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        logger.error(f"{action}需要 sudo 权限，但当前环境无法交互式输入密码。请先手动挂载，或配置 sudo 权限。")
        return _finish(action, sudo_proc, abort)

    logger.info(f"{action}需要 sudo 权限，系统可能会提示输入密码...")
    return _finish(action, _run(["sudo", *cmd], capture=False), abort)
