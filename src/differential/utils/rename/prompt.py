from typing import Callable, Iterable, List

from differential.utils.rename.models import RenamePlan


def choose_optional(
    label: str,
    suggestions: Iterable[str],
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> str:
    choices = [value for value in suggestions if value]
    if choices:
        output_func(f"{label} suggestions:")
        for index, value in enumerate(choices, start=1):
            output_func(f"  {index}. {value}")
        prompt = f"Select {label} [1-{len(choices)}], enter custom value, or leave blank: "
    else:
        prompt = f"Enter {label} or leave blank: "

    value = input_func(prompt).strip()
    if not value:
        return ""
    if value.isdigit():
        index = int(value)
        if 1 <= index <= len(choices):
            return choices[index - 1]
    return value


def print_plan(plan: RenamePlan, output_func: Callable[[str], None] = print) -> None:
    if plan.warnings:
        output_func("Warnings:")
        for warning in plan.warnings:
            output_func(f"  - {warning}")
        output_func("")
    output_func("Rename plan:")
    if not plan.operations:
        output_func("  No changes.")
        return
    for operation in plan.operations:
        output_func(f"  {operation.source} -> {operation.target}")


def confirm_apply(
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> bool:
    value = input_func("Apply these renames? [y/N]: ").strip().lower()
    return value in {"y", "yes"}
