"""Schema validation diagnostics and errors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .._errors import AgentPluginError


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Describe one invalid or ignored value in a plugin document."""

    location: tuple[str | int, ...]
    message: str


class ValidationError(AgentPluginError):
    """A plugin document could not be validated."""

    def __init__(self, path: Path, issues: tuple[ValidationIssue, ...]) -> None:
        if not issues:
            raise ValueError("ValidationError requires at least one issue")
        self.path = path
        self.issues = issues
        issue = issues[0]
        location = _format_location(issue.location)
        super().__init__(f"{path}: {location}: {issue.message}")


def _format_location(location: tuple[str | int, ...]) -> str:
    if not location:
        return "$"
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in location
    )
