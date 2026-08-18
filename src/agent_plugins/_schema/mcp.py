"""Lazy, file-backed Agent Plugins MCP configuration model."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import cast

from .errors import ValidationIssue
from .json import read_json, resolve_file, validation_error
from .lazy import LazyResult
from .manifest import Manifest
from .models import MCPData, MCPServer
from .v1 import MCP_SCHEMA_1_0_0, PLUGIN_SCHEMA_1_0_0
from .v1.mcp import load_mcp_v1

_MCPLoader = Callable[
    [Path, dict[str, object], Path],
    tuple[dict[str, MCPServer], tuple[ValidationIssue, ...]],
]
_MCP_LOADERS: Mapping[str, tuple[str, _MCPLoader]] = MappingProxyType(
    {MCP_SCHEMA_1_0_0: (PLUGIN_SCHEMA_1_0_0, load_mcp_v1)}
)


class MCPConfig:
    """Expose a lazily validated `mcp.json` document."""

    __slots__ = ("_path", "_result")

    def __init__(
        self,
        path: str | os.PathLike[str],
        manifest: Manifest,
    ) -> None:
        resolved = resolve_file(path)
        root = manifest.path.parent
        self._path = resolved
        self._result = LazyResult(lambda: _load_mcp(resolved, manifest, root))

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
