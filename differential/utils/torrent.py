from pathlib import Path
from typing import List, Optional

import bencodepy
from torf import Torrent
from loguru import logger

from differential.version import version


def remake_torrent(path: Path, tracker: str, old_torrent: str) -> Optional[bytes]:
    if not Path(old_torrent).is_file():
        return None
    try:
        with open(old_torrent, 'rb') as f:
            t = f.read()
            torrent = bencodepy.decode(t)
    except:
        import traceback
        traceback.print_exc()
        return None

    _name = torrent.get(b'info', {}).get(b'name').decode()
    if _name != path.name:
        logger.warning(f"洗种的基础种子很可能不匹配！基础种子文件名为：{_name}，而将要制种的文件名为：{path.name}")

    new_torrent = {}
    new_torrent[b'announce'] = tracker
    new_torrent[b'created by'] = f"Differential {version}"
    new_torrent[b'comment'] = f"Generate by Differential {version} made by XGCM"
    new_torrent[b'info'] = {b'private': 1}
    for k, v in torrent[b'info'].items():
        if k in (b'files', b'name', b'piece length', b'pieces'):
            new_torrent[b'info'][k] = v
    return bencodepy.encode(new_torrent)


def make_torrent_progress(torrent, filepath, pieces_done, pieces_total):
    logger.info(f'制种进度: {pieces_done/pieces_total*100:3.0f} %')


def make_torrent(path: Path, tracker: str, prefix: str = None, reuse_torrent: bool = True, from_torrent: str = None):
    torrent_name = path.resolve().parent.joinpath((f"[{prefix}]." if prefix else '') + f"{path.name if path.is_dir() else path.stem}.torrent")
    if from_torrent and Path(from_torrent).is_file():
        logger.info(f"正在基于{from_torrent}制作种子...")
        torrent = remake_torrent(path, tracker, from_torrent)
        if torrent:
            with open(torrent_name, 'wb') as f:
                f.write(torrent)
            logger.info(f"种子制作完成：{torrent_name.absolute()}")
            return
    if reuse_torrent:
        for f in path.resolve().parent.glob(f'*{path.name if path.is_dir() else path.stem}.torrent'):
            logger.info(f"正在基于{f.name}制作种子...")
            torrent = remake_torrent(path, tracker, f)
            if torrent:
                with open(torrent_name, 'wb') as f:
                    f.write(torrent)
                logger.info(f"种子制作完成：{torrent_name.absolute()}")
                return
        
    logger.info("正在生成种子...")
    t = Torrent(path=path, trackers=[tracker],
                created_by=f"Differential {version}",
                comment=f"Generate by Differential {version} made by XGCM")
    t.private = True
    t.generate(callback=make_torrent_progress, interval=1)
    t.write(torrent_name, overwrite=True)
    logger.info(f"种子制作完成：{torrent_name.absolute()}")
