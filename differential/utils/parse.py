import re
from pathlib import Path


def parse_encoder_log(encoder_log: str):
    log = ""
    if encoder_log and Path(encoder_log).is_file():
        with open(encoder_log, "r") as f:
            log = f.read()
    m = re.search(
        r".*?(x264 \[info]: frame I:.*?)\n"
        r".*?(x264 \[info]: frame P:.*?)\n"
        r".*?(x264 \[info]: frame B:.*?)\n"
        r".*?(x264 \[info]: consecutive B-frames:.*?)\n",
        log,
    )
    if m:
        return "\n".join(m.groups())
    m = re.search(
        r".*?(x265 \[info]: frame I:.*?)\n"
        r".*?(x265 \[info]: frame P:.*?)\n"
        r".*?(x265 \[info]: frame B:.*?)\n"
        r".*?(x265 \[info]: Weighted P-Frames:.*?)\n"
        r".*?(x265 \[info]: Weighted B-Frames:.*?)\n"
        r".*?(x265 \[info]: consecutive B-frames:.*?)\n",
        log,
    )
    if m:
        return "\n".join(m.groups())
    return ""
