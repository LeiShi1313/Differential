import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.rename.words import RenameWords, ReplacementRule, WordRule, apply_rename_words


class MediaRenameWordsTest(unittest.TestCase):
    def test_block_rules_run_before_replacements(self):
        words = RenameWords(
            block=(WordRule("sample"),),
            replace=(ReplacementRule("sample", "movie"),),
        )

        result = apply_rename_words("Sample.Release.2024", words)

        self.assertTrue(result.blocked)
        self.assertEqual(result.name, "Sample.Release.2024")
        self.assertEqual(result.blocked_by, "sample")

    def test_literal_replace_is_case_insensitive(self):
        words = RenameWords(replace=(ReplacementRule("WEB DL", "WEB-DL"),))

        result = apply_rename_words("Movie.2024.web dl.1080p", words)

        self.assertFalse(result.blocked)
        self.assertEqual(result.name, "Movie.2024.WEB-DL.1080p")
        self.assertEqual(result.applied, ("replace:WEB DL",))

    def test_regex_replace_requires_explicit_marker(self):
        words = RenameWords(replace=(ReplacementRule(r"\s+", ".", is_regex=True),))

        result = apply_rename_words("Movie Title 2024", words)

        self.assertEqual(result.name, "Movie.Title.2024")
        self.assertEqual(result.applied, (r"replace:\s+",))

    def test_invalid_regex_is_reported_as_warning(self):
        words = RenameWords(block=(WordRule("[", is_regex=True),))

        result = apply_rename_words("Movie.2024", words)

        self.assertFalse(result.blocked)
        self.assertIn("invalid block regex ignored: [", result.warnings[0])


if __name__ == "__main__":
    unittest.main()
