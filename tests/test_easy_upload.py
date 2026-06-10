import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.uploader.easy_upload import EasyUpload


def make_plugin(**overrides):
    defaults = {
        "title": "After the Flood S01 2024 2160p AMZN WEB-DL DDP5.1 HDR H 265-HHWEB",
        "subtitle": "",
        "description": "",
        "original_description": "",
        "douban_url": "",
        "douban_info": "",
        "imdb_url": "",
        "media_info": "",
        "media_infos": [],
        "screenshots": [],
        "poster": "",
        "year": "2024",
        "category": "tvPack",
        "video_type": "WEB-DL",
        "format": ".mkv",
        "source": "WEB-DL",
        "video_codec": "H.265",
        "audio_codec": "DDP",
        "resolution": "4K",
        "area": "US",
        "movie_aka_name": "",
        "movie_name": "After the Flood",
        "size": 0,
        "tags": {},
        "other_tags": {},
        "comparisons": [],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class EasyUploadTest(unittest.TestCase):
    def test_payload_uses_easy_upload_canonical_media_values(self):
        info = EasyUpload(make_plugin()).torrent_info

        self.assertEqual(info["videoType"], "web")
        self.assertEqual(info["source"], "web")
        self.assertEqual(info["videoCodec"], "hevc")
        self.assertEqual(info["audioCodec"], "dd+")
        self.assertEqual(info["resolution"], "2160p")

    def test_differential_native_values_are_preserved(self):
        info = EasyUpload(
            make_plugin(
                video_type="web",
                source="",
                video_codec="hevc",
                audio_codec="dd+",
                resolution="2160p",
            )
        ).torrent_info

        self.assertEqual(info["videoType"], "web")
        self.assertEqual(info["source"], "web")
        self.assertEqual(info["videoCodec"], "hevc")
        self.assertEqual(info["audioCodec"], "dd+")
        self.assertEqual(info["resolution"], "2160p")

    def test_media_variants_are_canonicalized_for_easy_upload(self):
        cases = [
            (
                {
                    "video_type": "UltraHD Blu-ray",
                    "source": "Blu-ray",
                    "video_codec": "x265",
                    "audio_codec": "DTS-HD MA",
                    "resolution": "8K",
                },
                ("uhdbluray", "bluray", "x265", "dtshdma", "4320p"),
            ),
            (
                {
                    "video_type": "Blu-ray",
                    "source": "HDTV",
                    "video_codec": "VC-1",
                    "audio_codec": "DTS:X",
                    "resolution": "SD",
                },
                ("bluray", "hdtv", "vc1", "dtsx", "480p"),
            ),
            (
                {
                    "video_type": "Remux",
                    "source": "WEBRip",
                    "video_codec": "MPEG-2",
                    "audio_codec": "Dolby Digital",
                    "resolution": "1080i",
                },
                ("remux", "web", "mpeg2", "dd", "1080i"),
            ),
        ]

        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                info = EasyUpload(make_plugin(**overrides)).torrent_info
                self.assertEqual(
                    (
                        info["videoType"],
                        info["source"],
                        info["videoCodec"],
                        info["audioCodec"],
                        info["resolution"],
                    ),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
