from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

from differential.utils.ptgen.base import PTGenData, Person, DataType

AREA_MAP = {
            "中国大陆": "CN",
            "中国香港": "HK",
            "中国台湾": "TW",
            "美国": "US",
            "日本": "JP",
            "韩国": "KR",
            "印度": "IN",
            "法国": "FR",
            "意大利": "IT",
            "德国": "GE",
            "西班牙": "ES",
            "葡萄牙": "PT",
        }

@dataclass
class DoubanData(PTGenData):
    imdb_id: Optional[str] = None
    imdb_link: Optional[str] = None
    imdb_rating_average: Optional[float] = None
    imdb_votes: Optional[int] = None
    imdb_rating: Optional[str] = None

    chinese_title: Optional[str] = None
    foreign_title: Optional[str] = None
    aka: List[str] = field(default_factory=list)
    trans_title: List[str] = field(default_factory=list)
    this_title: List[str] = field(default_factory=list)

    year: Optional[str] = None
    region: List[str] = field(default_factory=list)
    genre: List[str] = field(default_factory=list)
    language: List[str] = field(default_factory=list)
    episodes: Optional[str] = None
    duration: Optional[str] = None

    introduction: Optional[str] = None
    douban_rating_average: Optional[float] = None
    douban_votes: Optional[int] = None
    douban_rating: Optional[str] = None
    poster: Optional[str] = None

    director: List[Person] = field(default_factory=list)
    writer: List[Person] = field(default_factory=list)
    cast: List[Person] = field(default_factory=list)

    tags: List[str] = field(default_factory=list)
    awards: Optional[str] = None

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'DoubanData':
        base = PTGenData(
            site=obj['site'],
            sid=obj['sid'],
            success=obj.get('success', False),
            error=obj.get('error'),
            format=obj.get('format'),
            type_=DataType.TV_SERIES if obj.get('episodes', '').isdigit() else DataType.MOVIE
        )
        douban = DoubanData(**base.__dict__)

        douban.imdb_id = obj.get('imdb_id')
        douban.imdb_link = obj.get('imdb_link')
        douban.imdb_rating_average = obj.get('imdb_rating_average')
        douban.imdb_votes = obj.get('imdb_votes')
        douban.imdb_rating = obj.get('imdb_rating')

        douban.chinese_title = obj.get('chinese_title')
        douban.foreign_title = obj.get('foreign_title')
        douban.aka = obj.get('aka', [])
        douban.trans_title = obj.get('trans_title', [])
        douban.this_title = obj.get('this_title', [])

        douban.year = obj.get('year')
        douban.region = obj.get('region', [])
        douban.genre = obj.get('genre', [])
        douban.language = obj.get('language', [])
        douban.episodes = obj.get('episodes')
        douban.duration = obj.get('duration')
        douban.introduction = obj.get('introduction')
        douban.douban_rating_average = obj.get('douban_rating_average')
        douban.douban_votes = obj.get('douban_votes')
        douban.douban_rating = obj.get('douban_rating')
        douban.poster = obj.get('poster')

        if 'director' in obj and isinstance(obj['director'], list):
            douban.director = [Person.from_dict(p) for p in obj['director']]
        if 'writer' in obj and isinstance(obj['writer'], list):
            douban.writer = [Person.from_dict(p) for p in obj['writer']]
        if 'cast' in obj and isinstance(obj['cast'], list):
            douban.cast = [Person.from_dict(p) for p in obj['cast']]

        douban.tags = obj.get('tags', [])
        douban.awards = obj.get('awards')

        return douban

    def __str__(self) -> str:
        if self.chinese_title:
            return self.chinese_title
        elif self.this_title:
            return self.this_title[0]
        elif self.trans_title:
            return self.trans_title[0]
        return super().__str__()

    @property
    def subtitle(self):
        if self.chinese_title:
            subtitle = f"{'/'.join([self.chinese_title] + self.aka)}"
        else:
            subtitle = f"{'/'.join(self.aka)}"
        if self.director:
            subtitle += (
                f"【导演：{'/'.join([d.name for d in self.director])}】"
            )
        if self.writer:
            subtitle += (
                f"【编剧：{'/'.join([w.name for w in self.writer])}】"
            )
        if self.cast:
            subtitle += (
                f"【主演：{'/'.join([c.name for c in self.cast[:3]])}】"
            )
        return subtitle

    @property
    def area(self):
        for area in AREA_MAP.keys():
            if area in self.region:
                return AREA_MAP[area]
        return ""