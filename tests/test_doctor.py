import argparse
import os
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

from differential.commands import PARSER
from differential.doctor import (
    Diagnostic,
    _check_bdinfo,
    _check_binary,
    _check_config,
    _check_image_host_config,
    run_doctor,
)
# Imported so PluginRegister registers CHDBitsEncode for _check_config.
from differential.plugins.chdbits_encode import CHDBitsEncode
from differential.plugins.nexusphp import NexusPHP


ROOT = Path(__file__).resolve().parents[1]


class DoctorTest(unittest.TestCase):
    def test_parser_accepts_doctor_command(self):
        args = PARSER.parse_args(["doctor", "-c", "config.ini", "--section", "Profile", "NexusPHP"])

        self.assertEqual(args.command, "doctor")
        self.assertEqual(args.config, "config.ini")
        self.assertEqual(args.doctor_section, "Profile")
        self.assertEqual(args.doctor_plugin, "NexusPHP")

    def test_config_check_fails_unknown_plugin_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                "[DEFAULT]\n"
                "folder = /media/Movie\n"
                "upload_url = https://example.test/upload.php\n"
                "unknown_key = value\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(config=str(config), doctor_plugin="NexusPHP", doctor_section="")

            diagnostic, merged = _check_config(args)

        self.assertEqual(diagnostic.status, "fail")
        self.assertIn("unsupported config key", diagnostic.message)
        self.assertIsNone(merged)

    def test_config_check_merges_plugin_config_for_image_host_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                "[DEFAULT]\n"
                "folder = /media/Movie\n"
                "upload_url = https://example.test/upload.php\n"
                "image_hosting = ptpimg\n"
                "ptpimg_api_key = secret\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(config=str(config), doctor_plugin="NexusPHP", doctor_section="")

            diagnostic, merged = _check_config(args)
            image_host_diagnostic = _check_image_host_config(merged)

        self.assertEqual(diagnostic.status, "ok")
        self.assertEqual(image_host_diagnostic.status, "ok")
        self.assertEqual(image_host_diagnostic.message, "ptpimg")

    def test_config_check_normalizes_plugin_alias_for_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                "[DEFAULT]\n"
                "folder = /media/Movie\n"
                "upload_url = https://default.example/upload.php\n"
                "\n"
                "[NexusPHP]\n"
                "upload_url = https://section.example/upload.php\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(config=str(config), doctor_plugin="nexus", doctor_section="")

            diagnostic, merged = _check_config(args)

        self.assertEqual(diagnostic.status, "ok")
        self.assertEqual(merged["upload_url"], "https://section.example/upload.php")

    def test_image_host_config_reports_missing_required_keys(self):
        diagnostic = _check_image_host_config({"image_hosting": "cloudinary", "cloudinary_api_key": "key"})

        self.assertEqual(diagnostic.status, "fail")
        self.assertIn("cloudinary_cloud_name", diagnostic.message)
        self.assertIn("cloudinary_api_secret", diagnostic.message)

    def test_image_host_config_requires_smms_api_key(self):
        diagnostic = _check_image_host_config({"image_hosting": "smms"})

        self.assertEqual(diagnostic.status, "fail")
        self.assertIn("smms_api_key", diagnostic.message)

    def test_bdinfo_check_matches_runtime_current_directory_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                bdinfo = Path(tmp) / "BDInfo"
                bdinfo.write_text("#!/bin/sh\n", encoding="utf-8")

                with mock.patch("differential.doctor.shutil.which", return_value=None), mock.patch(
                    "differential.doctor._bdinfo_env_path",
                    return_value=None,
                ):
                    diagnostic = _check_bdinfo()
            finally:
                os.chdir(old_cwd)

        self.assertEqual(diagnostic.status, "ok")
        self.assertEqual(diagnostic.message, str(bdinfo))

    def test_ffmpeg_check_honors_runtime_env_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            ffmpeg = Path(tmp) / "ffmpeg-custom"
            ffmpeg.write_text("#!/bin/sh\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"FFMPEGPATH": str(ffmpeg)}), mock.patch(
                "differential.doctor.shutil.which",
                return_value=None,
            ):
                diagnostic = _check_binary("ffmpeg", "ffmpeg")

        self.assertEqual(diagnostic.status, "ok")
        self.assertEqual(diagnostic.message, f"FFMPEGPATH={ffmpeg}")

    def test_example_league_official_section_validates_for_chdbits_encode(self):
        args = argparse.Namespace(
            config=str(ROOT / "config.ini.example"),
            doctor_plugin="CHDBitsEncode",
            doctor_section="LeagueOfficial",
        )

        diagnostic, merged = _check_config(args)

        self.assertEqual(diagnostic.status, "ok")
        self.assertEqual(merged["team"], "LeagueTV")
        self.assertEqual(merged["source_name"], "HDTV")

    def test_run_doctor_prints_diagnostics_and_returns_failure(self):
        diagnostics = [
            Diagnostic("ffmpeg", "ok", "/usr/bin/ffmpeg"),
            Diagnostic("config", "fail", "bad config"),
        ]
        with mock.patch("differential.doctor.collect_diagnostics", return_value=diagnostics), mock.patch(
            "sys.stdout",
            new_callable=StringIO,
        ) as stdout:
            code = run_doctor(argparse.Namespace())

        self.assertEqual(code, 1)
        self.assertIn("[OK] ffmpeg: /usr/bin/ffmpeg", stdout.getvalue())
        self.assertIn("[FAIL] config: bad config", stdout.getvalue())

    def test_module_execution_preserves_doctor_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_config = Path(tmp) / "missing.ini"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "differential.main",
                    "doctor",
                    "-c",
                    str(missing_config),
                ],
                text=True,
                capture_output=True,
            )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("[FAIL] config:", proc.stdout)


if __name__ == "__main__":
    unittest.main()
