from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from differential.utils.rename.release_tokens import (
    find_editions,
    find_hdr_values,
    find_release_types,
    find_sources,
    find_uploaders,
)


@dataclass
class TokenSuggestions:
    sources: List[str] = field(default_factory=list)
    uploaders: List[str] = field(default_factory=list)
    release_types: List[str] = field(default_factory=list)
    editions: List[str] = field(default_factory=list)
    hdr: List[str] = field(default_factory=list)


def suggest_tokens(path_or_name) -> TokenSuggestions:
    name = Path(path_or_name).name if isinstance(path_or_name, Path) else str(path_or_name or "")
    return TokenSuggestions(
        sources=find_sources(name),
        uploaders=find_uploaders(name),
        release_types=find_release_types(name),
        editions=find_editions(name),
        hdr=find_hdr_values(name),
    )
