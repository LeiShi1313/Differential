import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from differential.utils import binary


class BinaryHelperTest(unittest.TestCase):
    def test_execute_decodes_non_utf8_output_with_replacement(self):
        proc = subprocess.CompletedProcess("cmd", 0, stdout=b"ok", stderr=b"\xe8")
        with mock.patch.object(binary, "build_cmd", return_value="cmd"), mock.patch(
            "subprocess.run", return_value=proc
        ):
            output = binary.execute("ffprobe", "-i file")

        self.assertIn("ok", output)
        self.assertIn("\ufffd", output)


if __name__ == "__main__":
    unittest.main()
