import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.ptgen.base import PTGenData
from differential.utils.ptgen.douban import DoubanData
from differential.utils.ptgen.imdb import IMDBData
from differential.utils.rename.metadata import fetch_url_metadata, manual_metadata, metadata_from_ptgen


class MediaRenameMetadataTest(unittest.TestCase):
    def test_manual_metadata_skips_ptgen(self):
        metadata = manual_metadata("Movie Title", 2024)

        self.assertEqual(metadata.title, "Movie Title")
        self.assertEqual(metadata.year, "2024")

    def test_imdb_name_beats_douban_chinese_title(self):
        metadata = metadata_from_ptgen(
            PTGenData(site="douban", sid="1", success=True),
            DoubanData(chinese_title="中文名", year="2024"),
            IMDBData(name="English Title", year="2024"),
        )

        self.assertEqual(metadata.title, "English Title")

    def test_douban_foreign_title_beats_chinese_title(self):
        metadata = metadata_from_ptgen(
            PTGenData(site="douban", sid="1", success=True),
            DoubanData(chinese_title="中文名", foreign_title="Foreign Title", year="2024"),
            None,
        )

        self.assertEqual(metadata.title, "Foreign Title")

    def test_url_metadata_uses_ptgen_handler(self):
        handler = mock.Mock()
        handler.fetch_ptgen_info.return_value = (
            PTGenData(site="imdb", sid="tt1", success=True),
            None,
            IMDBData(name="IMDb Title", year="2024"),
        )

        with mock.patch("differential.utils.rename.metadata.PTGenHandler", return_value=handler):
            metadata, _ptgen, _douban, _imdb = fetch_url_metadata("https://www.imdb.com/title/tt1/")

        self.assertEqual(metadata.title, "IMDb Title")
        handler.fetch_ptgen_info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
