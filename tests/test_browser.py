import unittest
import webbrowser
from unittest import mock

from differential import constants
from differential.utils.browser import open_link


class BrowserHelperTest(unittest.TestCase):
    def test_short_url_uses_leishi_redirect_domain(self):
        response = mock.Mock(ok=True, text="abc123")

        with mock.patch("differential.utils.browser.requests.post", return_value=response) as post, mock.patch(
            "differential.utils.browser.webbrowser.get",
            side_effect=webbrowser.Error("no browser"),
        ):
            open_link("https://example.test/upload", use_short_url=True)

        self.assertEqual(constants.URL_SHORTENER_PATH, "https://r.leishi.xyz")
        post.assert_called_once_with("https://r.leishi.xyz/new", {"url": "https://example.test/upload"})


if __name__ == "__main__":
    unittest.main()
