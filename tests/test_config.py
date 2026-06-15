import argparse
import os
import sys
import tempfile
import textwrap
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.plugins.chdbits_encode import CHDBitsEncode
from differential.plugins.nexusphp import NexusPHP
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
                    screenshot_tonemap = auto
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
        self.assertEqual(merged["screenshot_tonemap"], "auto")
        self.assertEqual(merged["screenshot_count"], 0)

    def test_screenshot_tonemap_boolean_aliases(self):
        for value, expected in (("true", "always"), ("false", "never")):
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as tmp:
                    config = Path(tmp) / "config.ini"
                    config.write_text(
                        textwrap.dedent(
                            f"""
                            [NexusPHP]
                            screenshot_tonemap = {value}
                            """
                        ).strip(),
                        encoding="utf-8",
                    )

                    merged = merge_config(
                        Namespace(config=str(config), plugin="NexusPHP", section="")
                    )

                self.assertEqual(merged["screenshot_tonemap"], expected)

    def test_missing_default_config_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmp)
                args = argparse.Namespace(
                    config="config.ini",
                    plugin="NexusPHP",
                    folder="/media/Movie",
                    upload_url="https://example.test/upload.php",
                )

                merged = merge_config(args)
            finally:
                os.chdir(old_cwd)

        self.assertEqual(merged["folder"], "/media/Movie")
        self.assertEqual(merged["upload_url"], "https://example.test/upload.php")

    def test_missing_custom_config_raises(self):
        args = argparse.Namespace(
            config="/no/such/config.ini",
            plugin="NexusPHP",
            folder="/media/Movie",
            upload_url="https://example.test/upload.php",
        )

        with self.assertRaisesRegex(FileNotFoundError, "config file does not exist"):
            merge_config(args)

    def test_unknown_config_key_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                "[DEFAULT]\n"
                "folder = /media/Movie\n"
                "upload_url = https://example.test/upload.php\n"
                "not_a_real_key = true\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(config=str(config), plugin="NexusPHP")

            with self.assertRaisesRegex(ValueError, "unsupported config key: not_a_real_key"):
                merge_config(args)

    def test_invalid_boolean_config_value_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                "[DEFAULT]\n"
                "folder = /media/Movie\n"
                "upload_url = https://example.test/upload.php\n"
                "make_torrent = maybe\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(config=str(config), plugin="NexusPHP")

            with self.assertRaisesRegex(ValueError, "invalid boolean value for make_torrent"):
                merge_config(args)

    def test_invalid_auto_feed_boolean_config_value_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                "[DEFAULT]\n"
                "folder = /media/Movie\n"
                "upload_url = https://example.test/upload.php\n"
                "auto_feed = maybe\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(config=str(config), plugin="NexusPHP")

            with self.assertRaisesRegex(ValueError, "invalid boolean value for auto_feed"):
                merge_config(args)

    def test_plugin_specific_config_keys_are_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.ini"
            config.write_text(
                "[DEFAULT]\n"
                "folder = /media/Movie\n"
                "source_name = Source Disc\n"
                "encoder = Alice\n"
                "make_torrent = yes\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(config=str(config), plugin="CHDBitsEncode")

            merged = merge_config(args)

        self.assertEqual(merged["source_name"], "Source Disc")
        self.assertEqual(merged["encoder"], "Alice")
        self.assertTrue(merged["make_torrent"])


if __name__ == "__main__":
    unittest.main()
