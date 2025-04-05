import pickle
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from differential.constants import ImageHosting

@dataclass
class ImageUploaded:
    hosting: ImageHosting
    image: Path
    url: str
    thumb: Optional[str] = None

    @classmethod
    def from_pickle(cls, image: Path, hosting: ImageHosting) -> Optional['ImageUploaded']:
        try:
            with open(image.parent.joinpath(f".{image.stem}.{hosting.value}"), 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

    def __post_init__(self):
        with open(self.image.parent.joinpath(f".{self.image.stem}.{self.hosting.value}"), 'wb') as f:
            pickle.dump(self, f)

    def __str__(self):
        if self.thumb:
            return f"[url={self.url}][img]{self.thumb}[/img][/url]"
        return f"[img]{self.url}[/img]"
