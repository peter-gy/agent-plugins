"""Declarative Agent Plugin file planning."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .._errors import AgentPluginError

STAGED_ROOT = ".agent-plugin"


@dataclass(frozen=True, slots=True)
class FileMapping:
    """Map one source file to its path inside the plugin root."""

    source: Path
    target: PurePosixPath


@dataclass(frozen=True, slots=True)
class BuildPlan:
    """Describe the files carried from a project into its Agent Plugin."""

    project: Path
    root: Path
    files: tuple[FileMapping, ...]


def build_plan(project: str | Path = ".") -> BuildPlan:
    """Load project configuration and return its complete plugin file plan."""
    project_path = Path(project).resolve()
    pyproject = project_path / "pyproject.toml"
    if not project_path.is_dir() or not pyproject.is_file():
        raise AgentPluginError(f"Project has no pyproject.toml: {project_path}")

    try:
        document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise AgentPluginError(
            f"Cannot read project configuration: {pyproject}"
        ) from error

    config = _config(document, pyproject)
    root_value = config.get("root")
    if not isinstance(root_value, str) or not root_value:
        raise AgentPluginError(
            f"[tool.agent-plugins].root must be a non-empty path in {pyproject}"
        )
    include = _include(config.get("include"), pyproject)

    staged = project_path / STAGED_ROOT
    configured = project_path / root_value
    source_root = staged if (staged / "plugin.json").is_file() else configured
    try:
        root = source_root.resolve(strict=True)
    except OSError as error:
        raise AgentPluginError(
            f"Agent Plugin root cannot be resolved: {source_root}"
        ) from error
    if not root.is_dir():
        raise AgentPluginError(f"Agent Plugin root is not a directory: {root}")

    files: dict[PurePosixPath, Path] = {}
    _add_file(files, root, root / "plugin.json", required=True)
    _add_tree(files, root, root / "skills")
    _add_file(files, root, root / "mcp.json", required=False)
    for pattern in include:
        _add_pattern(files, root, pattern)

    mappings = tuple(
        FileMapping(source=source, target=target)
        for target, source in sorted(files.items(), key=lambda item: item[0].as_posix())
    )
    return BuildPlan(project=project_path, root=root, files=mappings)


def _config(document: dict[str, object], pyproject: Path) -> dict[str, object]:
    tool = document.get("tool")
    if not isinstance(tool, dict):
        raise AgentPluginError(f"Missing [tool.agent-plugins] in {pyproject}")
    config = tool.get("agent-plugins")
    if not isinstance(config, dict):
        raise AgentPluginError(f"Missing [tool.agent-plugins] in {pyproject}")
    return cast(dict[str, object], config)


def _include(value: object, pyproject: Path) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(
        isinstance(pattern, str) and pattern for pattern in value
    ):
        raise AgentPluginError(
            f"[tool.agent-plugins].include must be a list of paths in {pyproject}"
        )
    return tuple(cast(list[str], value))


def _add_pattern(files: dict[PurePosixPath, Path], root: Path, pattern: str) -> None:
    portable = PurePosixPath(pattern)
    if portable.is_absolute() or ".." in portable.parts or "\\" in pattern:
        raise AgentPluginError(
            f"Include pattern must stay within the plugin root: {pattern}"
        )
    try:
        matches = tuple(root.glob(pattern))
    except ValueError as error:
        raise AgentPluginError(f"Invalid include pattern: {pattern}") from error
    if not matches:
        raise AgentPluginError(f"Include pattern matched no files: {pattern}")
    for match in matches:
        if match.is_dir():
            _add_tree(files, root, match)
        elif match.is_file():
            _add_file(files, root, match, required=True)


def _add_tree(files: dict[PurePosixPath, Path], root: Path, directory: Path) -> None:
    if not directory.exists():
        return
    if not directory.is_dir():
        raise AgentPluginError(f"Expected a directory: {directory}")
    for candidate in directory.rglob("*"):
        if candidate.is_symlink() and candidate.is_dir():
            raise AgentPluginError(
                f"Directory symlinks cannot be packaged: {candidate}"
            )
        if candidate.is_file():
            _add_file(files, root, candidate, required=True)


def _add_file(
    files: dict[PurePosixPath, Path],
    root: Path,
    candidate: Path,
    *,
    required: bool,
) -> None:
    if not candidate.exists() and not required:
        return
    if not candidate.is_file():
        raise AgentPluginError(f"Expected a file: {candidate}")
    try:
        source = candidate.resolve(strict=True)
        source.relative_to(root)
    except (OSError, ValueError) as error:
        raise AgentPluginError(f"Plugin file escapes its root: {candidate}") from error
    target = PurePosixPath(candidate.relative_to(root).as_posix())
    files[target] = source
