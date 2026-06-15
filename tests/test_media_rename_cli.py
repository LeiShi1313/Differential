import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.rename_cli import build_parser, build_plan_from_args, main, should_prompt, validate_args


class MediaRenameCliTest(unittest.TestCase):
    def test_parser_requires_url_or_manual_title_year(self):
        parser = build_parser()
        args = parser.parse_args(["/tmp/media"])

        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                validate_args(args, parser)

    def test_parser_rejects_url_mixed_with_manual_identity(self):
        parser = build_parser()
        args = parser.parse_args(["/tmp/media", "--url", "https://example.test", "--title", "Title", "--year", "2024"])

        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                validate_args(args, parser)

    def test_json_disables_prompts(self):
        args = SimpleNamespace(yes=False, json=True)
        with mock.patch("sys.stdin.isatty", return_value=True), mock.patch("sys.stdout.isatty", return_value=True):
            self.assertFalse(should_prompt(args))

    def test_yes_does_not_infer_source_or_uploader(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Movie.2024.1080p.NF.WEB-DL-GROUP"
            folder.mkdir()
            main_file = folder / "Old.Movie.2024.1080p.NF.WEB-DL-GROUP.mkv"
            main_file.write_bytes(b"video")
            parser = build_parser()
            args = parser.parse_args([str(folder), "--title", "Movie Title", "--year", "2024", "--yes"])
            fake_scan = SimpleNamespace(
                root=folder,
                main_file=main_file,
                media_files=[main_file],
                is_bdmv=False,
                is_direct_file=False,
                resolution="1080p",
                video_codec="",
                audio_codec="",
                hdr="",
                release_type="",
                handler=SimpleNamespace(cleanup=mock.Mock()),
            )

            with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                plan, _scan = build_plan_from_args(args)

            target_names = " ".join(operation.target.name for operation in plan.operations)
            self.assertNotIn(".NF.", target_names)
            self.assertNotIn("-GROUP", target_names)
            self.assertIn(".WEB-DL", target_names)

    def test_dry_run_json_does_not_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Movie"
            folder.mkdir()
            main_file = folder / "Old.Movie.mkv"
            main_file.write_bytes(b"video")
            fake_scan = SimpleNamespace(
                root=folder,
                main_file=main_file,
                media_files=[main_file],
                is_bdmv=False,
                is_direct_file=False,
                resolution="1080p",
                video_codec="",
                audio_codec="",
                hdr="",
                release_type="",
                handler=SimpleNamespace(cleanup=mock.Mock()),
            )

            with redirect_stdout(StringIO()):
                with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan), mock.patch(
                    "differential.rename_cli.apply_plan"
                ) as apply:
                    code = main([str(folder), "--title", "Movie Title", "--year", "2024", "--dry-run", "--json"])

            self.assertEqual(code, 0)
            apply.assert_not_called()

    def test_dry_run_json_includes_parse_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Example.Show.S01E01.2024.2160p.NF.WEB-DL.DDP5.1.Atmos.HEVC-GRP"
            folder.mkdir()
            main_file = folder / "Example.Show.S01E01.2024.2160p.NF.WEB-DL.DDP5.1.Atmos.HEVC-GRP.mkv"
            main_file.write_bytes(b"video")
            fake_scan = SimpleNamespace(
                root=folder,
                main_file=main_file,
                media_files=[main_file],
                is_bdmv=False,
                is_direct_file=False,
                resolution="2160p",
                video_codec="",
                audio_codec="",
                hdr="",
                release_type="",
                handler=SimpleNamespace(cleanup=mock.Mock()),
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                    code = main(
                        [
                            str(folder),
                            "--title",
                            "Example Show",
                            "--year",
                            "2024",
                            "--dry-run",
                            "--json",
                        ]
                    )

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            parse_payload = payload["parse"]
            self.assertEqual(parse_payload["original_name"], folder.name)
            self.assertEqual(parse_payload["identity"]["title"], "Example Show")
            self.assertEqual(parse_payload["identity"]["season"], 1)
            self.assertEqual(parse_payload["identity"]["episode"], 1)
            self.assertEqual(parse_payload["release_tokens"]["source"], "NF")
            self.assertEqual(parse_payload["release_tokens"]["release_type"], "WEB-DL")
            self.assertEqual(parse_payload["release_tokens"]["resolution"], "2160p")
            self.assertEqual(parse_payload["release_tokens"]["audio_codec"], "DDP5.1.Atmos")
            self.assertEqual(parse_payload["release_tokens"]["release_group"], "GRP")
            self.assertEqual(parse_payload["selected_tokens"]["source"]["source"], "none")
            self.assertEqual(parse_payload["selected_tokens"]["release_type"]["source"], "inferred")

    def test_manual_metadata_fills_season_from_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Existing.Release.S03.2024.1080p.WEB-DL"
            folder.mkdir()
            main_file = folder / "Existing.Release.S03E01.2024.1080p.WEB-DL.mkv"
            main_file.write_bytes(b"video")
            parser = build_parser()
            args = parser.parse_args([str(folder), "--title", "Old Show", "--year", "2024", "--dry-run", "--json"])
            fake_scan = SimpleNamespace(
                root=folder,
                main_file=main_file,
                media_files=[main_file],
                is_bdmv=False,
                is_direct_file=False,
                resolution="1080p",
                video_codec="",
                audio_codec="",
                hdr="",
                release_type="",
                handler=SimpleNamespace(cleanup=mock.Mock()),
            )

            with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                plan, _scan = build_plan_from_args(args)

            targets = {operation.target.name for operation in plan.operations}
            self.assertIn("Old.Show.S03.2024.1080p.WEB-DL", targets)
            self.assertIn("Old.Show.S03E01.2024.1080p.WEB-DL.mkv", targets)

    def test_main_loads_current_folder_config_and_codec_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "Old.Movie"
            folder.mkdir()
            main_file = folder / "Old.Movie.mkv"
            main_file.write_bytes(b"video")
            (root / "config.ini").write_text(
                "\n".join(
                    [
                        "[Rename]",
                        "source = NF",
                        "type = WEB-DL",
                        "uploader = CFG",
                        "",
                        "[RenameCodecMap]",
                        "video.H.264 = H264",
                        "audio.AAC2.0 = AAC",
                    ]
                ),
                encoding="utf-8",
            )
            fake_scan = _fake_scan(folder, main_file, video_codec="h264", audio_codec="AAC2.0")

            stdout = StringIO()
            with _pushd(root), redirect_stdout(stdout):
                with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                    code = main([str(folder), "--title", "Movie Title", "--year", "2024", "--dry-run", "--json"])

            self.assertEqual(code, 0)
            self.assertIn("Movie.Title.2024.1080p.NF.WEB-DL.H264.AAC-CFG", stdout.getvalue())

    def test_rename_words_replace_before_parse_and_report_applied_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "Movie.2024.WEB DL.1080p-GRP"
            folder.mkdir()
            main_file = folder / "Movie.2024.WEB DL.1080p-GRP.mkv"
            main_file.write_bytes(b"video")
            (root / "config.ini").write_text(
                "\n".join(
                    [
                        "[RenameWords]",
                        "replace =",
                        "    WEB DL => WEB-DL",
                    ]
                ),
                encoding="utf-8",
            )
            fake_scan = _fake_scan(folder, main_file)

            stdout = StringIO()
            with _pushd(root), redirect_stdout(stdout):
                with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                    code = main([str(folder), "--title", "Movie Title", "--year", "2024", "--dry-run", "--json"])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["parse"]["release_tokens"]["release_type"], "WEB-DL")
            self.assertEqual(payload["parse"]["applied_words"], ["replace:WEB DL"])

    def test_rename_words_block_stops_planning_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "Movie.Sample.2024"
            folder.mkdir()
            main_file = folder / "Movie.Sample.2024.mkv"
            main_file.write_bytes(b"video")
            (root / "config.ini").write_text(
                "\n".join(
                    [
                        "[RenameWords]",
                        "block =",
                        "    sample",
                    ]
                ),
                encoding="utf-8",
            )
            fake_scan = _fake_scan(folder, main_file)

            stderr = StringIO()
            with _pushd(root), redirect_stderr(stderr):
                with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                    code = main([str(folder), "--title", "Movie Title", "--year", "2024", "--dry-run"])

            self.assertEqual(code, 1)
            self.assertIn("blocked by [RenameWords] rule: sample", stderr.getvalue())

    def test_configured_release_group_is_reported_in_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "Movie.2024.1080p.WEB-DL.H264.mygrp"
            folder.mkdir()
            main_file = folder / "Movie.2024.1080p.WEB-DL.H264.mygrp.mkv"
            main_file.write_bytes(b"video")
            (root / "config.ini").write_text(
                "\n".join(
                    [
                        "[RenameReleaseGroups]",
                        "groups =",
                        "    MyGrp",
                    ]
                ),
                encoding="utf-8",
            )
            fake_scan = _fake_scan(folder, main_file)

            stdout = StringIO()
            with _pushd(root), redirect_stdout(stdout):
                with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                    code = main([str(folder), "--title", "Movie Title", "--year", "2024", "--dry-run", "--json"])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            release_tokens = payload["parse"]["release_tokens"]
            self.assertEqual(release_tokens["release_group"], "MyGrp")
            self.assertEqual(release_tokens["release_group_source"], "custom")
            self.assertEqual(release_tokens["release_group_confidence"], "high")
            self.assertEqual(payload["parse"]["selected_tokens"]["uploader"]["source"], "none")

    def test_cli_values_override_current_folder_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "Old.Movie"
            folder.mkdir()
            main_file = folder / "Old.Movie.mkv"
            main_file.write_bytes(b"video")
            (root / "config.ini").write_text(
                "\n".join(
                    [
                        "[Rename]",
                        "source = NF",
                        "type = WEB-DL",
                        "folder_only = true",
                    ]
                ),
                encoding="utf-8",
            )
            fake_scan = _fake_scan(folder, main_file)

            stdout = StringIO()
            with _pushd(root), redirect_stdout(stdout):
                with mock.patch("differential.rename_cli.scan_media", return_value=fake_scan):
                    code = main(
                        [
                            str(folder),
                            "--title",
                            "Movie Title",
                            "--year",
                            "2024",
                            "--source",
                            "AMZN",
                            "--no-folder-only",
                            "--dry-run",
                            "--json",
                        ]
                    )

            output = stdout.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Movie.Title.2024.1080p.AMZN.WEB-DL.mkv", output)
            self.assertNotIn(".NF.WEB-DL", output)


@contextmanager
def _pushd(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _fake_scan(folder: Path, main_file: Path, video_codec: str = "", audio_codec: str = ""):
    return SimpleNamespace(
        root=folder,
        main_file=main_file,
        media_files=[main_file],
        is_bdmv=False,
        is_direct_file=False,
        resolution="1080p",
        video_codec=video_codec,
        audio_codec=audio_codec,
        hdr="",
        release_type="",
        handler=SimpleNamespace(cleanup=mock.Mock()),
    )


if __name__ == "__main__":
    unittest.main()
