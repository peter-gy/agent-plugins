"""Filesystem-backed Agent Skill object."""

from __future__ import annotations

import os
from html import escape
from pathlib import Path

from ._files import FileInventory
from ._schema.skill import SkillDocument
from ._tree import DEFAULT_MAX_DEPTH, DEFAULT_MAX_FILES, render_tree

_KIND = "Agent Skill"
_INSTRUCTIONS = "SKILL.md"


class Skill:
    """Expose an Agent Skill directory through native paths and source text."""

    __slots__ = ("_document", "_inventory")

    _inventory: FileInventory
    _document: SkillDocument

    def __init__(self, path: str | os.PathLike[str]) -> None:
        """Create a skill from a directory containing `SKILL.md`."""
        inventory = FileInventory.discover(
            path,
            kind=_KIND,
            required=_INSTRUCTIONS,
        )
        _set_state(self, inventory)

    @classmethod
    def _from_inventory(cls, inventory: FileInventory) -> Skill:
        skill = object.__new__(cls)
        _set_state(skill, inventory)
        return skill

    @property
    def path(self) -> Path:
        """Return the absolute skill root."""
        return self._inventory.root

    @property
    def files(self) -> tuple[Path, ...]:
        """Return the absolute paths selected for this skill."""
        return self._inventory.paths()

    @property
    def frontmatter(self) -> str:
        """Return the raw text between the `SKILL.md` frontmatter delimiters."""
        return self._document.frontmatter

    @property
    def body(self) -> str:
        """Return the raw Markdown text after the frontmatter."""
        return self._document.body

    def tree(
        self,
        *,
        max_depth: int | None = DEFAULT_MAX_DEPTH,
        max_files: int | None = DEFAULT_MAX_FILES,
    ) -> str:
        """Return a deterministic ASCII tree of the skill files.

        Args:
            max_depth: Deepest directory level to expand. `None` expands the
                complete tree.
            max_files: Maximum files to display. `None` includes every file.

        Raises:
            ValueError: A limit is negative.
        """
        return render_tree(
            self.path,
            self._inventory.names,
            max_depth=max_depth,
            max_files=max_files,
        )

    def __truediv__(self, child: str | os.PathLike[str]) -> Path:
        """Return a native path below the skill root."""
        return self.path / child

    def __fspath__(self) -> str:
        """Return the skill root for native filesystem APIs."""
        return str(self.path)

    def __str__(self) -> str:
        """Return the default skill tree."""
        return self.tree()

    def __repr__(self) -> str:
        """Return the default skill tree."""
        return self.tree()

    def _repr_html_(self) -> str:
        """Return a preformatted skill tree for notebook displays."""
        return f"<pre>{escape(self.tree())}</pre>"

    def __eq__(self, other: object) -> bool:
        """Return whether two skill handles select the same files."""
        return type(other) is type(self) and other._inventory == self._inventory

    def __hash__(self) -> int:
        """Return a hash of the selected skill files."""
        return hash(self._inventory)


def _set_state(
    skill: Skill,
    inventory: FileInventory,
) -> None:
    skill._inventory = inventory
    skill._document = SkillDocument(inventory.root / _INSTRUCTIONS)
