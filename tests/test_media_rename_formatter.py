import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.rename.formatter import build_release_stem, normalize_resolution, normalize_title
from differential.utils.rename.models import CodecTokenMap, RenameMetadata, TechnicalTokens
from differential.utils.rename.tokens import suggest_tokens


class MediaRenameFormatterTest(unittest.TestCase):
    def test_builds_pt_style_stem_with_separate_source_and_type(self):
        stem = build_release_stem(
            RenameMetadata(title="Movie Title", year="2024"),
            TechnicalTokens(
                resolution="2160p",
                source="NF",
                release_type="WEB-DL",
                video_codec="hevc",
                audio_codec="ddp5.1",
                uploader="NTb",
            ),
        )

        self.assertEqual(stem, "Movie.Title.2024.2160p.NF.WEB-DL.HEVC.DDP5.1-NTb")

    def test_empty_optional_tokens_drop_cleanly(self):
        stem = build_release_stem(
            RenameMetadata(title="Movie Title", year="2024"),
            TechnicalTokens(resolution="1080p", video_codec="h264"),
        )

        self.assertEqual(stem, "Movie.Title.2024.1080p.H264")

    def test_avc_normalizes_to_avc_by_default(self):
        stem = build_release_stem(
            RenameMetadata(title="Movie Title", year="2024"),
            TechnicalTokens(resolution="1080p", video_codec="AVC"),
        )

        self.assertEqual(stem, "Movie.Title.2024.1080p.AVC")

    def test_h265_normalizes_to_h265_by_default(self):
        stem = build_release_stem(
            RenameMetadata(title="Movie Title", year="2024"),
            TechnicalTokens(resolution="1080p", video_codec="H.265"),
        )

        self.assertEqual(stem, "Movie.Title.2024.1080p.H265")

    def test_aac_2_0_normalizes_to_aac_by_default(self):
        stem = build_release_stem(
            RenameMetadata(title="Movie Title", year="2024"),
            TechnicalTokens(resolution="1080p", audio_codec="AAC2.0"),
        )

        self.assertEqual(stem, "Movie.Title.2024.1080p.AAC")

    def test_codec_map_rewrites_final_normalized_codec_tokens(self):
        stem = build_release_stem(
            RenameMetadata(title="Movie Title", year="2024"),
            TechnicalTokens(resolution="1080p", video_codec="h264", audio_codec="AAC2.0"),
            codec_map=CodecTokenMap(video={"H264": "AVC"}, audio={"AAC": "AAC2.0"}),
        )

        self.assertEqual(stem, "Movie.Title.2024.1080p.AVC.AAC2.0")

    def test_tv_episode_token_goes_before_year(self):
        stem = build_release_stem(
            RenameMetadata(title="Show Title", year="2024", kind="tv", season="S01"),
            TechnicalTokens(resolution="1080p", source="AMZN", release_type="WEB-DL"),
            episode="S01E03",
        )

        self.assertEqual(stem, "Show.Title.S01E03.2024.1080p.AMZN.WEB-DL")

    def test_title_sanitizes_illegal_filename_characters(self):
        self.assertEqual(normalize_title('Bad: Movie / "Name"?'), "Bad.Movie.Name")

    def test_cropped_display_resolution_normalizes_to_release_class(self):
        self.assertEqual(normalize_resolution("3840x1600"), "2160p")
        self.assertEqual(normalize_resolution("1918x802"), "1080p")

    def test_remux_type_keeps_disc_medium(self):
        suggestions = suggest_tokens("Alpha.2025.UHD.BluRay.2160p.REMUX.HDR.HEVC.DTS-HD.MA.5.1-UBits")

        self.assertEqual(suggestions.release_types[0], "UHD.BluRay.REMUX")

    def test_uploader_suggestion_ignores_audio_codec_hyphens(self):
        suggestions = suggest_tokens("Alpha.2025.UHD.BluRay.2160p.REMUX.HDR.HEVC.DTS-HD.MA.5.1-UBits")

        self.assertEqual(suggestions.uploaders[0], "UBits")


if __name__ == "__main__":
    unittest.main()
