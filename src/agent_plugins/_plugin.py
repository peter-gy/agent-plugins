"""Filesystem-backed Agent Plugin object."""

from __future__ import annotations

import os
from html import escape
from pathlib import Path, PurePosixPath, PureWindowsPath

from ._build.plan import build_plan
from ._errors import AgentPluginError
from ._files import FileInventory
from ._schema import Manifest, MCPConfig
from ._schema.skill import SkillDocument
from ._skill import Skill
from ._tree import DEFAULT_MAX_DEPTH, DEFAULT_MAX_FILES, render_tree

_KIND = "Agent Plugin"
_MANIFEST = "plugin.json"


class Plugin:
    """Expose an Agent Plugin through native paths and a tree display."""

    __slots__ = ("_inventory", "_manifest", "_mcp", "_skill_names", "_skills")

    _inventory: FileInventory
    _manifest: Manifest
    _mcp: MCPConfig | None
    _skill_names: tuple[str, ...]
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
    def from_project(
        cls,
        project: str | os.PathLike[str] = ".",
    ) -> Plugin:
        """Return the Agent Plugin selected by a Python project's build plan."""
        plan = build_plan(Path(project))
        inventory = FileInventory.select(
            plan.root,
            (mapping.target for mapping in plan.files),
            kind=_KIND,
            required=_MANIFEST,
        )
        return cls._from_inventory(inventory)

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

    def skill(self, name: str) -> Skill:
        """Return the immediate Agent Skill stored in directory `name`."""
        if (
            not name
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
            or PureWindowsPath(name).drive
        ):
            raise AgentPluginError(f"Invalid Agent Skill directory name: {name!r}")

        matches = tuple(
            skill
            for skill_name, skill in zip(self._skill_names, self._skills, strict=True)
            if skill_name == name
        )
        available = tuple(
            sorted(
                self._skill_names,
                key=lambda value: (value.casefold(), value),
            )
        )
        if not matches:
            choices = ", ".join(available) if available else "none"
            raise AgentPluginError(
                f"Agent Skill {name!r} is unavailable. Available skills: {choices}"
            )
        return matches[0]

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
    manifest = Manifest._from_inventory(inventory)
    mcp = (
        MCPConfig._from_inventory(inventory.root / "mcp.json", manifest, inventory)
        if PurePosixPath("mcp.json") in inventory.names
        else None
    )
    plugin._manifest = manifest
    plugin._mcp = mcp
    entries = _skills(inventory)
    plugin._skill_names = tuple(name for name, _skill in entries)
    plugin._skills = tuple(skill for _name, skill in entries)


def _skills(inventory: FileInventory) -> tuple[tuple[str, Skill], ...]:
    skill_roots = (
        relative.parent
        for relative in inventory.names
        if len(relative.parts) == 3
        and relative.parts[0] == "skills"
        and relative.name == "SKILL.md"
    )
    return tuple(
        (
            skill_root.name,
            Skill._from_inventory(
                inventory.subtree(skill_root),
                document=SkillDocument(inventory, (skill_root / "SKILL.md").as_posix()),
            ),
        )
        for skill_root in skill_roots
    )
