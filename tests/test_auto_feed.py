import base64
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.uploader.auto_feed import AutoFeed


def make_plugin(**overrides):
    defaults = {
        "title": "After the Flood S01 2024 2160p AMZN WEB-DL DDP5.1 HDR H 265-HHWEB",
        "subtitle": "",
        "imdb_url": "",
        "douban_url": "",
        "description": "Audio: Dolby Digital Plus",
        "screenshots": [],
        "category": "tvPack",
        "area": "US",
        "resolution": "2160p",
        "video_type": "web",
        "video_codec": "hevc",
        "audio_codec": "dd+",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def decode_info(info):
    encoded = info.split("separator#", 1)[1]
    decoded = unquote(base64.b64decode(encoded).decode())
    parts = decoded.split("#linkstr#")
    return dict(zip(parts[::2], parts[1::2]))


class AutoFeedTest(unittest.TestCase):
    def test_payload_uses_auto_feed_js_tokens_for_quality_fields(self):
        info = decode_info(AutoFeed(make_plugin()).info)

        self.assertEqual(info["type"], "剧集")
        self.assertEqual(info["source_sel"], "欧美")
        self.assertEqual(info["standard_sel"], "4K")
        self.assertEqual(info["medium_sel"], "WEB-DL")
        self.assertEqual(info["codec_sel"], "H265")
        self.assertEqual(info["audiocodec_sel"], "AC3")
        self.assertIn("DDP5.1", info["name"])

    def test_media_variants_are_canonicalized_for_auto_feed_js(self):
        cases = [
            (
                {"video_type": "uhdbluray", "video_codec": "x265", "audio_codec": "dtshdma"},
                ("UHD", "X265", "DTS-HDMA"),
            ),
            (
                {"video_type": "bluray", "video_codec": "vc-1", "audio_codec": "dts-x"},
                ("Blu-ray", "VC-1", "DTS-X"),
            ),
            (
                {"video_type": "remux", "video_codec": "mpeg-2", "audio_codec": "flac"},
                ("Remux", "MPEG-2", "Flac"),
            ),
        ]

        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                auto_feed = AutoFeed(make_plugin(**overrides))
                self.assertEqual(
                    (auto_feed.video_type, auto_feed.video_codec, auto_feed.audio_codec),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
