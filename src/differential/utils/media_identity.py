import hashlib
from pathlib import Path
from typing import Iterable, Optional


IDENTITY_VERSION = "v1"
BDINFO_CACHE_VERSION = "v2"
SAMPLE_SIZE = 1024 * 1024
BDMV_HASHED_STREAMS = 3


def sampled_file_hash(path: Path, sample_size: int = SAMPLE_SIZE) -> str:
    path = Path(path)
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(IDENTITY_VERSION.encode("ascii"))
    digest.update(b"\0file\0")
    digest.update(str(size).encode("ascii"))
    digest.update(b"\0")

    if size <= sample_size * 3:
        offsets = [0]
    else:
        offsets = [0, max(0, size // 2 - sample_size // 2), max(0, size - sample_size)]

    with path.open("rb") as handle:
        for offset in offsets:
            handle.seek(offset)
            digest.update(str(offset).encode("ascii"))
            digest.update(b"\0")
            digest.update(handle.read(sample_size))
            digest.update(b"\0")

    return digest.hexdigest()


def media_file_identity(path: Path) -> str:
    path = Path(path)
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(IDENTITY_VERSION.encode("ascii"))
    digest.update(b"\0media-file\0")
    digest.update(str(size).encode("ascii"))
    digest.update(b"\0")
    digest.update(sampled_file_hash(path).encode("ascii"))
    return digest.hexdigest()


def bdmv_identity(folder: Path) -> str:
    folder = Path(folder)
    digest = hashlib.sha256()
    digest.update(IDENTITY_VERSION.encode("ascii"))
    digest.update(b"\0bdmv\0")

    files = list(_bdmv_relevant_files(folder))
    for file_path in files:
        relative = file_path.relative_to(folder).as_posix().lower()
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(str(file_path.stat().st_size).encode("ascii"))
        digest.update(b"\0")

    streams = sorted(
        (path for path in files if path.suffix.lower() == ".m2ts"),
        key=lambda path: path.stat().st_size,
        reverse=True,
    )[:BDMV_HASHED_STREAMS]
    for stream in streams:
        relative = stream.relative_to(folder).as_posix().lower()
        digest.update(b"stream-hash\0")
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(sampled_file_hash(stream).encode("ascii"))
        digest.update(b"\0")

    return digest.hexdigest()


def media_identity(path: Path, main_file: Optional[Path] = None, is_bdmv: bool = False) -> str:
    path = Path(path)
    if path.is_file():
        return media_file_identity(path)
    if is_bdmv:
        return bdmv_identity(path)
    if main_file:
        return media_file_identity(Path(main_file))
    raise ValueError(f"cannot build stable media identity without a main file: {path}")


def bdinfo_cache_key(identity: str) -> str:
    return f"Differential.bdinfo.{BDINFO_CACHE_VERSION}.{identity}"


def _bdmv_relevant_files(folder: Path) -> Iterable[Path]:
    roots = [folder / "BDMV", folder / "CERTIFICATE"]
    files = []
    for root in roots:
        if root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(files, key=lambda path: path.relative_to(folder).as_posix().lower())
