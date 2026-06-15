import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from differential.plugins.chdbits_encode import CHDBitsEncode
from differential.plugins.hdbits import HDBits
from differential.plugins.nexusphp import NexusPHP
from differential.utils.ptgen.imdb import IMDBData


class UploadedStub:
    def __str__(self):
        return "[img]shot[/img]"


class LegacyPluginCompatTest(unittest.TestCase):
    def test_base_exposes_legacy_handler_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = NexusPHP(folder=tmp, upload_url="https://example.test/upload.php")

        mediainfo = object()
        screenshot = object()
        plugin.mediainfo_handler = SimpleNamespace(
            is_bdmv=True,
            mediainfo=mediainfo,
            bdinfo="bdinfo text",
        )
        plugin.screenshot_handler = SimpleNamespace(screenshots=[screenshot])
        plugin.imdb = IMDBData(site="imdb", sid="tt1", success=True, genre=["Drama"])

        self.assertTrue(plugin.is_bdmv)
        self.assertIs(plugin._mediainfo, mediainfo)
        self.assertEqual(plugin._bdinfo, "bdinfo text")
        self.assertEqual(plugin._screenshots, [screenshot])
        self.assertEqual(plugin._imdb["genre"], ["Drama"])

    def test_hdbits_uses_legacy_aliases_for_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = HDBits(folder=tmp)

        plugin.mediainfo_handler = SimpleNamespace(
            is_bdmv=False,
            mediainfo=object(),
            bdinfo="bdinfo text",
        )
        plugin.screenshot_handler = SimpleNamespace(
            screenshots=[SimpleNamespace(__str__=lambda self: "[img]shot[/img]")]
        )

        with mock.patch("differential.plugins.hdbits.get_full_mediainfo", return_value="media info") as full:
            self.assertEqual(plugin.media_info, "media info")

        full.assert_called_once_with(plugin._mediainfo)

        plugin.mediainfo_handler.is_bdmv = True
        self.assertEqual(plugin.media_info, "")
        self.assertIn("[quote]bdinfo text[/quote]", plugin.description)

    def test_chdbits_encode_uses_legacy_aliases_for_media_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media_file = root / "Movie.mkv"
            media_file.write_bytes(b"video")
            plugin = CHDBitsEncode(folder=str(root), source_name="Source Disc")

        plugin.main_file = media_file
        plugin.ptgen = SimpleNamespace(format="ptgen format")
        plugin.imdb = IMDBData(
            site="imdb",
            sid="tt1",
            success=True,
            imdb_link="https://www.imdb.com/title/tt1/",
            imdb_rating="7.8/10",
            genre=["Drama"],
        )
        plugin.mediainfo_handler = SimpleNamespace(
            mediainfo=SimpleNamespace(
                general_tracks=[
                    SimpleNamespace(other_duration=["1 h 30 min"], other_file_size=["8.0 GiB"])
                ],
                video_tracks=[
                    SimpleNamespace(
                        encoded_library_name="x264",
                        commercial_name="AVC",
                        format_profile="High",
                        other_bit_rate=["10.0 Mb/s"],
                        other_frame_rate=["24.000 FPS"],
                        other_display_aspect_ratio=["16:9"],
                        width=1920,
                        height=1080,
                    )
                ],
                audio_tracks=[
                    SimpleNamespace(
                        other_language=["English"],
                        commercial_name="DTS",
                        other_channel_s=["5.1"],
                        other_bit_rate=["1 509 kb/s"],
                    )
                ],
                text_tracks=[],
                menu_tracks=[],
            )
        )
        plugin.screenshot_handler = SimpleNamespace(screenshots=[UploadedStub()])

        media_info = plugin.media_info
        description = plugin.description

        self.assertIn("GENRE...........: Drama", media_info)
        self.assertIn("RUNTiME.........: 1 h 30 min", media_info)
        self.assertIn("SOURCE..........: Source Disc (Thanks)", media_info)
        self.assertIn("[quote]" + media_info, description)
        self.assertIn("[img]shot[/img]", description)


if __name__ == "__main__":
    unittest.main()
