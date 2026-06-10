import tempfile
import unittest

from differential.main import _redact_config
from differential.plugins.nexusphp import NexusPHP


class MainCliTest(unittest.TestCase):
    def test_nexus_plugin_accepts_missing_url_for_media_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = NexusPHP(folder=tmp, upload_url="https://example.test/upload.php")

        self.assertEqual(plugin.url, "")
        self.assertEqual(plugin.upload_url, "https://example.test/upload.php")

    def test_nexus_plugin_still_requires_upload_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(TypeError, "upload_url"):
                NexusPHP(folder=tmp)

    def test_redact_config_hides_secrets_without_mutating_source(self):
        config = {
            "folder": "/media/Movie",
            "ptpimg_api_key": "secret-api-key",
            "hdbits_cookie": "uid=secret",
            "lsky_password": "secret-password",
            "cloudinary_api_secret": "secret",
            "lsky_token": "",
            "screenshot_count": 0,
        }

        redacted = _redact_config(config)

        self.assertEqual(redacted["folder"], "/media/Movie")
        self.assertEqual(redacted["screenshot_count"], 0)
        self.assertEqual(redacted["ptpimg_api_key"], "<redacted>")
        self.assertEqual(redacted["hdbits_cookie"], "<redacted>")
        self.assertEqual(redacted["lsky_password"], "<redacted>")
        self.assertEqual(redacted["cloudinary_api_secret"], "<redacted>")
        self.assertEqual(redacted["lsky_token"], "")
        self.assertEqual(config["ptpimg_api_key"], "secret-api-key")


if __name__ == "__main__":
    unittest.main()
