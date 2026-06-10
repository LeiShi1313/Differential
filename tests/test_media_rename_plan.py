import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.rename.models import RenameMetadata, TechnicalTokens
from differential.utils.rename.plan import RenamePlanError, build_rename_plan


class MediaRenamePlanTest(unittest.TestCase):
    def test_movie_folder_renames_main_file_and_subtitle_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Name"
            folder.mkdir()
            main = folder / "Old.Name.mkv"
            sub = folder / "Old.Name.en.forced.srt"
            main.write_bytes(b"video")
            sub.write_text("sub", encoding="utf-8")
            scan = _scan(folder, main, [main])

            plan = build_rename_plan(
                scan,
                RenameMetadata("Movie Title", "2024"),
                TechnicalTokens(resolution="1080p", source="NF", release_type="WEB-DL"),
            )

            targets = {operation.target.name for operation in plan.operations}
            self.assertIn("Movie.Title.2024.1080p.NF.WEB-DL.mkv", targets)
            self.assertIn("Movie.Title.2024.1080p.NF.WEB-DL.en.forced.srt", targets)
            self.assertIn("Movie.Title.2024.1080p.NF.WEB-DL", targets)

    def test_info_sidecar_requires_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Name"
            folder.mkdir()
            main = folder / "Old.Name.mkv"
            nfo = folder / "Old.Name.nfo"
            main.write_bytes(b"video")
            nfo.write_text("nfo", encoding="utf-8")
            scan = _scan(folder, main, [main])
            metadata = RenameMetadata("Movie Title", "2024")
            tokens = TechnicalTokens(resolution="1080p")

            without_flag = build_rename_plan(scan, metadata, tokens)
            with_flag = build_rename_plan(scan, metadata, tokens, include_info_sidecars=True)

            self.assertNotIn("Movie.Title.2024.1080p.nfo", {op.target.name for op in without_flag.operations})
            self.assertIn("Movie.Title.2024.1080p.nfo", {op.target.name for op in with_flag.operations})

    def test_bdmv_is_folder_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old Disc"
            stream = folder / "BDMV" / "STREAM" / "00001.m2ts"
            stream.parent.mkdir(parents=True)
            stream.write_bytes(b"stream")
            scan = _scan(folder, stream, [stream], is_bdmv=True)

            plan = build_rename_plan(
                scan,
                RenameMetadata("Movie Title", "2024"),
                TechnicalTokens(resolution="1080p"),
            )

            self.assertEqual([operation.kind for operation in plan.operations], ["folder"])
            self.assertIn("BDMV detected", plan.warnings[0])

    def test_tv_renames_stable_episode_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Show.S01"
            folder.mkdir()
            ep1 = folder / "Old.Show.S01E01.mkv"
            ep2 = folder / "Old.Show.S01E02.mkv"
            ep1.write_bytes(b"1")
            ep2.write_bytes(b"2")
            scan = _scan(folder, ep1, [ep1, ep2])

            plan = build_rename_plan(
                scan,
                RenameMetadata("Show Title", "2024", kind="tv", season="S01"),
                TechnicalTokens(resolution="1080p"),
            )

            targets = {operation.target.name for operation in plan.operations}
            self.assertIn("Show.Title.S01E01.2024.1080p.mkv", targets)
            self.assertIn("Show.Title.S01E02.2024.1080p.mkv", targets)

    def test_tv_unclear_episode_falls_back_to_folder_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Show.S01"
            folder.mkdir()
            video = folder / "Old.Show.Part.One.mkv"
            video.write_bytes(b"1")
            scan = _scan(folder, video, [video])

            plan = build_rename_plan(
                scan,
                RenameMetadata("Show Title", "2024", kind="tv", season="S01"),
                TechnicalTokens(resolution="1080p"),
            )

            self.assertEqual([operation.kind for operation in plan.operations], ["folder"])
            self.assertIn("TV episode identity is unclear", plan.warnings[0])

    def test_tv_renames_numeric_episode_files_when_season_is_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Show.S01"
            folder.mkdir()
            ep1 = folder / "01.mkv"
            ep2 = folder / "02.mkv"
            ep1.write_bytes(b"1")
            ep2.write_bytes(b"2")
            scan = _scan(folder, ep1, [ep1, ep2])

            plan = build_rename_plan(
                scan,
                RenameMetadata("Show Title", "2024", kind="tv", season="S01"),
                TechnicalTokens(resolution="1080p"),
            )

            targets = {operation.target.name for operation in plan.operations}
            self.assertIn("Show.Title.S01E01.2024.1080p.mkv", targets)
            self.assertIn("Show.Title.S01E02.2024.1080p.mkv", targets)

    def test_tv_renames_chinese_episode_files_when_season_is_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Show.S01"
            folder.mkdir()
            ep1 = folder / "第01集.mkv"
            ep1.write_bytes(b"1")
            scan = _scan(folder, ep1, [ep1])

            plan = build_rename_plan(
                scan,
                RenameMetadata("Show Title", "2024", kind="tv", season="S01"),
                TechnicalTokens(resolution="1080p"),
            )

            targets = {operation.target.name for operation in plan.operations}
            self.assertIn("Show.Title.S01E01.2024.1080p.mkv", targets)

    def test_tv_renames_episode_word_files_when_season_is_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Show.S01"
            folder.mkdir()
            ep1 = folder / "Episode 1.mkv"
            ep1.write_bytes(b"1")
            scan = _scan(folder, ep1, [ep1])

            plan = build_rename_plan(
                scan,
                RenameMetadata("Show Title", "2024", kind="tv", season="S01"),
                TechnicalTokens(resolution="1080p"),
            )

            targets = {operation.target.name for operation in plan.operations}
            self.assertIn("Show.Title.S01E01.2024.1080p.mkv", targets)

    def test_collision_detection_fails_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Old.Name"
            folder.mkdir()
            main = folder / "Old.Name.mkv"
            main.write_bytes(b"video")
            (Path(tmp) / "Movie.Title.2024").mkdir()
            scan = _scan(folder, main, [main])

            with self.assertRaises(RenamePlanError):
                build_rename_plan(scan, RenameMetadata("Movie Title", "2024"), TechnicalTokens())

    def test_folder_only_rejects_direct_file_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "Old.Name.mkv"
            video.write_bytes(b"video")
            scan = _scan(video, video, [video], is_direct_file=True)

            with self.assertRaises(RenamePlanError):
                build_rename_plan(scan, RenameMetadata("Movie Title", "2024"), TechnicalTokens(), folder_only=True)

    def test_direct_tv_episode_keeps_episode_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "Show.S02E01.mkv"
            video.write_bytes(b"video")
            scan = _scan(video, video, [video], is_direct_file=True)

            plan = build_rename_plan(
                scan,
                RenameMetadata("Show Title", "2025", kind="tv", season="S02", episode="E01"),
                TechnicalTokens(resolution="1080p"),
            )

            self.assertEqual(plan.operations[0].target.name, "Show.Title.S02E01.2025.1080p.mkv")

    def test_direct_iso_with_bdmv_allows_iso_file_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            iso = Path(tmp) / "Old.Name.iso"
            iso.write_bytes(b"iso")
            scan = _scan(iso, iso, [iso], is_bdmv=True, is_direct_file=True)

            plan = build_rename_plan(
                scan,
                RenameMetadata("Movie Title", "2024"),
                TechnicalTokens(resolution="2160p", release_type="UHD.BluRay"),
            )

            self.assertEqual(plan.operations[0].target.name, "Movie.Title.2024.2160p.UHD.BluRay.iso")
            self.assertIn("BDMV detected inside direct file input", plan.warnings[0])


def _scan(root, main, media_files, is_bdmv=False, is_direct_file=False):
    return SimpleNamespace(
        root=root,
        main_file=main,
        media_files=media_files,
        is_bdmv=is_bdmv,
        is_direct_file=is_direct_file,
    )


if __name__ == "__main__":
    unittest.main()
