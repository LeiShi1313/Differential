import os
import re
import sys
import platform
import tempfile
import shutil
from dataclasses import dataclass
from pathlib import Path
from loguru import logger
from typing import Optional, List
from pymediainfo import MediaInfo

from differential import tools
from differential.version import version
from differential.utils.binary import execute_with_output
from differential.utils.mediainfo import get_full_mediainfo, get_duration, get_resolution


BDINFO_ENV_VAR = "BDINFOPATH"
BDINFO_BINARY_NAMES = ("BDInfo", "bdinfo")


def _escape_shell_path(path) -> str:
    return str(path).replace('"', '\\"')


def _bundled_bdinfo_path() -> Path:
    return Path(tools.__file__).resolve().parent / "BDinfoCli.0.7.3" / "BDInfo.exe"


def find_native_bdinfo() -> Optional[Path]:
    env_path = os.environ.get(BDINFO_ENV_VAR)
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate
        logger.error(f"{candidate}不是可执行文件！")
        sys.exit(1)

    for name in BDINFO_BINARY_NAMES:
        cwd_candidate = Path.cwd().joinpath(name)
        if cwd_candidate.is_file():
            return cwd_candidate

        which_candidate = shutil.which(name)
        if which_candidate:
            return Path(which_candidate)

    return None


@dataclass(frozen=True)
class BDInfoRunner:
    name: str
    executable: str
    use_mono: bool = False

    def run(self, bd_path: Path, report_dir: str) -> None:
        bd_path_arg = _escape_shell_path(bd_path)
        report_dir_arg = _escape_shell_path(report_dir)

        if self.use_mono:
            executable_arg = _escape_shell_path(self.executable)
            args = f'"{executable_arg}" -w "{bd_path_arg}" "{report_dir_arg}"'
            execute_with_output("mono", args, abort=True)
            return

        args = f'-w "{bd_path_arg}" "{report_dir_arg}"'
        execute_with_output(self.executable, args, abort=True)


