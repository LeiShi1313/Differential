import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.screenshot_handler import ScreenshotHandler


class ScreenshotHandlerTest(unittest.TestCase):
    def test_default_screenshot_command_uses_size_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = ScreenshotHandler(
                folder=Path(tmp) / "DefaultScreenshotCase",
                screenshot_count=1,
                optimize_screenshot=False,
            )

            args = handler._build_ffmpeg_args(
                Path(tmp) / "movie.mkv",
                Path(tmp) / "out.png",
                "1920x1080",
                62000,
            )

        self.assertIn("-s 1920x1080", args)
        self.assertNotIn('-vf "', args)
        self.assertIn("-vframes 1", args)

    def test_auto_tonemap_screenshot_command_uses_filter_chain_for_hdr(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = ScreenshotHandler(
                folder=Path(tmp) / "TonemapScreenshotCase",
                screenshot_count=1,
                optimize_screenshot=False,
            )
            tracks = [
                SimpleNamespace(
                    track_type="Video",
                    hdr_format="SMPTE ST 2086, HDR10 compatible",
                    transfer_characteristics="PQ",
                )
            ]

            with mock.patch.object(
                ScreenshotHandler,
                "_available_ffmpeg_filters",
                return_value={"zscale", "scale", "tonemap"},
            ):
                args = handler._build_ffmpeg_args(
                    Path(tmp) / "movie.mkv",
                    Path(tmp) / "out.png",
                    "3840x2160",
                    62000,
                    tracks,
                )

        self.assertIn(
            '-vf "zscale=primariesin=bt2020:transferin=smpte2084:matrixin=bt2020nc:transfer=linear:npl=100,format=gbrpf32le,tonemap=tonemap=hable:desat=0:peak=1000,zscale=primaries=bt709:transfer=bt709:matrix=bt709:range=limited,scale=3840:2160,format=rgb24"',
            args,
        )
        self.assertNotIn("-s 3840x2160", args)
        self.assertIn("-vframes 1", args)

    def test_auto_tonemap_uses_scale_fallback_without_zscale(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = ScreenshotHandler(
                folder=Path(tmp) / "ScaleFallbackTonemapScreenshotCase",
                screenshot_count=1,
                optimize_screenshot=False,
            )
            tracks = [SimpleNamespace(track_type="Video", hdr_format="Dolby Vision")]

            with mock.patch.object(
                ScreenshotHandler,
                "_available_ffmpeg_filters",
                return_value={"scale", "tonemap"},
            ):
                args = handler._build_ffmpeg_args(
                    Path(tmp) / "movie.mkv",
                    Path(tmp) / "out.png",
                    "3840x2160",
                    62000,
                    tracks,
                )

        self.assertIn("scale=in_transfer=smpte2084:out_transfer=linear", args)
        self.assertIn("tonemap=tonemap=hable:desat=0:peak=1000", args)
        self.assertNotIn("zscale", args)
        self.assertIn("scale=3840:2160", args)

    def test_auto_tonemap_uses_hlg_transfer_for_hlg_tracks(self):
        handler = ScreenshotHandler(folder=Path("/tmp"), screenshot_count=1)
        tracks = [SimpleNamespace(track_type="Video", transfer_characteristics="HLG")]

        self.assertEqual(handler._hdr_input_transfer(tracks), "arib-std-b67")

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            ScreenshotHandler,
            "_available_ffmpeg_filters",
            return_value={"scale", "tonemap"},
        ):
            args = handler._build_ffmpeg_args(
                Path(tmp) / "movie.mkv",
                Path(tmp) / "out.png",
                "3840x2160",
                62000,
                tracks,
            )

        self.assertIn("scale=in_transfer=arib-std-b67:out_transfer=linear", args)
        self.assertIn("tonemap=tonemap=mobius:desat=0:peak=400", args)

    def test_auto_tonemap_leaves_sdr_screenshot_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = ScreenshotHandler(
                folder=Path(tmp) / "SdrScreenshotCase",
                screenshot_count=1,
                optimize_screenshot=False,
            )
            tracks = [
                SimpleNamespace(
                    track_type="Video",
                    transfer_characteristics="BT.709",
                    color_primaries="BT.709",
                )
            ]

            args = handler._build_ffmpeg_args(
                Path(tmp) / "movie.mkv",
                Path(tmp) / "out.png",
                "1920x1080",
                62000,
                tracks,
            )

        self.assertIn("-s 1920x1080", args)
        self.assertNotIn('-vf "', args)

    def test_no_tonemap_disables_hdr_auto_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = ScreenshotHandler(
                folder=Path(tmp) / "DisableTonemapScreenshotCase",
                screenshot_count=1,
                optimize_screenshot=False,
                screenshot_tonemap="never",
            )
            tracks = [SimpleNamespace(track_type="Video", hdr_format="Dolby Vision")]

            args = handler._build_ffmpeg_args(
                Path(tmp) / "movie.mkv",
                Path(tmp) / "out.png",
                "3840x2160",
                62000,
                tracks,
            )

        self.assertIn("-s 3840x2160", args)
        self.assertNotIn("tonemap", args)

    def test_auto_tonemap_detects_dolby_vision_codec_id(self):
        tracks = [SimpleNamespace(track_type="Video", codec_id="dvhe.05.06")]
        handler = ScreenshotHandler(folder=Path("/tmp"), screenshot_count=1)

        self.assertTrue(handler._should_tonemap(tracks))

    def test_force_tonemap_handles_missing_tracks(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = ScreenshotHandler(
                folder=Path(tmp) / "ForceTonemapScreenshotCase",
                screenshot_count=1,
                optimize_screenshot=False,
                screenshot_tonemap="always",
            )

            args = handler._build_ffmpeg_args(
                Path(tmp) / "movie.mkv",
                Path(tmp) / "out.png",
                "3840x2160",
                62000,
            )

        self.assertIn("tonemap=tonemap=hable", args)

    def test_generate_screenshots_executes_auto_tonemap_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = ScreenshotHandler(
                folder=Path(tmp) / "GenerateTonemapScreenshotCase",
                screenshot_count=1,
                optimize_screenshot=False,
            )
            tracks = [SimpleNamespace(track_type="Video", transfer_characteristics="HLG")]

            with mock.patch(
                "differential.utils.screenshot_handler.execute"
            ) as execute, mock.patch.object(
                ScreenshotHandler,
                "_available_ffmpeg_filters",
                return_value={"scale", "tonemap"},
            ):
                handler._generate_screenshots(
                    Path(tmp) / "movie.mkv",
                    "3840x2160",
                    Decimal("120000"),
                    tracks,
                )

        execute.assert_called_once()
        binary_name, args = execute.call_args.args
        self.assertEqual(binary_name, "ffmpeg")
        self.assertIn("tonemap=mobius", args)
        self.assertIn("scale=3840:2160", args)


if __name__ == "__main__":
    unittest.main()
