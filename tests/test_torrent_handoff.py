import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.torrent_handoff import torrent_file_to_base64, upload_torrent


class FakeResponse:
    def __init__(self, text="", json_data=None):
        self.text = text
        self._json_data = json_data

    def raise_for_status(self):
        return None

    def json(self):
        if self._json_data is None:
            raise ValueError("not json")
        return self._json_data


class TorrentHandoffTest(unittest.TestCase):
    def test_torrent_file_to_base64_encodes_file_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            torrent = Path(tmp) / "movie.torrent"
            torrent.write_bytes(b"torrent-bytes")

            self.assertEqual(torrent_file_to_base64(torrent), "dG9ycmVudC1ieXRlcw==")

    def test_upload_torrent_posts_raw_file_to_redirect_service(self):
        response = FakeResponse(json_data={"torrentUrl": "https://r.leishi.xyz/torrent/abc123"})
        with tempfile.TemporaryDirectory() as tmp:
            torrent = Path(tmp) / "movie.torrent"
            torrent.write_bytes(b"torrent-bytes")

            with mock.patch(
                "differential.utils.torrent_handoff.requests.post",
                return_value=response,
            ) as post:
                url = upload_torrent(torrent)

        self.assertEqual(url, "https://r.leishi.xyz/torrent/abc123")
        self.assertEqual(post.call_args.args[0], "https://r.leishi.xyz/torrent")
        self.assertEqual(post.call_args.kwargs["timeout"], 30)
        self.assertEqual(post.call_args.kwargs["data"], b"torrent-bytes")
        self.assertEqual(
            post.call_args.kwargs["headers"],
            {"content-type": "application/x-bittorrent"},
        )

    def test_upload_torrent_accepts_bare_response_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            torrent = Path(tmp) / "movie.torrent"
            torrent.write_bytes(b"torrent-bytes")

            with mock.patch(
                "differential.utils.torrent_handoff.requests.post",
                return_value=FakeResponse(text="abc123"),
            ):
                url = upload_torrent(torrent)

        self.assertEqual(url, "https://r.leishi.xyz/torrent/abc123")


if __name__ == "__main__":
    unittest.main()
