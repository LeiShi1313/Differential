from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

from differential.utils.ptgen.base import PTGenData, DataType

@dataclass
class IndienovaData(PTGenData):
    """
    Dataclass for data returned from indienova.js
    """
    cover: Optional[str] = None
    poster: Optional[str] = None
    chinese_title: Optional[str] = None
    another_title: Optional[str] = None
    english_title: Optional[str] = None
    release_date: Optional[str] = None
    links: Dict[str, str] = field(default_factory=dict)  # e.g., {'Steam': 'http://...', ...}
    intro: Optional[str] = None
    intro_detail: List[str] = field(default_factory=list)  # e.g., ['类型: 冒险/动作', '视角: 第一人称', ...]
    descr: Optional[str] = None  # Detailed description; fallback to intro if none
    rate: Optional[str] = None   # "评分" field
    dev: List[str] = field(default_factory=list)  # List of developers
    pub: List[str] = field(default_factory=list)  # List of publishers
    screenshot: List[str] = field(default_factory=list)  # List of screenshot URLs
    cat: List[str] = field(default_factory=list)  # Tags
    level: List[str] = field(default_factory=list) # Game ratings / ESRB images
    price: List[str] = field(default_factory=list) # Price info

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'IndienovaData':
        """
        Create an IndienovaData instance from a raw dictionary
        (typically from the JS function gen_indienova).
        """
        base = PTGenData(
            site=obj['site'],
            sid=obj['sid'],
            success=obj.get('success', False),
            error=obj.get('error'),
            format=obj.get('format'),
            type_=DataType.GAME
        )
        indienova = IndienovaData(**base.__dict__)

        indienova.cover = obj.get('cover')
        indienova.poster = obj.get('poster')
        indienova.chinese_title = obj.get('chinese_title')
        indienova.another_title = obj.get('another_title')
        indienova.english_title = obj.get('english_title')
        indienova.release_date = obj.get('release_date')
        indienova.links = obj.get('links', {})
        indienova.intro = obj.get('intro')
        indienova.intro_detail = obj.get('intro_detail', [])
        indienova.descr = obj.get('descr')
        indienova.rate = obj.get('rate')
        indienova.dev = obj.get('dev', [])
        indienova.pub = obj.get('pub', [])
        indienova.screenshot = obj.get('screenshot', [])
        indienova.cat = obj.get('cat', [])
        indienova.level = obj.get('level', [])
        indienova.price = obj.get('price', [])

        return indienova

    def __str__(self) -> str:
        if self.chinese_title:
            return self.chinese_title
        elif self.english_title:
            return self.english_title
        elif self.another_title:
            return self.another_title
        return super().__str__()
