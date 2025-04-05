from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

from differential.utils.ptgen.base import PTGenData, DataType

@dataclass
class SteamData(PTGenData):
    """ Dataclass for data returned from steam.js """
    steam_id: Optional[str] = None
    poster: Optional[str] = None
    name: Optional[str] = None
    detail: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    review: List[str] = field(default_factory=list)
    linkbar: Optional[str] = None
    language: List[str] = field(default_factory=list)
    descr: Optional[str] = None
    screenshot: List[str] = field(default_factory=list)
    sysreq: List[str] = field(default_factory=list)
    name_chs: Optional[str] = None

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'SteamData':
        base = PTGenData(
            site=obj['site'],
            sid=obj['sid'],
            success=obj.get('success', False),
            error=obj.get('error'),
            format=obj.get('format'),
            type_=DataType.GAME
        )
        steam = SteamData(**base.__dict__)

        steam.steam_id = obj.get('steam_id')
        steam.poster = obj.get('poster')
        steam.name = obj.get('name')
        steam.detail = obj.get('detail')
        steam.tags = obj.get('tags', [])
        steam.review = obj.get('review', [])
        steam.linkbar = obj.get('linkbar')
        steam.language = obj.get('language', [])
        steam.descr = obj.get('descr')
        steam.screenshot = obj.get('screenshot', [])
        steam.sysreq = obj.get('sysreq', [])
        steam.name_chs = obj.get('name_chs')

        return steam

    def __str__(self) -> str:
        if self.name_chs:
            return self.name_chs
        elif self.name:
            return self.name
        return super().__str__()