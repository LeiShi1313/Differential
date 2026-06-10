import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.rename.apply import apply_plan
from differential.utils.rename.models import RenameMetadata, TechnicalTokens
from differential.utils.rename.plan import RenamePlanError, build_rename_plan


class MediaRenameApplyTest(unittest.TestCase):
    def test_apply_renames_child_file_before_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Name"
            folder.mkdir()
            main = folder / "Old.Name.mkv"
            main.write_bytes(b"video")
            scan = SimpleNamespace(
                root=folder,
                main_file=main,
                media_files=[main],
                is_bdmv=False,
                is_direct_file=False,
            )
            plan = build_rename_plan(
                scan,
                RenameMetadata("Movie Title", "2024"),
                TechnicalTokens(resolution="1080p"),
            )

            applied = apply_plan(plan)

            self.assertEqual(len(applied), 2)
            self.assertTrue((Path(tmp) / "Movie.Title.2024.1080p" / "Movie.Title.2024.1080p.mkv").exists())

    def test_failed_validation_leaves_filesystem_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Name"
            folder.mkdir()
            main = folder / "Old.Name.mkv"
            main.write_bytes(b"video")
            (Path(tmp) / "Movie.Title.2024").mkdir()
            scan = SimpleNamespace(
                root=folder,
                main_file=main,
                media_files=[main],
                is_bdmv=False,
                is_direct_file=False,
            )

            with self.assertRaises(RenamePlanError):
                build_rename_plan(scan, RenameMetadata("Movie Title", "2024"), TechnicalTokens())

            self.assertTrue(folder.exists())
            self.assertTrue(main.exists())


if __name__ == "__main__":
    unittest.main()