class MediaInfoHandler:
    """
    Manages finding MediaInfo, determining if the target is a BDMV,
    scanning BDInfo if necessary, etc.
    """
    mediainfo: MediaInfo

    def __init__(
        self,
        folder: Path,
        create_folder: bool,
        use_short_bdinfo: bool,
        scan_bdinfo: bool,
    ):
        self.folder = folder
        self.create_folder = create_folder
        self.use_short_bdinfo = use_short_bdinfo
        self.scan_bdinfo = scan_bdinfo

        self.is_bdmv = False
        self.bdinfo = None
        self.main_file = None

    def find_mediainfo(self):
        """
        Main entry method to:
          1) Possibly create folder if needed
          2) Determine main file
          3) Check for BDMV presence
          4) Parse mediainfo
          5) Possibly run BDInfo scanning
        Returns (MediaInfo, BDInfo, main_file, is_bdmv).
        """
        logger.info(f"正在获取Mediainfo: {self.folder}")
        self._handle_single_or_folder()
        if not self.main_file:
            logger.error("未找到可分析的文件，请确认路径。")
            sys.exit(1)

        if self.main_file.suffix.lower() == ".iso":
            logger.error("请先挂载ISO文件再使用。")
            sys.exit(1)

        self.mediainfo = MediaInfo.parse(self.main_file)
        logger.info(f"[MediaInfo] 已获取: {self.main_file}")
        logger.trace(self.mediainfo.to_data())

        # If BDMV found, handle BDInfo
        if self.is_bdmv:
            if self.scan_bdinfo:
                self.bdinfo = self._get_bdinfo()
            else:
                self.bdinfo = "[BDINFO HERE]"

        return self.main_file

    @property
    def media_info(self):
        if self.is_bdmv:
            return self.bdinfo
        else:
            return get_full_mediainfo(self.mediainfo)

    @property
    def resolution(self):
        return get_resolution(self.main_file, self.mediainfo)

    @property
    def duration(self):
        return get_duration(self.main_file, self.mediainfo)

    @property
    def tracks(self):
        return self.mediainfo.tracks

    def _handle_single_or_folder(self):
        """
        If `folder` is actually a single file, handle create_folder logic.
        Otherwise, find the biggest file in the folder.
        Also detect if there's a BDMV structure present.
        """
        if self.folder.is_file():
            if self.create_folder:
                logger.info("目标是文件，正在创建文件夹...")
                new_dir = self.folder.parent.joinpath(self.folder.stem)
                if not new_dir.is_dir():
                    new_dir.mkdir(parents=True)
                shutil.move(str(self.folder), new_dir)
                self.folder = new_dir
                self.main_file = new_dir.joinpath(self.folder.name)
            else:
                self.main_file = self.folder
        else:
            logger.info("目标为文件夹，正在获取最大的文件...")
            biggest_size = -1
            biggest_file = None
            has_bdmv = False

            for f in self.folder.glob("**/*"):
                if f.is_file():
                    if f.suffix.lower() == ".bdmv":
                        has_bdmv = True
                    s = f.stat().st_size
                    if s > biggest_size:
                        biggest_size = s
                        biggest_file = f

            self.main_file = biggest_file
            self.is_bdmv = has_bdmv

    def _get_bdinfo(self) -> str:
        """
        Run or reuse BDInfo scanning for a BDMV structure.
        Return either the short summary or the full disc info.
        """
        logger.info("[BDMV] 发现 BDMV 结构，准备扫描BDInfo...")

        # Check existing BDInfo in temp
        if cached := self._find_cached_bdinfo():
            logger.info("[BDMV] 已发现之前的 BDInfo，跳过重复扫描")
            return cached

        # Otherwise, run BDInfo scanning
        temp_dir = tempfile.mkdtemp(prefix=f"Differential.bdinfo.{version}.", suffix=f".{self.folder.name}")
        self._run_bdinfo_scan(temp_dir)
        return self._collect_bdinfo_from_temp(temp_dir)

    def _find_cached_bdinfo(self) -> Optional[str]:
        """
        Look in the temp dir for an existing BDInfo scan matching self.folder.name.
        """
        for d in Path(tempfile.gettempdir()).glob(f"Differential.bdinfo.{version}.*.{self.folder.name}"):
            if d.is_dir():
                if txt_files := list(d.glob("*.txt")):
                    return self._extract_bdinfo_content(txt_files)
        return None

    def _run_bdinfo_scan(self, temp_dir: str) -> None:
        runner = self._select_bdinfo_runner()
        for bdmv_path in self.folder.glob("**/BDMV"):
            logger.info(f"[BDInfo] 扫描: {bdmv_path.parent}")
            runner.run(bdmv_path.parent, temp_dir)

    def _select_bdinfo_runner(self) -> BDInfoRunner:
        bundled_bdinfo = _bundled_bdinfo_path()
        if platform.system() == "Windows":
            logger.info(f"[BDInfo] 使用内置BDInfo: {bundled_bdinfo}")
            return BDInfoRunner("bundled", str(bundled_bdinfo))

        native_bdinfo = find_native_bdinfo()
        if native_bdinfo:
            logger.info(f"[BDInfo] 使用原生BDInfo: {native_bdinfo}")
            return BDInfoRunner("native", str(native_bdinfo))

        logger.info("[BDInfo] 未找到原生BDInfo，回退到Mono运行内置BDInfo")
        return BDInfoRunner("mono", str(bundled_bdinfo), use_mono=True)

    def _collect_bdinfo_from_temp(self, temp_dir: str) -> str:
        txt_files = sorted(Path(temp_dir).glob("*.txt"))
        if not txt_files:
            logger.warning(f"[BDInfo] 未找到BDInfo信息：{temp_dir}")
            return "[BDINFO HERE]"
        return self._extract_bdinfo_content(txt_files)

    def _extract_bdinfo_content(self, txt_files: List[Path]) -> str:
        bdinfos = []
        for txt in txt_files:
            content = txt.read_text(errors="ignore")
            if self.use_short_bdinfo:
                # Extract QUICK SUMMARY
                if m := re.search(r"(QUICK SUMMARY:\n+(.+?\n)+)\n\n", content):
                    bdinfos.append(m.group(1))
            else:
                # Extract DISC INFO
                pattern = (
                    r"(DISC INFO:\n+(.+?\n{1,2})+?)(?:CHAPTERS:\n|STREAM DIAGNOSTICS:\n|\[\/code\]\n<---- END FORUMS PASTE ---->)"
                )
                if m := re.search(pattern, content):
                    bdinfos.append(m.group(1))
        return "\n\n".join(bdinfos)
