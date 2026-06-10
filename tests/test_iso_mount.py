import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.base_plugin import Base
from differential.utils.mediainfo_handler import MediaInfoHandler
from differential.utils.ptgen.reference import PTGenReference
from differential.utils.privilege import run_command, run_with_sudo_fallback
from differential.version import version


def completed(cmd, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)


class PrivilegeHelperTest(unittest.TestCase):
    def test_run_command_returns_direct_success(self):
        with mock.patch("subprocess.run", return_value=completed(["hdiutil"])) as run:
            proc = run_command(["hdiutil"], action="hdiutil test")

        self.assertEqual(proc.returncode, 0)
        run.assert_called_once_with(["hdiutil"], text=True, capture_output=True)

    def test_run_command_returns_failure_without_abort(self):
        with mock.patch(
            "subprocess.run",
            return_value=completed(["hdiutil"], returncode=1, stderr="detach failed"),
        ):
            proc = run_command(["hdiutil"], action="hdiutil test", abort=False)

        self.assertEqual(proc.returncode, 1)

    def test_run_with_sudo_fallback_uses_direct_success(self):
        with mock.patch("subprocess.run", return_value=completed(["mount"])) as run:
            proc = run_with_sudo_fallback(["mount"], action="mount test")

        self.assertEqual(proc.returncode, 0)
        run.assert_called_once_with(["mount"], text=True, capture_output=True)

    def test_run_with_sudo_fallback_uses_noninteractive_sudo(self):
        with mock.patch("shutil.which", return_value="/usr/bin/sudo"), mock.patch(
            "subprocess.run",
            side_effect=[
                completed(["mount"], returncode=1, stderr="permission denied"),
                completed(["sudo", "-n", "mount"]),
            ],
        ) as run:
            proc = run_with_sudo_fallback(["mount"], action="mount test")

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(run.call_args_list[1].args[0], ["sudo", "-n", "mount"])

    def test_run_with_sudo_fallback_does_not_prompt_for_command_failure(self):
        with mock.patch("shutil.which", return_value="/usr/bin/sudo"), mock.patch(
            "subprocess.run",
            side_effect=[
                completed(["mount"], returncode=1, stderr="permission denied"),
                completed(["sudo", "-n", "mount"], returncode=32, stderr="wrong fs type"),
            ],
        ) as run:
            proc = run_with_sudo_fallback(["mount"], action="mount test", abort=False)

        self.assertEqual(proc.returncode, 32)
        self.assertEqual(len(run.call_args_list), 2)

    def test_run_with_sudo_fallback_returns_failure_without_tty(self):
        with mock.patch("shutil.which", return_value="/usr/bin/sudo"), mock.patch(
            "subprocess.run",
            side_effect=[
                completed(["mount"], returncode=1, stderr="permission denied"),
                completed(["sudo", "-n", "mount"], returncode=1, stderr="sudo: a password is required"),
            ],
        ), mock.patch("sys.stdin.isatty", return_value=False), mock.patch(
            "sys.stdout.isatty", return_value=False
        ), mock.patch("sys.stderr.isatty", return_value=False):
            proc = run_with_sudo_fallback(["mount"], action="mount test", abort=False)

        self.assertEqual(proc.returncode, 1)


