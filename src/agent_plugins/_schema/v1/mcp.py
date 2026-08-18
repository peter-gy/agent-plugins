"""Agent Plugins 1.0.0 MCP configuration validation."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import cast
from urllib.parse import urlsplit

from ..errors import ValidationIssue
from ..json import validation_error
from ..models import MCPServer, SSEServer, StdioServer, StreamableHTTPServer

_TOP_LEVEL_FIELDS = frozenset({"$schema", "mcpServers"})
_STDIO_FIELDS = frozenset({"type", "command", "args", "env", "cwd"})
_HTTP_FIELDS = frozenset({"type", "url", "headers"})
_HEADER_NAME = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


class _InvalidServer(ValueError):
    pass


def load_mcp_v1(
    path: Path,
    value: dict[str, object],
    root: Path,
) -> tuple[dict[str, MCPServer], tuple[ValidationIssue, ...]]:
    """Validate an Agent Plugins 1.0.0 MCP configuration."""
    unknown = next((field for field in value if field not in _TOP_LEVEL_FIELDS), None)
    if unknown is not None:
        raise validation_error(path, (unknown,), f"Unknown MCP field: {unknown}")
    if "mcpServers" not in value:
        raise validation_error(
            path, ("mcpServers",), "Missing required MCP field: mcpServers"
        )
    servers_value = value["mcpServers"]
    if not isinstance(servers_value, dict):
        raise validation_error(path, ("mcpServers",), "Expected an object")

    servers: dict[str, MCPServer] = {}
    issues: list[ValidationIssue] = []
    for name, server_value in servers_value.items():
        try:
            servers[name] = _server(cast(object, server_value), root)
        except _InvalidServer as error:
            issues.append(ValidationIssue(("mcpServers", name), str(error)))
    return servers, tuple(issues)


def _server(value: object, root: Path) -> MCPServer:
    if not isinstance(value, dict):
        raise _InvalidServer("Expected an object")
    server = cast(dict[str, object], value)
    server_type = server.get("type")
    if server_type == "stdio":
        return _stdio(server, root)
    if server_type == "streamable-http":
        return _http(server, "streamable-http")
    if server_type == "sse":
        return _http(server, "sse")
    raise _InvalidServer("Unknown MCP server type")


def _stdio(value: dict[str, object], root: Path) -> StdioServer:
    _reject_unknown(value, _STDIO_FIELDS, "stdio")
    command = _required_string(value, "command")
    if not command:
        raise _InvalidServer("MCP stdio command must not be empty")
    if command.startswith("./"):
        _plugin_path(root, command)
    elif "/" in command or "\\" in command or "\0" in command:
        raise _InvalidServer("MCP stdio command must be a bare name or begin with ./")

    args = _string_array(value, "args")
    env = _string_map(value, "env")
    reserved = next(
        (name for name in env if name in {"PLUGIN_ROOT", "PLUGIN_DATA"}), None
    )
    if reserved is not None:
        raise _InvalidServer(
            f"MCP stdio env contains reserved environment variable: {reserved}"
        )

    cwd: str | None = None
    if "cwd" in value:
        cwd_value = value["cwd"]
        if not isinstance(cwd_value, str):
            raise _InvalidServer("Expected stdio cwd to be a string")
        cwd = cwd_value
    if cwd is not None:
        _cwd(root, cwd)

    return StdioServer(
        command=command,
        args=args,
        env=MappingProxyType(env),
        cwd=cwd,
    )


def _http(
    value: dict[str, object], server_type: str
) -> StreamableHTTPServer | SSEServer:
    _reject_unknown(value, _HTTP_FIELDS, server_type)
    url = _required_string(value, "url")
    _url(url)
    headers = MappingProxyType(_headers(value))
    if server_type == "streamable-http":
        return StreamableHTTPServer(url=url, headers=headers)
    return SSEServer(url=url, headers=headers)


def _cwd(root: Path, value: str) -> None:
    if value.startswith("./"):
        _plugin_path(root, value)
        return
    if value == "${PLUGIN_ROOT}":
        return
    if value.startswith("${PLUGIN_ROOT}/"):
        _plugin_path(root, "./" + value.removeprefix("${PLUGIN_ROOT}/"))
        return
    if value == "${PLUGIN_DATA}":
        return
    if value.startswith("${PLUGIN_DATA}/"):
        if _escapes(value.removeprefix("${PLUGIN_DATA}/")):
            raise _InvalidServer("MCP stdio cwd escapes the plugin data directory")
        return
    raise _InvalidServer("Invalid stdio working directory")


def _plugin_path(root: Path, value: str) -> None:
    relative = PurePosixPath(value.removeprefix("./").replace("\\", "/"))
    candidate = root.joinpath(*relative.parts)
    try:
        candidate.resolve(strict=False).relative_to(root)
    except (OSError, ValueError) as error:
        raise _InvalidServer("MCP server path escapes the plugin root") from error


def _escapes(value: str) -> bool:
    depth = 0
    for part in PurePosixPath(value.replace("\\", "/").lstrip("/")).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if depth == 0:
                return True
            depth -= 1
        else:
            depth += 1
    return False


def _url(value: str) -> None:
    if not value:
        raise _InvalidServer("MCP HTTP URL must not be empty")
    if (
        "\\" in value
        or _INVALID_PERCENT_ESCAPE.search(value) is not None
        or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise _InvalidServer("Invalid MCP HTTP URL")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        _port = parsed.port
    except ValueError as error:
        raise _InvalidServer("Invalid MCP HTTP URL") from error
    if parsed.scheme.lower() not in {"http", "https"} or host is None:
        raise _InvalidServer("MCP URL must be an absolute HTTP or HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise _InvalidServer("MCP URL must not contain user information")
    if "#" in value:
        raise _InvalidServer("MCP URL must not contain a fragment")
    if parsed.scheme.lower() == "http" and not _loopback(host):
        raise _InvalidServer("MCP HTTP is limited to loopback hosts")


def _loopback(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _headers(value: dict[str, object]) -> dict[str, str]:
    headers = _string_map(value, "headers")
    seen: set[str] = set()
    for name, header_value in headers.items():
        folded = name.casefold()
        if folded in seen:
            raise _InvalidServer(f"Duplicate HTTP header name: {name}")
        seen.add(folded)
        if _HEADER_NAME.fullmatch(name) is None:
            raise _InvalidServer(f"Invalid HTTP header name: {name}")
        if not all(_header_character(character) for character in header_value):
            raise _InvalidServer(f"Invalid HTTP header value for {name}")
    return headers


def _header_character(value: str) -> bool:
    codepoint = ord(value)
    return value == "\t" or 0x20 <= codepoint <= 0x7E or 0x80 <= codepoint <= 0xFF


def _required_string(value: dict[str, object], field: str) -> str:
    if field not in value:
        raise _InvalidServer(f"Missing required MCP server field: {field}")
    item = value[field]
    if not isinstance(item, str):
        raise _InvalidServer(f"Expected {field} to be a string")
    return item


def _string_array(value: dict[str, object], field: str) -> tuple[str, ...]:
    item = value.get(field, [])
    if not isinstance(item, list) or not all(isinstance(entry, str) for entry in item):
        raise _InvalidServer(f"Expected {field} to be an array of strings")
    return tuple(cast(list[str], item))


def _string_map(value: dict[str, object], field: str) -> dict[str, str]:
    item = value.get(field, {})
    if not isinstance(item, dict) or not all(
        isinstance(entry, str) for entry in item.values()
    ):
        raise _InvalidServer(f"Expected {field} to be an object of strings")
    return cast(dict[str, str], item)


def _reject_unknown(
    value: dict[str, object], allowed: frozenset[str], server_type: str
) -> None:
    unknown = next((field for field in value if field not in allowed), None)
    if unknown is not None:
        raise _InvalidServer(f"Unknown {server_type} server field: {unknown}")
