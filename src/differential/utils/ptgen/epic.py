from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

from differential.utils.ptgen.base import PTGenData, DataType

@dataclass
class EpicData(PTGenData):
    """ Dataclass for data returned from epic.js """
    name: Optional[str] = None
    epic_link: Optional[str] = None
    desc: Optional[str] = None
    poster: Optional[str] = None
    screenshot: List[str] = field(default_factory=list)
    language: List[str] = field(default_factory=list)

    # Typically: "min_req" / "max_req" = { 'Windows': ['OS: ...','CPU: ...'], ... }
    min_req: Dict[str, List[str]] = field(default_factory=dict)
    max_req: Dict[str, List[str]] = field(default_factory=dict)

    # Possibly a list of rating label image URLs
    level: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'EpicData':
        base = PTGenData(
            site=obj['site'],
            sid=obj['sid'],
            success=obj.get('success', False),
            error=obj.get('error'),
            format=obj.get('format'),
            type_=DataType.GAME
        )
        epic = EpicData(**base.__dict__)

        epic.name = obj.get('name')
        epic.epic_link = obj.get('epic_link')
        epic.desc = obj.get('desc')
        epic.poster = obj.get('poster')
        epic.screenshot = obj.get('screenshot', [])
        epic.language = obj.get('language', [])
        epic.min_req = obj.get('min_req', {})
        epic.max_req = obj.get('max_req', {})
        epic.level = obj.get('level', [])

        return epic

    def __str__(self) -> str:
        if self.name:
            return self.name
        return super().__str__()