
from pathlib import Path


def generate_nfo(folder: Path, media_info: str):
    logger.info("[NFO] 正在生成nfo文件...")
    if folder.is_file():
        with open(f"{folder.resolve().parent.joinpath(folder.stem)}.nfo", "wb") as f:
            f.write(media_info.encode())
    elif folder.is_dir():
        with open(folder.joinpath(f"{folder.name}.nfo"), "wb") as f:
            f.write(media_info.encode())