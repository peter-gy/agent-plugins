"""Lazy, file-backed Agent Skill document."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .._files import FileInventory
from .errors import ValidationError, ValidationIssue
from .json import selected_file
from .lazy import LazyResult


@dataclass(frozen=True, slots=True)
class _SkillData:
    source: str
    frontmatter: str
    body: str


class SkillDocument:
    """Expose complete `SKILL.md` source and its two sections."""

    __slots__ = ("_path", "_result")

    def __init__(self, inventory: FileInventory, name: str = "SKILL.md") -> None:
        self._path = inventory.root / name
        self._result = LazyResult(lambda: _load(selected_file(inventory, name)))

    @property
    def frontmatter(self) -> str:
        """Return text between the frontmatter delimiters."""
        return self._result.get().frontmatter

    @property
    def source(self) -> str:
        """Return the complete `SKILL.md` source text."""
        return self._result.get().source

    @property
    def body(self) -> str:
        """Return Markdown text after the frontmatter."""
        return self._result.get().body


def _load(path: Path) -> _SkillData:
    try:
        with path.open(encoding="utf-8", newline="") as file:
            source = file.read()
    except UnicodeError as error:
        raise _validation_error(path, "SKILL.md must contain UTF-8 text") from error
    except OSError as error:
        raise _validation_error(path, "SKILL.md could not be read") from error

    lines = source.splitlines(keepends=True)
    if not lines or _line_value(lines[0]) != "---":
        raise _validation_error(
            path,
            "SKILL.md must begin with a --- frontmatter delimiter",
        )

    for index, line in enumerate(lines[1:], start=1):
        if _line_value(line) == "---":
            return _SkillData(
                source=source,
                frontmatter="".join(lines[1:index]),
                body="".join(lines[index + 1 :]),
            )
    raise _validation_error(path, "SKILL.md frontmatter must end with a --- delimiter")


def _line_value(line: str) -> str:
    return line.removesuffix("\n").removesuffix("\r")


def _validation_error(path: Path, message: str) -> ValidationError:
    return ValidationError(path, (ValidationIssue(location=(), message=message),))
