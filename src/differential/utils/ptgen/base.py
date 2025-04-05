from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any, Dict


class DataType(Enum):
    MOVIE = "Movie"
    TV_SERIES = "TV Series"
    GAME = "Game"

    @classmethod
    def from_str(cls, value: str) -> Optional['DataType']:
        value = value.lower().strip()
        if value in ["movie", "电影"]:
            return cls.MOVIE
        elif value in ["TVSeries", "tv series", "电视剧", "剧集"]:
            return cls.TV_SERIES
        return None

@dataclass
class PTGenData:
    """
    Common base class for all ptgen data,
    """
    site: str = "Unknown"
    sid: str = ""
    success: bool = False
    error: Optional[str] = None
    format: Optional[str] = None
    type_: Optional[DataType] = None

    def __str__(self) -> str:
        return f"{self.site} ({self.sid})"

    @property
    def subtitle(self) -> str:
        return ""

@dataclass
class Person:
    """Simple class for person-like fields (director, writer, actor)."""
    url: Optional[str] = None
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Person':
        return cls(
            url=data.get("url"),
            name=data.get("name")
        )
