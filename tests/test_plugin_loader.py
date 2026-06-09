import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.plugin_loader import _fqname


class PluginLoaderTest(unittest.TestCase):
    def test_fqname_uses_package_segment_inside_pipx_venv(self):
        path = Path(
            "/tmp/differential-pipx-home/venvs/differential/lib/python3.14/"
            "site-packages/differential/plugins/chdbits_encode.py"
        )

        self.assertEqual(_fqname(path), "differential.plugins.chdbits_encode")


if __name__ == "__main__":
    unittest.main()
