"""Normalized values returned by Agent Plugin document validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar, Literal, TypeAlias

from .errors import ValidationIssue


@dataclass(frozen=True, slots=True)
class Author:
    """Author metadata from `plugin.json`."""

    name: str | None = None
    email: str | None = None
    url: str | None = None


@dataclass(frozen=True, slots=True)
class ManifestData:
    """Normalized values from a supported `plugin.json`."""

    schema: str
    name: str
    version: str | None
    description: str | None
    author: Author | None
    homepage: str | None
    repository: str | None
    license: str | None
    keywords: tuple[str, ...]
    extensions: Mapping[str, Mapping[str, object]]
    issues: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True)
class StdioServer:
    """Configuration for an MCP stdio server."""

    type: ClassVar[Literal["stdio"]] = "stdio"
    command: str
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    cwd: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))
        object.__setattr__(self, "env", MappingProxyType(dict(self.env)))


@dataclass(frozen=True, slots=True)
class StreamableHTTPServer:
    """Configuration for a Streamable HTTP MCP server."""

    type: ClassVar[Literal["streamable-http"]] = "streamable-http"
    url: str
    headers: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))


@dataclass(frozen=True, slots=True)
class SSEServer:
    """Configuration for a legacy HTTP+SSE MCP server."""

    type: ClassVar[Literal["sse"]] = "sse"
    url: str
    headers: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))


MCPServer: TypeAlias = StdioServer | StreamableHTTPServer | SSEServer


@dataclass(frozen=True, slots=True)
class MCPData:
    """Normalized values from a supported `mcp.json`."""

    schema: str
    servers: Mapping[str, MCPServer]
    issues: tuple[ValidationIssue, ...]
