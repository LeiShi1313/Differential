from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RenameMetadata:
    title: str
    year: Optional[str] = None
    kind: str = ""
    season: str = ""
    episode: str = ""


@dataclass
class TechnicalTokens:
    resolution: str = ""
    source: str = ""
    release_type: str = ""
    video_codec: str = ""
    hdr: str = ""
    audio_codec: str = ""
    edition: str = ""
    uploader: str = ""


@dataclass
class CodecTokenMap:
    video: Dict[str, str] = field(default_factory=dict)
    audio: Dict[str, str] = field(default_factory=dict)


@dataclass
class RenameOperation:
    source: Path
    target: Path
    kind: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "source": str(self.source),
            "target": str(self.target),
            "kind": self.kind,
        }


@dataclass
class RenamePlan:
    root: Path
    operations: List[RenameOperation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_bdmv: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": str(self.root),
            "is_bdmv": self.is_bdmv,
            "operations": [operation.to_dict() for operation in self.operations],
            "warnings": list(self.warnings),
        }
