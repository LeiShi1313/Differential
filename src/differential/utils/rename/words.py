import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class WordRule:
    pattern: str
    is_regex: bool = False


@dataclass(frozen=True)
class ReplacementRule:
    pattern: str
    replacement: str
    is_regex: bool = False


@dataclass(frozen=True)
class RenameWords:
    block: Tuple[WordRule, ...] = ()
    replace: Tuple[ReplacementRule, ...] = ()
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class WordApplication:
    original_name: str
    name: str
    applied: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    blocked: bool = False
    blocked_by: str = ""


def apply_rename_words(path_or_name, words: RenameWords) -> WordApplication:
    original_name = _name_from_path(path_or_name)
    warnings = list(words.warnings)

    for rule in words.block:
        matched, warning = _matches(rule, original_name, "block")
        if warning:
            warnings.append(warning)
            continue
        if matched:
            return WordApplication(
                original_name=original_name,
                name=original_name,
                applied=(f"block:{rule.pattern}",),
                warnings=tuple(warnings),
                blocked=True,
                blocked_by=rule.pattern,
            )

    name = original_name
    applied = []
    for rule in words.replace:
        updated, changed, warning = _replace(rule, name)
        if warning:
            warnings.append(warning)
            continue
        if changed:
            name = updated
            applied.append(f"replace:{rule.pattern}")

    return WordApplication(
        original_name=original_name,
        name=name,
        applied=tuple(applied),
        warnings=tuple(warnings),
    )


def _matches(rule: WordRule, name: str, label: str) -> Tuple[bool, str]:
    if rule.is_regex:
        try:
            return bool(re.search(rule.pattern, name, flags=re.IGNORECASE)), ""
        except re.error:
            return False, f"invalid {label} regex ignored: {rule.pattern}"
    return rule.pattern.lower() in name.lower(), ""


def _replace(rule: ReplacementRule, name: str) -> Tuple[str, bool, str]:
    if rule.is_regex:
        try:
            updated = re.sub(rule.pattern, rule.replacement, name, flags=re.IGNORECASE)
        except re.error:
            return name, False, f"invalid replace regex ignored: {rule.pattern}"
    else:
        updated = re.sub(re.escape(rule.pattern), rule.replacement, name, flags=re.IGNORECASE)
    return updated, updated != name, ""


def _name_from_path(path_or_name) -> str:
    if isinstance(path_or_name, Path):
        return path_or_name.name
    text = str(path_or_name or "").strip().replace("\\", "/").rstrip("/")
    return text.rsplit("/", 1)[-1] if "/" in text else text
