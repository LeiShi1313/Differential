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

    # staff: e.g. ["导演: XXX", "脚本: YYY", ...]
    staff: List[str] = field(default_factory=list)
    # info: e.g. ["中文名: XXX", "别名: YYY", ...]
    info: List[str] = field(default_factory=list)

    bangumi_votes: Optional[str] = None
    bangumi_rating_average: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    cast: List[str] = field(default_factory=list)

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

        bangumi.alt = obj.get('alt')
        bangumi.cover = obj.get('cover')
        bangumi.poster = obj.get('poster')
        bangumi.story = obj.get('story')

        # Staff & Info
        bangumi.staff = obj.get('staff', [])
        bangumi.info = obj.get('info', [])

        # Ratings
        bangumi.bangumi_votes = obj.get('bangumi_votes')
        bangumi.bangumi_rating_average = obj.get('bangumi_rating_average')

        # Tags & Cast
        bangumi.tags = obj.get('tags', [])
        bangumi.cast = obj.get('cast', [])

        return bangumi

    def __str__(self) -> str:
        # Extract Chinese name from info if available
        for info_item in self.info:
            if info_item.startswith('中文名:'):
                return info_item.split(':', 1)[1].strip()
        
        # Fallback to alt if available
        if self.alt:
            return self.alt
            
        return super().__str__()