import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from differential.plugins.hdbits import HDBits
from differential.plugins.nexusphp import NexusPHP
from differential.utils.ptgen.imdb import IMDBData


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


if __name__ == "__main__":
    unittest.main()
