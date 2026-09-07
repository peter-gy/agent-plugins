"""Resolve MCP stdio declarations into subprocess inputs."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from posixpath import normpath

from ._errors import AgentPluginError
from ._files import FileInventory
from ._schema.models import MCPServer, ResolvedStdioServer, StdioServer

_PLACEHOLDER = re.compile(r"\$\{PLUGIN_(ROOT|DATA)\}")


def resolve_stdio(
    servers: Mapping[str, MCPServer],
    name: str,
    *,
    root: Path,
    inventory: FileInventory | None,
    data_dir: str | os.PathLike[str],
    base_env: Mapping[str, str] | None,
) -> ResolvedStdioServer:
    """Resolve a stdio server against current filesystem and environment state."""
    server = servers.get(name)
    if server is None:
        available = ", ".join(
            sorted(servers, key=lambda value: (value.casefold(), value))
        )
        raise AgentPluginError(
            f"MCP server {name!r} is unavailable. "
            f"Available servers: {available or 'none'}"
        )
    if not isinstance(server, StdioServer):
        raise AgentPluginError(f"MCP server {name!r} uses {server.type!r}, not 'stdio'")

    plugin_root = _plugin_directory(root)
    data_root = _directory(data_dir, label="Plugin data directory")
    roots = {"ROOT": str(plugin_root), "DATA": str(data_root)}
    command = (
        str(_plugin_file(plugin_root, server.command, inventory))
        if server.command.startswith("./")
        else server.command
    )
    args = tuple(_expand(value, roots) for value in server.args)

    environment = dict(base_env or {})
    for key, value in server.env.items():
        _set_environment(environment, key, _expand(value, roots))
    _set_environment(environment, "PLUGIN_ROOT", str(plugin_root))
    _set_environment(environment, "PLUGIN_DATA", str(data_root))

    cwd = _working_directory(
        server.cwd,
        plugin_root,
        data_root,
        roots,
        inventory,
    )
    return ResolvedStdioServer(
        command=command,
        args=args,
        env=environment,
        cwd=cwd,
    )


def _expand(value: str, roots: Mapping[str, str]) -> str:
    return _PLACEHOLDER.sub(lambda match: roots[match.group(1)], value)


def _directory(path: str | os.PathLike[str], *, label: str) -> Path:
    candidate = Path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise AgentPluginError(f"{label} cannot be resolved: {candidate}") from error
    if not resolved.is_dir():
        raise AgentPluginError(f"{label} is not a directory: {resolved}")
    return resolved


def _plugin_directory(root: Path) -> Path:
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise AgentPluginError(f"Plugin root cannot be resolved: {root}") from error
    if resolved != root or not root.is_dir():
        raise AgentPluginError(f"Plugin root changed after construction: {root}")
    return root


def _plugin_file(
    root: Path,
    command: str,
    inventory: FileInventory | None,
) -> Path:
    relative = PurePosixPath(command.removeprefix("./").replace("\\", "/"))
    if inventory is not None:
        try:
            candidate = root.joinpath(*relative.parts)
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
            selected_name = _selected_name(root, candidate, resolved)
            selected = inventory.file(selected_name, kind="Agent Plugin")
            if selected.resolve(strict=True) != resolved:
                raise AgentPluginError("Command changed during selected-file lookup")
        except (AgentPluginError, OSError, RuntimeError, ValueError) as error:
            raise AgentPluginError(
                f"MCP stdio command is unavailable in the selected plugin: {command}"
            ) from error
        if not resolved.is_file():
            raise AgentPluginError(
                f"MCP stdio command is unavailable in the selected plugin: {command}"
            )
        return resolved
    candidate = root.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise AgentPluginError(
            f"MCP stdio command cannot be resolved inside the plugin root: {command}"
        ) from error
    if not resolved.is_file():
        raise AgentPluginError(f"MCP stdio command is not a regular file: {candidate}")
    return resolved


def _working_directory(
    value: str | None,
    plugin_root: Path,
    data_root: Path,
    roots: Mapping[str, str],
    inventory: FileInventory | None,
) -> Path:
    if value is None:
        return plugin_root
    expanded = _expand(value.replace("\\", "/"), roots)
    if value.startswith("./"):
        candidate = plugin_root / Path(expanded)
        root = plugin_root
        plugin_scoped = True
    elif value == "${PLUGIN_ROOT}" or value.startswith("${PLUGIN_ROOT}/"):
        candidate = Path(expanded)
        root = plugin_root
        plugin_scoped = True
    elif value == "${PLUGIN_DATA}" or value.startswith("${PLUGIN_DATA}/"):
        candidate = Path(expanded)
        root = data_root
        plugin_scoped = False
    else:
        raise AgentPluginError(f"Invalid MCP stdio working directory: {value}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        relative = (
            _selected_name(plugin_root, candidate, resolved)
            if inventory is not None and plugin_scoped
            else None
        )
    except (OSError, RuntimeError, ValueError) as error:
        raise AgentPluginError(
            f"MCP stdio working directory cannot be resolved inside {root}: {value}"
        ) from error
    if not resolved.is_dir():
        raise AgentPluginError(
            f"MCP stdio working directory is not a directory: {candidate}"
        )
    if (
        inventory is not None
        and relative is not None
        and not any(name.is_relative_to(relative) for name in inventory.names)
    ):
        raise AgentPluginError(
            "MCP stdio working directory is unavailable in the selected plugin: "
            f"{value}"
        )
    return resolved


def _selected_name(root: Path, candidate: Path, resolved: Path) -> PurePosixPath:
    relative = PurePosixPath(normpath(candidate.relative_to(root).as_posix()))
    if root.joinpath(*relative.parts).resolve(strict=False) != resolved:
        return PurePosixPath(resolved.relative_to(root).as_posix())
    return relative


def _set_environment(environment: dict[str, str], name: str, value: str) -> None:
    if os.name == "nt":
        normalized = name.upper()
        for existing in tuple(environment):
            if existing.upper() == normalized:
                del environment[existing]
    environment[name] = value
