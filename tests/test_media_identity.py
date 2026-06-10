import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.media_identity import bdmv_identity, media_file_identity


class MediaIdentityTest(unittest.TestCase):
    def test_file_identity_survives_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "Old.Name.mkv"
            path.write_bytes(b"same media bytes")
            before = media_file_identity(path)
            renamed = root / "New.Name.mkv"
            path.rename(renamed)

            self.assertEqual(media_file_identity(renamed), before)

    def test_bdmv_identity_ignores_top_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "Old Disc"
            second = root / "New Disc"
            for folder in (first, second):
                stream = folder / "BDMV" / "STREAM" / "00001.m2ts"
                stream.parent.mkdir(parents=True)
                stream.write_bytes(b"stream data")
                (folder / "BDMV" / "index.bdmv").write_bytes(b"index")

            self.assertEqual(bdmv_identity(first), bdmv_identity(second))

    def test_bdmv_identity_changes_when_stream_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Disc"
            stream = folder / "BDMV" / "STREAM" / "00001.m2ts"
            stream.parent.mkdir(parents=True)
            stream.write_bytes(b"stream data")
            before = bdmv_identity(folder)
            stream.write_bytes(b"changed stream data")

            self.assertNotEqual(bdmv_identity(folder), before)


if __name__ == "__main__":
    unittest.main()
