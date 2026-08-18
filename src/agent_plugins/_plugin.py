"""Filesystem-backed Agent Plugin object."""

from __future__ import annotations

import os
from html import escape
from pathlib import Path, PurePosixPath

from ._files import FileInventory
from ._schema import Manifest, MCPConfig
from ._skill import Skill
from ._tree import DEFAULT_MAX_DEPTH, DEFAULT_MAX_FILES, render_tree

_KIND = "Agent Plugin"
_MANIFEST = "plugin.json"


class Plugin:
    """Expose an Agent Plugin through native paths and a tree display."""

    __slots__ = ("_inventory", "_manifest", "_mcp", "_skills")

    _inventory: FileInventory
    _manifest: Manifest
    _mcp: MCPConfig | None
    _skills: tuple[Skill, ...]

    def __init__(self, path: str | os.PathLike[str]) -> None:
        """Create a plugin from a directory containing `plugin.json`."""
        inventory = FileInventory.discover(
            path,
            kind=_KIND,
            required=_MANIFEST,
        )
        _set_state(self, inventory)

    @classmethod
    def _from_inventory(cls, inventory: FileInventory) -> Plugin:
        plugin = object.__new__(cls)
        _set_state(plugin, inventory)
        return plugin

    @property
    def path(self) -> Path:
        """Return the absolute plugin root."""
        return self._inventory.root

    @property
    def manifest(self) -> Manifest:
        """Return the lazy plugin manifest model."""
        return self._manifest

    @property
    def files(self) -> tuple[Path, ...]:
        """Return the absolute paths selected for this plugin."""
        return self._inventory.paths()

    @property
    def skills(self) -> tuple[Skill, ...]:
        """Return each immediate Agent Skill in the plugin."""
        return self._skills

    @property
    def mcp(self) -> MCPConfig | None:
        """Return the lazy MCP configuration model when present."""
        return self._mcp

    def tree(
        self,
        *,
        max_depth: int | None = DEFAULT_MAX_DEPTH,
        max_files: int | None = DEFAULT_MAX_FILES,
    ) -> str:
        """Return a deterministic ASCII tree of the plugin files.

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

    def __fspath__(self) -> str:
        """Return the plugin root for native filesystem APIs."""
        return str(self.path)

    def __str__(self) -> str:
        """Return the default plugin tree."""
        return self.tree()

    def __repr__(self) -> str:
        """Return the default plugin tree."""
        return self.tree()

    def _repr_html_(self) -> str:
        """Return a preformatted plugin tree for notebook displays."""
        return f"<pre>{escape(self.tree())}</pre>"

    def __eq__(self, other: object) -> bool:
        """Return whether two plugin handles select the same files."""
        return type(other) is type(self) and other._inventory == self._inventory

    def __hash__(self) -> int:
        """Return a hash of the selected plugin files."""
        return hash(self._inventory)


def _set_state(
    plugin: Plugin,
    inventory: FileInventory,
) -> None:
    plugin._inventory = inventory
    manifest = Manifest(inventory.root / "plugin.json")
    mcp = (
        MCPConfig(inventory.root / "mcp.json", manifest)
        if PurePosixPath("mcp.json") in inventory.names
        else None
    )
    plugin._manifest = manifest
    plugin._mcp = mcp
    plugin._skills = _skills(inventory)


def _skills(inventory: FileInventory) -> tuple[Skill, ...]:
    skill_roots = (
        relative.parent
        for relative in inventory.names
        if len(relative.parts) == 3
        and relative.parts[0] == "skills"
        and relative.name == "SKILL.md"
    )
    return tuple(
        Skill._from_inventory(inventory.subtree(skill_root))
        for skill_root in skill_roots
    )
