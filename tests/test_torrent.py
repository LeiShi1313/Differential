import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.torrent import make_torrent


class MakeTorrentTest(unittest.TestCase):
    def test_make_torrent_returns_generated_torrent_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "Movie.mkv"
            media.write_bytes(b"video")
            expected = Path(tmp) / "[Tracker].Movie.torrent"

            def write_torrent(path, overwrite=False):
                Path(path).write_bytes(b"torrent")

            torrent = mock.Mock()
            torrent.write.side_effect = write_torrent

            with mock.patch("differential.utils.torrent.Torrent", return_value=torrent):
                torrent_path = make_torrent(
                    media,
                    "https://tracker.example/announce",
                    prefix="Tracker",
                    reuse_torrent=False,
                )

            self.assertEqual(torrent_path, expected)
            self.assertTrue(expected.exists())


if __name__ == "__main__":
    unittest.main()
