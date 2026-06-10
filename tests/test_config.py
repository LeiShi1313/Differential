import sys
import tempfile
import textwrap
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils.config import merge_config


class ConfigTest(unittest.TestCase):
    def test_auto_feed_is_parsed_as_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                textwrap.dedent(
                    """
                    [DEFAULT]
                    easy_upload = false
                    auto_feed = true

                    [NexusPHP]
                    easy_upload = true
                    auto_feed = false
                    screenshot_count = 0
                    """
                ).strip(),
                encoding="utf-8",
            )

            merged = merge_config(
                Namespace(config=str(config), plugin="NexusPHP", section="")
            )

        self.assertIs(merged["easy_upload"], True)
        self.assertIs(merged["auto_feed"], False)
        self.assertEqual(merged["screenshot_count"], 0)


if __name__ == "__main__":
    unittest.main()