class MediaInfoIsoMountTest(unittest.TestCase):
    def test_find_mediainfo_mounts_linux_iso_before_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            iso = root / "Movie [Test].iso"
            iso.write_bytes(b"iso")
            mounted = root / "mounted"
            (mounted / "BDMV" / "STREAM").mkdir(parents=True)
            (mounted / "BDMV" / "index.bdmv").write_bytes(b"bdmv")
            main_stream = mounted / "BDMV" / "STREAM" / "00001.m2ts"
            main_stream.write_bytes(b"stream-data")

            handler = MediaInfoHandler(
                folder=iso,
                create_folder=True,
                use_short_bdinfo=False,
                scan_bdinfo=False,
            )

            def fake_mount():
                handler.iso_mount_parent = root
                handler.iso_mount_dir = mounted
                handler.folder = mounted

            with mock.patch.object(handler, "_mount_iso", side_effect=fake_mount) as mount_iso, mock.patch(
                "differential.utils.mediainfo_handler.platform.system", return_value="Linux"
            ), mock.patch(
                "differential.utils.mediainfo_handler.MediaInfo.parse",
                return_value=SimpleNamespace(to_data=lambda: {}),
            ):
                main_file = handler.find_mediainfo()

            mount_iso.assert_called_once()
            self.assertEqual(main_file, main_stream)
            self.assertTrue(iso.exists())
            self.assertTrue(handler.is_bdmv)
            self.assertEqual(handler.bdinfo, "[BDINFO HERE]")

    def test_cleanup_unmounts_and_removes_temp_mount_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "iso-parent"
            mount_dir = parent / "movie"
            mount_dir.mkdir(parents=True)
            handler = MediaInfoHandler(mount_dir / "movie.iso", False, False, True)
            handler.iso_mount_parent = parent
            handler.iso_mount_dir = mount_dir

            with mock.patch.object(handler, "_is_mountpoint", side_effect=[True, False]), mock.patch(
                "differential.utils.mediainfo_handler.run_with_sudo_fallback",
                return_value=completed(["umount"]),
            ) as sudo:
                handler.cleanup()

            sudo.assert_called_once_with(
                ["umount", "--", str(mount_dir)],
                action=f"卸载ISO: {mount_dir}",
                abort=False,
            )
            self.assertFalse(parent.exists())

    def test_mount_iso_uses_read_only_loop_mount_with_option_terminator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            iso = root / "-leading-dash.iso"
            iso.write_bytes(b"iso")
            mount_parent = root / "mount-parent"
            mount_parent.mkdir()
            handler = MediaInfoHandler(iso, False, False, True)

            with mock.patch(
                "differential.utils.mediainfo_handler.platform.system",
                return_value="Linux",
            ), mock.patch(
                "differential.utils.mediainfo_handler.tempfile.mkdtemp",
                return_value=str(mount_parent),
            ), mock.patch(
                "differential.utils.mediainfo_handler.run_with_sudo_fallback",
                return_value=completed(["mount"]),
            ) as sudo:
                handler._mount_iso()

            expected_mount_dir = mount_parent / handler.cache_key
            sudo.assert_called_once_with(
                ["mount", "-o", "ro,loop", "--", str(iso.resolve()), str(expected_mount_dir)],
                action=f"挂载ISO: {iso}",
                abort=True,
            )
            self.assertEqual(handler.folder, expected_mount_dir)

    def test_mount_iso_uses_hdiutil_attach_on_macos(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            iso = root / "-leading-dash.iso"
            iso.write_bytes(b"iso")
            mount_parent = root / "mount-parent"
            mount_parent.mkdir()
            handler = MediaInfoHandler(iso, False, False, True)

            with mock.patch(
                "differential.utils.mediainfo_handler.platform.system",
                return_value="Darwin",
            ), mock.patch(
                "differential.utils.mediainfo_handler.tempfile.mkdtemp",
                return_value=str(mount_parent),
            ), mock.patch(
                "differential.utils.mediainfo_handler.run_command",
                return_value=completed(["hdiutil"]),
            ) as run:
                handler._mount_iso()

            expected_mount_dir = mount_parent / handler.cache_key
            run.assert_called_once_with(
                [
                    "hdiutil",
                    "attach",
                    "-readonly",
                    "-nobrowse",
                    "-mountpoint",
                    str(expected_mount_dir),
                    str(iso.resolve()),
                ],
                action=f"挂载ISO: {iso}",
                abort=True,
            )
            self.assertEqual(handler.folder, expected_mount_dir)
            self.assertEqual(handler.iso_mount_platform, "Darwin")

    def test_cleanup_detaches_macos_iso_and_removes_temp_mount_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "iso-parent"
            mount_dir = parent / "movie"
            mount_dir.mkdir(parents=True)
            handler = MediaInfoHandler(mount_dir / "movie.iso", False, False, True)
            handler.iso_mount_parent = parent
            handler.iso_mount_dir = mount_dir
            handler.iso_mount_platform = "Darwin"

            with mock.patch(
                "differential.utils.mediainfo_handler.run_command",
                return_value=completed(["hdiutil"]),
            ) as run, mock.patch.object(handler, "_is_mountpoint", return_value=False):
                handler.cleanup()

            run.assert_called_once_with(
                ["hdiutil", "detach", str(mount_dir)],
                action=f"卸载ISO: {mount_dir}",
                abort=False,
            )
            self.assertFalse(parent.exists())
            self.assertIsNone(handler.iso_mount_platform)

    def test_mount_iso_exits_on_unsupported_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            iso = Path(tmp) / "Movie.iso"
            iso.write_bytes(b"iso")
            handler = MediaInfoHandler(iso, False, False, True)

            with mock.patch(
                "differential.utils.mediainfo_handler.platform.system",
                return_value="Windows",
            ), self.assertRaises(SystemExit):
                handler._mount_iso()

            self.assertIsNone(handler.iso_mount_dir)

    def test_bdinfo_cache_uses_sanitized_original_media_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = MediaInfoHandler(Path("Movie [Test]*.iso"), False, False, True)
            cache_dir = Path(tmp) / f"Differential.bdinfo.{version}.abc.{handler.cache_key}"
            cache_dir.mkdir()
            (cache_dir / "BDINFO.txt").write_text("DISC INFO:\n\nName: Test\n\nCHAPTERS:\n", encoding="utf-8")

            with mock.patch("differential.utils.mediainfo_handler.tempfile.gettempdir", return_value=tmp):
                cached = handler._find_cached_bdinfo()

        self.assertNotIn("[", handler.cache_key)
        self.assertNotIn("*", handler.cache_key)
        self.assertIn("DISC INFO", cached)

    def test_short_bdinfo_extracts_quick_summary_at_eof(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "BDINFO.txt"
            report.write_text(
                "DISC INFO:\n\nName: Test\n\nQUICK SUMMARY:\n\nDisc Title: Test\nPlaylist: 00001.MPLS\n",
                encoding="utf-8",
            )
            handler = MediaInfoHandler(Path("Movie.iso"), False, True, True)

            bdinfo = handler._extract_bdinfo_content([report])

        self.assertIn("QUICK SUMMARY", bdinfo)
        self.assertIn("Playlist: 00001.MPLS", bdinfo)


class BasePluginIsoWorkflowTest(unittest.TestCase):
    def test_upload_cleans_up_after_prepare_exception(self):
        plugin = SimpleNamespace(
            _prepare=mock.Mock(side_effect=RuntimeError("forced")),
            mediainfo_handler=SimpleNamespace(cleanup=mock.Mock()),
        )

        with self.assertRaises(RuntimeError):
            Base.upload(plugin)

        plugin.mediainfo_handler.cleanup.assert_called_once()

    def test_upload_cleans_up_after_system_exit(self):
        plugin = SimpleNamespace(
            _prepare=mock.Mock(side_effect=SystemExit(1)),
            mediainfo_handler=SimpleNamespace(cleanup=mock.Mock()),
        )

        with self.assertRaises(SystemExit):
            Base.upload(plugin)

        plugin.mediainfo_handler.cleanup.assert_called_once()

    def test_prepare_keeps_original_iso_for_nfo_and_torrent(self):
        with tempfile.TemporaryDirectory() as tmp:
            iso = Path(tmp) / "Movie.iso"
            iso.write_bytes(b"iso")
            mounted_stream = Path(tmp) / "mounted" / "BDMV" / "STREAM" / "00001.m2ts"
            mounted_stream.parent.mkdir(parents=True)
            mounted_stream.write_bytes(b"stream")

            plugin = SimpleNamespace(
                folder=iso,
                announce_url="https://tracker.example/announce",
                reuse_torrent=True,
                from_torrent=None,
                generate_nfo=True,
                make_torrent=True,
                mediainfo_handler=SimpleNamespace(
                    find_mediainfo=mock.Mock(return_value=mounted_stream),
                    resolution="1080p",
                    duration=1000,
                    media_info="media info",
                    cleanup=mock.Mock(),
                ),
                ptgen_handler=SimpleNamespace(fetch_ptgen_info=mock.Mock(return_value=(None, None, None))),
                screenshot_handler=SimpleNamespace(collect_screenshots=mock.Mock()),
            )

            with mock.patch("differential.base_plugin.generate_nfo") as generate_nfo, mock.patch(
                "differential.base_plugin.make_torrent"
            ) as make_torrent:
                Base._prepare(plugin)

        plugin.screenshot_handler.collect_screenshots.assert_called_once_with(
            mounted_stream,
            "1080p",
            1000,
        )
        generate_nfo.assert_called_once_with(iso, "media info")
        self.assertEqual(make_torrent.call_args.args[0], iso)

    def test_prepare_searches_media_when_url_is_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "[两心不疑].No.Doubt.in.Us.2026.S01.Complete"
            folder.mkdir()
            main_file = folder / "episode.mkv"
            main_file.write_bytes(b"video")
            selected = SimpleNamespace(display_title="两心不疑")
            reference = PTGenReference(
                site="douban",
                sid="37227662",
                original_url="https://movie.douban.com/subject/37227662/",
            )
            client = SimpleNamespace(search_parsed=mock.Mock(return_value=[selected]))
            ptgen_handler = SimpleNamespace(fetch_ptgen_reference=mock.Mock(return_value=("ptgen", "douban", "imdb")))
            plugin = SimpleNamespace(
                folder=folder,
                url="",
                non_interactive=True,
                ptgen_source="douban",
                ptgen_fields="title_aliases",
                search_hint="国漫",
                generate_nfo=False,
                make_torrent=False,
                mediainfo_handler=SimpleNamespace(
                    find_mediainfo=mock.Mock(return_value=main_file),
                    resolution="1080p",
                    duration=1000,
                ),
                ptgen_handler=ptgen_handler,
                screenshot_handler=SimpleNamespace(collect_screenshots=mock.Mock()),
            )
            plugin._search_and_fetch_ptgen_info = Base._search_and_fetch_ptgen_info.__get__(plugin, type(plugin))

            with mock.patch("differential.base_plugin.MediaSearchClient", return_value=client), mock.patch(
                "differential.base_plugin.select_media_result",
                return_value=selected,
            ) as select_result, mock.patch(
                "differential.base_plugin.result_to_ptgen_reference",
                return_value=reference,
            ):
                Base._prepare(plugin)

        client.search_parsed.assert_called_once()
        self.assertEqual(client.search_parsed.call_args.kwargs["ptgen_source"], "douban")
        self.assertEqual(client.search_parsed.call_args.kwargs["ptgen_fields"], "title_aliases")
        self.assertEqual(client.search_parsed.call_args.kwargs["search_hint"], "国漫")
        select_result.assert_called_once()
        self.assertTrue(select_result.call_args.kwargs["non_interactive"])
        ptgen_handler.fetch_ptgen_reference.assert_called_once_with(reference)
        self.assertEqual(plugin.url, reference.original_url)
        self.assertEqual((plugin.ptgen, plugin.douban, plugin.imdb), ("ptgen", "douban", "imdb"))


if __name__ == "__main__":
    unittest.main()
