import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils import mediainfo_handler
from differential.utils.mediainfo_handler import (
    BDINFO_ENV_VAR,
    BDInfoRunner,
    MediaInfoHandler,
    find_native_bdinfo,
)


class BDInfoRunnerTest(unittest.TestCase):
    def test_native_runner_invokes_bdinfo_directly(self):
        runner = BDInfoRunner("native", "/usr/local/bin/BDInfo")

        with patch.object(mediainfo_handler, "execute_with_output") as execute:
            runner.run(Path("/media/Some Disc"), "/tmp/report dir")

        execute.assert_called_once_with(
            "/usr/local/bin/BDInfo",
            '-w "/media/Some Disc" "/tmp/report dir"',
            abort=True,
        )

    def test_mono_runner_wraps_bundled_bdinfo(self):
        runner = BDInfoRunner("mono", "/opt/tools/BDInfo.exe", use_mono=True)

        with patch.object(mediainfo_handler, "execute_with_output") as execute:
            runner.run(Path("/media/Some Disc"), "/tmp/report dir")

        execute.assert_called_once_with(
            "mono",
            '"/opt/tools/BDInfo.exe" -w "/media/Some Disc" "/tmp/report dir"',
            abort=True,
        )

    def test_find_native_bdinfo_uses_bdinfopath(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bdinfo = Path(temp_dir).joinpath("BDInfo")
            bdinfo.touch()

            with patch.dict(os.environ, {BDINFO_ENV_VAR: str(bdinfo)}, clear=True):
                self.assertEqual(find_native_bdinfo(), bdinfo)

    def test_find_native_bdinfo_uses_path(self):
        def fake_which(name):
            if name == "BDInfo":
                return "/usr/bin/BDInfo"
            return None

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(mediainfo_handler.shutil, "which", side_effect=fake_which):
                self.assertEqual(find_native_bdinfo(), Path("/usr/bin/BDInfo"))

    def test_windows_uses_bundled_bdinfo(self):
        handler = MediaInfoHandler(Path("/media/Some Disc"), False, False, True)

        with patch.object(mediainfo_handler.platform, "system", return_value="Windows"):
            with patch.object(mediainfo_handler, "_bundled_bdinfo_path", return_value=Path("/tools/BDInfo.exe")):
                with patch.object(mediainfo_handler, "find_native_bdinfo") as find_native:
                    runner = handler._select_bdinfo_runner()

        self.assertEqual(runner.name, "bundled")
        self.assertEqual(runner.executable, "/tools/BDInfo.exe")
        self.assertFalse(runner.use_mono)
        find_native.assert_not_called()

    def test_linux_prefers_native_bdinfo(self):
        handler = MediaInfoHandler(Path("/media/Some Disc"), False, False, True)

        with patch.object(mediainfo_handler.platform, "system", return_value="Linux"):
            with patch.object(mediainfo_handler, "find_native_bdinfo", return_value=Path("/usr/bin/BDInfo")):
                runner = handler._select_bdinfo_runner()

        self.assertEqual(runner.name, "native")
        self.assertEqual(runner.executable, "/usr/bin/BDInfo")
        self.assertFalse(runner.use_mono)

    def test_linux_falls_back_to_mono_when_native_missing(self):
        handler = MediaInfoHandler(Path("/media/Some Disc"), False, False, True)

        with patch.object(mediainfo_handler.platform, "system", return_value="Linux"):
            with patch.object(mediainfo_handler, "find_native_bdinfo", return_value=None):
                with patch.object(mediainfo_handler, "_bundled_bdinfo_path", return_value=Path("/tools/BDInfo.exe")):
                    runner = handler._select_bdinfo_runner()

        self.assertEqual(runner.name, "mono")
        self.assertEqual(runner.executable, "/tools/BDInfo.exe")
        self.assertTrue(runner.use_mono)


if __name__ == "__main__":
    unittest.main()
