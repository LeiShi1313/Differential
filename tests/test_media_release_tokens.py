import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.rename.release_groups import ReleaseGroupConfig
from differential.utils.rename.release_tokens import parse_release_tokens


class MediaReleaseTokensTest(unittest.TestCase):
    def test_parses_web_release_tokens_separately(self):
        tokens = parse_release_tokens(
            "Example.Show.S01E01.2160p.NF.WEB-DL.DDP5.1.Atmos.HEVC-GRP"
        )

        self.assertEqual(tokens.source, "NF")
        self.assertEqual(tokens.release_type, "WEB-DL")
        self.assertEqual(tokens.resolution, "2160p")
        self.assertEqual(tokens.video_codec, "HEVC")
        self.assertEqual(tokens.audio_codec, "DDP5.1.Atmos")
        self.assertEqual(tokens.uploader, "GRP")
        self.assertEqual(tokens.release_group, "GRP")

    def test_combines_uhd_bluray_remux_and_preserves_audio_token(self):
        tokens = parse_release_tokens(
            "Alpha.2025.UHD.BluRay.2160p.REMUX.HDR.HEVC.DTS-HD.MA.5.1-UBits"
        )

        self.assertEqual(tokens.release_type, "UHD.BluRay.REMUX")
        self.assertEqual(tokens.resolution, "2160p")
        self.assertEqual(tokens.hdr, "HDR")
        self.assertEqual(tokens.video_codec, "HEVC")
        self.assertEqual(tokens.audio_codec, "DTS-HD.MA.5.1")
        self.assertEqual(tokens.uploader, "UBits")

    def test_normalizes_common_aliases_to_formatter_values(self):
        tokens = parse_release_tokens(
            "Movie.2024.4K.DOVI.H.265.DDP.5.1.Atmos-GROUP"
        )

        self.assertEqual(tokens.resolution, "2160p")
        self.assertEqual(tokens.hdr, "DV")
        self.assertEqual(tokens.video_codec, "H265")
        self.assertEqual(tokens.audio_codec, "DDP5.1.Atmos")

    def test_audio_fragment_without_suffix_is_not_uploader(self):
        tokens = parse_release_tokens("Alpha.2025.1080p.BluRay.DTS-HD.MA.5.1")

        self.assertEqual(tokens.audio_codec, "DTS-HD.MA.5.1")
        self.assertEqual(tokens.uploader, "")
        self.assertEqual(tokens.release_group, "")

    def test_release_type_suffix_is_not_uploader(self):
        tokens = parse_release_tokens("Movie.2024.1080p.WEB-DL")

        self.assertEqual(tokens.release_type, "WEB-DL")
        self.assertEqual(tokens.uploader, "")

    def test_custom_release_group_canonicalizes_suffix(self):
        tokens = parse_release_tokens(
            "Movie.2024.1080p.WEB-DL.H264-mygrp",
            release_groups=ReleaseGroupConfig(groups=("MyGrp",)),
        )

        self.assertEqual(tokens.release_group, "MyGrp")
        self.assertEqual(tokens.uploader, "MyGrp")
        self.assertEqual(tokens.release_group_source, "custom")
        self.assertEqual(tokens.release_group_confidence, "high")

    def test_custom_release_group_matches_final_token(self):
        tokens = parse_release_tokens(
            "Movie.2024.1080p.WEB-DL.H264.ADWeb",
            release_groups=ReleaseGroupConfig(groups=("ADWeb",)),
        )

        self.assertEqual(tokens.release_group, "ADWeb")
        self.assertEqual(tokens.release_group_source, "custom")

    def test_unconfigured_suffix_is_lower_confidence_fallback(self):
        tokens = parse_release_tokens("Movie.2024.1080p.WEB-DL.H264-GRP")

        self.assertEqual(tokens.release_group, "GRP")
        self.assertEqual(tokens.release_group_source, "suffix")
        self.assertEqual(tokens.release_group_confidence, "medium")

    def test_at_suffix_wins_over_earlier_hyphen(self):
        tokens = parse_release_tokens("Movie.2024.2160p.WEB-DL.H265.HDR.DV-DIY@HDSWEB")

        self.assertEqual(tokens.release_group, "HDSWEB")
        self.assertEqual(tokens.release_group_source, "suffix")


if __name__ == "__main__":
    unittest.main()
