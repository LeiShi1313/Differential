from pathlib import Path
from typing import List

from differential.utils.rename.models import RenameOperation, RenamePlan
from differential.utils.rename.plan import validate_plan


def apply_plan(plan: RenamePlan) -> List[RenameOperation]:
    validate_plan(plan)
    applied: List[RenameOperation] = []
    for operation in _apply_order(plan.operations):
        Path(operation.source).rename(operation.target)
        applied.append(operation)
    return applied


def _apply_order(operations: List[RenameOperation]) -> List[RenameOperation]:
    files = [operation for operation in operations if operation.kind != "folder"]
    folders = [operation for operation in operations if operation.kind == "folder"]
    files.sort(key=lambda operation: len(Path(operation.source).parts), reverse=True)
    folders.sort(key=lambda operation: len(Path(operation.source).parts), reverse=True)
    return files + folders
