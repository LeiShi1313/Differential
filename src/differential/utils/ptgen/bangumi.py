from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

from differential.utils.ptgen.base import PTGenData, DataType

@dataclass
class BangumiData(PTGenData):
    """
    Dataclass for data returned from bangumi.js
    """
    alt: Optional[str] = None
    cover: Optional[str] = None  # for backward compatibility
    poster: Optional[str] = None
    story: Optional[str] = None
    name: Optional[str] = None
    name_cn: Optional[str] = None
    date: Optional[str] = None
    eps: Optional[int] = None
    platform: Optional[str] = None

    # staff: e.g. ["导演: XXX", "脚本: YYY", ...]
    staff: List[Any] = field(default_factory=list)
    # info: e.g. ["中文名: XXX", "别名: YYY", ...]
    info: List[str] = field(default_factory=list)

    bangumi_votes: Optional[str] = None
    bangumi_rating_average: Optional[str] = None
    tags: List[Any] = field(default_factory=list)
    cast: List[Any] = field(default_factory=list)

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'BangumiData':
        """
        Create a BangumiData instance from a raw dictionary
        (e.g., from the JS code `gen_bangumi(sid)`).
        """
        base = PTGenData(
            site=obj['site'], 
            sid=obj['sid'],
            success=obj.get('success', False),
            error=obj.get('error'),
            format=obj.get('format')
        )

        bangumi = BangumiData(**base.__dict__)

        bangumi.alt = obj.get('alt') or (f"https://bgm.tv/subject/{obj.get('sid')}" if obj.get('sid') else None)
        bangumi.cover = obj.get('cover')
        bangumi.poster = obj.get('poster') or obj.get('cover')
        bangumi.story = obj.get('story')
        bangumi.name = obj.get('name')
        bangumi.name_cn = obj.get('name_cn')
        bangumi.date = obj.get('date')
        bangumi.eps = obj.get('eps')
        bangumi.platform = obj.get('platform')

        # Staff & Info
        bangumi.staff = obj.get('staff', [])
        bangumi.info = obj.get('info', [])
        if not bangumi.info:
            bangumi.info = [
                f"{key}: {value}"
                for key, value in (
                    ("中文名", bangumi.name_cn),
                    ("放送日期", bangumi.date),
                    ("话数", bangumi.eps),
                    ("平台", bangumi.platform),
                )
                if value
            ]

        # Ratings
        bangumi.bangumi_votes = obj.get('bangumi_votes')
        bangumi.bangumi_rating_average = obj.get('bangumi_rating_average')
        if isinstance(obj.get('rating'), dict):
            bangumi.bangumi_votes = obj['rating'].get('total')
            bangumi.bangumi_rating_average = obj['rating'].get('score')

        # Tags & Cast
        bangumi.tags = obj.get('tags', [])
        bangumi.cast = obj.get('cast', [])

        return bangumi

    def __str__(self) -> str:
        if self.name_cn:
            return self.name_cn
        if self.name:
            return self.name
        # Extract Chinese name from info if available
        for info_item in self.info:
            if info_item.startswith('中文名:'):
                return info_item.split(':', 1)[1].strip()
        
        # Fallback to alt if available
        if self.alt:
            return self.alt
            
        return super().__str__()
