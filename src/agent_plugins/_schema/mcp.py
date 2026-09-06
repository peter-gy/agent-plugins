"""Lazy, file-backed Agent Plugins MCP configuration model."""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import cast

from .._errors import AgentPluginError
from .._files import FileInventory
from .errors import ValidationIssue
from .json import read_json, resolve_file, validation_error
from .lazy import LazyResult
from .manifest import Manifest
from .models import MCPData, MCPServer, ResolvedStdioServer, StdioServer
from .v1 import MCP_SCHEMA_1_0_0, PLUGIN_SCHEMA_1_0_0
from .v1.mcp import load_mcp_v1

_MCPLoader = Callable[
    [Path, dict[str, object], Path],
    tuple[dict[str, MCPServer], tuple[ValidationIssue, ...]],
]
_MCP_LOADERS: Mapping[str, tuple[str, _MCPLoader]] = MappingProxyType(
    {MCP_SCHEMA_1_0_0: (PLUGIN_SCHEMA_1_0_0, load_mcp_v1)}
)
_PLACEHOLDER = re.compile(r"\$\{PLUGIN_(ROOT|DATA)\}")


class MCPConfig:
    """Expose a lazily validated `mcp.json` document."""

    __slots__ = ("_inventory", "_path", "_result", "_root")

    def __init__(
        self,
        path: str | os.PathLike[str],
        manifest: Manifest,
    ) -> None:
        resolved = resolve_file(path)
        root = manifest.path.parent
        self._path = resolved
        self._root = root
        self._inventory: FileInventory | None = None
        self._result = LazyResult(lambda: _load_mcp(resolved, manifest, root))

    @classmethod
    def _from_inventory(
        cls,
        path: str | os.PathLike[str],
        manifest: Manifest,
        inventory: FileInventory,
    ) -> MCPConfig:
        config = cls(path, manifest)
        config._inventory = inventory
        return config

    @property
    def path(self) -> Path:
        """Return the absolute MCP configuration path."""
        return self._path

    @property
    def schema(self) -> str:
        """Return the canonical Agent Plugins MCP schema identifier."""
        return self._data.schema

    @property
    def servers(self) -> Mapping[str, MCPServer]:
        """Return valid MCP server configurations keyed by server name."""
        return self._data.servers

    @property
    def issues(self) -> tuple[ValidationIssue, ...]:
        """Return issues for MCP servers skipped during validation."""
        return self._data.issues

    def resolve_stdio(
        self,
        name: str,
        *,
        data_dir: str | os.PathLike[str],
        base_env: Mapping[str, str] | None = None,
    ) -> ResolvedStdioServer:
        """Resolve one stdio server into subprocess inputs."""
        servers = self.servers
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
            raise AgentPluginError(
                f"MCP server {name!r} uses {server.type!r}, not 'stdio'"
            )

        plugin_root = _plugin_directory(self._root)
        data_root = _directory(data_dir, label="Plugin data directory")
        roots = {"ROOT": str(plugin_root), "DATA": str(data_root)}
        command = (
            str(_plugin_file(plugin_root, server.command, self._inventory))
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
            self._inventory,
        )
        return ResolvedStdioServer(
            command=command,
            args=args,
            env=environment,
            cwd=cwd,
        )

    @property
    def _data(self) -> MCPData:
        return self._result.get()

    def __fspath__(self) -> str:
        """Return the MCP configuration path for native filesystem APIs."""
        return str(self.path)

    def __str__(self) -> str:
        """Return the MCP configuration path."""
        return str(self.path)

    def __repr__(self) -> str:
        """Return a path-oriented representation without loading the configuration."""
        return f"MCPConfig(path={self.path!r})"


def _load_mcp(path: Path, manifest: Manifest, root: Path) -> MCPData:
    manifest_schema = manifest.schema
    value = read_json(path)
    if not isinstance(value, dict):
        raise validation_error(path, (), "Expected an object")
    schema = value.get("$schema")
    if not isinstance(schema, str):
        raise validation_error(path, ("$schema",), "Unsupported or missing MCP schema")
    configured = _MCP_LOADERS.get(schema)
    if configured is None:
        raise validation_error(path, ("$schema",), "Unsupported or missing MCP schema")
    expected_manifest_schema, loader = configured
    if manifest_schema != expected_manifest_schema:
        raise validation_error(
            path, ("$schema",), "MCP schema version does not match the manifest"
        )
    servers, issues = loader(path, cast(dict[str, object], value), root)
    return MCPData(
        schema=schema,
        servers=MappingProxyType(servers),
        issues=issues,
    )


def _expand(value: str, roots: Mapping[str, str]) -> str:
    return _PLACEHOLDER.sub(lambda match: roots[match.group(1)], value)


def _directory(path: str | os.PathLike[str], *, label: str) -> Path:
    candidate = Path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AgentPluginError(f"{label} cannot be resolved: {candidate}") from error
    if not resolved.is_dir():
        raise AgentPluginError(f"{label} is not a directory: {resolved}")
    return resolved


def _plugin_directory(root: Path) -> Path:
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
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
            candidate = inventory.file(relative, kind="Agent Plugin")
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
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
    except (OSError, RuntimeError, ValueError) as error:
        raise AgentPluginError(
            f"MCP stdio working directory cannot be resolved inside {root}: {value}"
        ) from error
    if not resolved.is_dir():
        raise AgentPluginError(
            f"MCP stdio working directory is not a directory: {candidate}"
        )
    if inventory is not None and plugin_scoped:
        relative = PurePosixPath(resolved.relative_to(plugin_root).as_posix())
        if not any(name.is_relative_to(relative) for name in inventory.names):
            raise AgentPluginError(
                "MCP stdio working directory is unavailable in the selected plugin: "
                f"{value}"
            )
    return resolved


def _set_environment(environment: dict[str, str], name: str, value: str) -> None:
    if os.name == "nt":
        normalized = name.upper()
        for existing in tuple(environment):
            if existing.upper() == normalized:
                del environment[existing]
    environment[name] = value
