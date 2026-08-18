"""Lazy, file-backed Agent Skill document."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import ValidationError, ValidationIssue
from .lazy import LazyResult


@dataclass(frozen=True, slots=True)
class _SkillData:
    frontmatter: str
    body: str


class SkillDocument:
    """Expose the two source sections in `SKILL.md`."""

    __slots__ = ("_path", "_result")

    def __init__(self, path: Path) -> None:
        self._path = path
        self._result = LazyResult(lambda: _load(path))

    @property
    def frontmatter(self) -> str:
        """Return text between the frontmatter delimiters."""
        return self._result.get().frontmatter

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
                frontmatter="".join(lines[1:index]),
                body="".join(lines[index + 1 :]),
            )
    raise _validation_error(path, "SKILL.md frontmatter must end with a --- delimiter")


def _line_value(line: str) -> str:
    return line.removesuffix("\n").removesuffix("\r")


def _validation_error(path: Path, message: str) -> ValidationError:
    return ValidationError(path, (ValidationIssue(location=(), message=message),))
