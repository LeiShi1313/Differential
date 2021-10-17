from typing import List
from pathlib import Path

from torf import Torrent
from loguru import logger

from differential.version import version


def make_torrent_progress(torrent, filepath, pieces_done, pieces_total):
    logger.info(f'制种进度: {pieces_done/pieces_total*100:3.0f} %')

def make_torrent(path: Path, trackers: List[str]):
    logger.info("正在生成种子...")
    t = Torrent(path=path, trackers=trackers,
                comment=f"Generate by Differential {version} made by XGCM")
    t.private = True
    t.generate(callback=make_torrent_progress, interval=1)
    t.write(path.resolve().parent.joinpath(f"{path.name if path.is_dir() else path.stem}.torrent"), overwrite=True)
