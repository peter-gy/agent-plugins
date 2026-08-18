from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import agent_plugins as ap

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"


def test_mcp_is_a_lazy_cached_file_backed_model(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    _write_mcp(root / "mcp.json", {"demo": _stdio(command="before-access")})
    plugin = ap.Plugin(root)
    mcp = plugin.mcp
    assert mcp is not None

    assert mcp.path == (root / "mcp.json").resolve()
    assert Path(mcp) == mcp.path
    assert str(mcp) == str(mcp.path)
    assert repr(mcp) == f"MCPConfig(path={mcp.path!r})"
    with pytest.raises(AttributeError):
        object.__setattr__(mcp, "path", root / "other.json")

    _write_mcp(root / "mcp.json", {"demo": _stdio(command="first-access")})
    assert cast(ap.StdioServer, mcp.servers["demo"]).command == "first-access"

    _write_mcp(root / "mcp.json", {"demo": _stdio(command="after-access")})
    assert cast(ap.StdioServer, mcp.servers["demo"]).command == "first-access"


def test_mcp_exposes_typed_immutable_servers(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    _write_mcp(
        root / "mcp.json",
        {
            "local": _stdio(
                command="./bin/server",
                args=["--data", "${PLUGIN_DATA}/demo"],
                env={"CONFIG": "${PLUGIN_ROOT}/config.json"},
                cwd="${PLUGIN_ROOT}",
            ),
            "remote": {
                "type": "streamable-http",
                "url": "https://example.com/mcp",
                "headers": {"X-Tenant": "public"},
            },
            "legacy": {
                "type": "sse",
                "url": "http://127.0.0.1:8080/sse",
            },
        },
    )

    mcp = ap.Plugin(root).mcp
    assert mcp is not None
    assert mcp.schema == MCP_SCHEMA
    assert mcp.issues == ()

    local = mcp.servers["local"]
    assert local == ap.StdioServer(
        command="./bin/server",
        args=("--data", "${PLUGIN_DATA}/demo"),
        env={"CONFIG": "${PLUGIN_ROOT}/config.json"},
        cwd="${PLUGIN_ROOT}",
    )
    assert local.type == "stdio"

    remote = mcp.servers["remote"]
    assert remote == ap.StreamableHTTPServer(
        url="https://example.com/mcp",
        headers={"X-Tenant": "public"},
    )
    assert remote.type == "streamable-http"

    legacy = mcp.servers["legacy"]
    assert legacy == ap.SSEServer(url="http://127.0.0.1:8080/sse", headers={})
    assert legacy.type == "sse"

    with pytest.raises(TypeError):
        cast(dict[str, ap.MCPServer], mcp.servers)["other"] = local
    with pytest.raises(TypeError):
        cast(dict[str, str], local.env)["OTHER"] = "value"


@pytest.mark.parametrize(
    ("server", "message"),
    [
        ({"type": "stdio", "command": "/bin/server"}, "bare name or begin with ./"),
        (
            {"type": "stdio", "command": "./bin/server", "cwd": "data"},
            "Invalid stdio working directory",
        ),
        (
            {
                "type": "stdio",
                "command": "server",
                "env": {"PLUGIN_ROOT": "other"},
            },
            "reserved environment variable",
        ),
        (
            {"type": "streamable-http", "url": "http://example.com/mcp"},
            "HTTP is limited to loopback hosts",
        ),
        (
            {
                "type": "streamable-http",
                "url": "https://user@example.com/mcp",
            },
            "must not contain user information",
        ),
        (
            {"type": "streamable-http", "url": "https://example.com/mcp#part"},
            "must not contain a fragment",
        ),
        (
            {
                "type": "streamable-http",
                "url": "https://example.com/mcp",
                "headers": {"X-Value": "one", "x-value": "two"},
            },
            "Duplicate HTTP header name",
        ),
        (
            {
                "type": "streamable-http",
                "url": "https://example.com/mcp",
                "extra": True,
            },
            "Unknown streamable-http server field",
        ),
        ({"type": "unknown"}, "Unknown MCP server type"),
    ],
)
def test_mcp_skips_invalid_servers(
    tmp_path: Path, server: object, message: str
) -> None:
    root = _plugin_root(tmp_path)
    _write_mcp(
        root / "mcp.json",
        {"valid": _stdio(command="python"), "invalid": server},
    )

    mcp = ap.Plugin(root).mcp
    assert mcp is not None
    assert tuple(mcp.servers) == ("valid",)
    assert len(mcp.issues) == 1
    assert mcp.issues[0].location == ("mcpServers", "invalid")
    assert message in mcp.issues[0].message


def test_mcp_rejects_plugin_path_escapes(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "server").write_text("", encoding="utf-8")
    (root / "bin").symlink_to(outside, target_is_directory=True)
    _write_mcp(
        root / "mcp.json",
        {
            "command": _stdio(command="./bin/server"),
            "cwd": _stdio(command="server", cwd="${PLUGIN_ROOT}/../outside"),
        },
    )

    mcp = ap.Plugin(root).mcp
    assert mcp is not None
    assert mcp.servers == {}
    assert len(mcp.issues) == 2
    assert all("escapes the plugin root" in issue.message for issue in mcp.issues)


def test_mcp_rejects_cross_platform_path_escapes(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    _write_mcp(
        root / "mcp.json",
        {
            "command": _stdio(command="./..\\outside"),
            "root": _stdio(command="server", cwd="${PLUGIN_ROOT}/..\\outside"),
            "data": _stdio(command="server", cwd="${PLUGIN_DATA}/..\\outside"),
        },
    )

    mcp = ap.Plugin(root).mcp
    assert mcp is not None
    assert mcp.servers == {}
    assert len(mcp.issues) == 3
    assert all("escapes" in issue.message for issue in mcp.issues)


def test_document_symlinks_keep_the_plugin_root(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    config = root / "config"
    config.mkdir()
    (root / "plugin.json").rename(config / "plugin.json")
    (root / "mcp.json").rename(config / "mcp.json")
    (root / "plugin.json").symlink_to(config / "plugin.json")
    (root / "mcp.json").symlink_to(config / "mcp.json")
    binary = root / "bin"
    binary.mkdir()
    (binary / "server").write_text("", encoding="utf-8")
    (config / "bin").symlink_to(binary, target_is_directory=True)
    _write_mcp(
        config / "mcp.json",
        {"local": _stdio(command="./bin/server")},
    )

    plugin = ap.Plugin(root)
    mcp = plugin.mcp
    assert mcp is not None
    assert plugin.manifest.path == root / "plugin.json"
    assert mcp.path == root / "mcp.json"
    assert tuple(mcp.servers) == ("local",)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([], "Expected an object"),
        ({"$schema": MCP_SCHEMA}, "Missing required MCP field: mcpServers"),
        (
            {"$schema": MCP_SCHEMA, "mcpServers": {}, "extra": True},
            "Unknown MCP field",
        ),
        (
            {"$schema": "https://example.com/mcp.schema.json", "mcpServers": {}},
            "Unsupported or missing MCP schema",
        ),
    ],
)
def test_mcp_rejects_invalid_top_level_configuration(
    tmp_path: Path, value: object, message: str
) -> None:
    root = _plugin_root(tmp_path)
    (root / "mcp.json").write_text(json.dumps(value), encoding="utf-8")
    plugin = ap.Plugin(root)
    mcp = plugin.mcp
    assert mcp is not None

    with pytest.raises(ap.ValidationError, match=message):
        _servers = mcp.servers

    assert plugin.manifest.name == "demo-plugin"


def test_mcp_caches_validation_failures(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    (root / "mcp.json").write_text("[]", encoding="utf-8")
    mcp = ap.Plugin(root).mcp
    assert mcp is not None

    with pytest.raises(ap.ValidationError) as first:
        _servers = mcp.servers

    _write_mcp(root / "mcp.json", {})
    with pytest.raises(ap.ValidationError) as second:
        _servers = mcp.servers

    assert first.value is second.value
    fresh = ap.Plugin(root).mcp
    assert fresh is not None
    assert fresh.servers == {}


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/mcp",
        "http://localhost/mcp",
        "http://127.0.0.1:8080/mcp",
        "http://[::1]/mcp",
    ],
)
def test_mcp_accepts_supported_http_urls(tmp_path: Path, url: str) -> None:
    root = _plugin_root(tmp_path)
    _write_mcp(
        root / "mcp.json",
        {"server": {"type": "streamable-http", "url": url}},
    )

    mcp = ap.Plugin(root).mcp
    assert mcp is not None
    assert tuple(mcp.servers) == ("server",)


@pytest.mark.parametrize(
    ("server", "message"),
    [
        ({"type": "stdio"}, "Missing required MCP server field: command"),
        ({"type": "stdio", "command": ""}, "must not be empty"),
        ({"type": "stdio", "command": "bin/server"}, "begin with ./"),
        ({"type": "stdio", "command": "bin\\server"}, "begin with ./"),
        ({"type": "stdio", "command": "server", "args": None}, "array of strings"),
        ({"type": "stdio", "command": "server", "env": []}, "object of strings"),
        ({"type": "stdio", "command": "server", "cwd": None}, "cwd to be a string"),
        (
            {"type": "streamable-http"},
            "Missing required MCP server field: url",
        ),
        (
            {"type": "streamable-http", "url": "ftp://example.com/mcp"},
            "absolute HTTP or HTTPS",
        ),
        (
            {"type": "streamable-http", "url": "/relative"},
            "absolute HTTP or HTTPS",
        ),
        (
            {"type": "streamable-http", "url": "https://example.com:bad/mcp"},
            "Invalid MCP HTTP URL",
        ),
        (
            {"type": "streamable-http", "url": "https://example.com/mcp path"},
            "Invalid MCP HTTP URL",
        ),
        (
            {"type": "streamable-http", "url": "https:\\example.com\\mcp"},
            "Invalid MCP HTTP URL",
        ),
        (
            {"type": "streamable-http", "url": "https://example.com/%invalid"},
            "Invalid MCP HTTP URL",
        ),
        (
            {
                "type": "streamable-http",
                "url": "https://example.com/mcp",
                "headers": {"Bad Name": "value"},
            },
            "Invalid HTTP header name",
        ),
        (
            {
                "type": "streamable-http",
                "url": "https://example.com/mcp",
                "headers": {"X-Value": "line\nbreak"},
            },
            "Invalid HTTP header value",
        ),
        (
            {
                "type": "sse",
                "url": "https://example.com/sse",
                "command": "server",
            },
            "Unknown sse server field",
        ),
    ],
)
def test_mcp_enforces_closed_server_schemas(
    tmp_path: Path, server: object, message: str
) -> None:
    root = _plugin_root(tmp_path)
    _write_mcp(root / "mcp.json", {"invalid": server})

    mcp = ap.Plugin(root).mcp
    assert mcp is not None
    assert mcp.servers == {}
    assert message in mcp.issues[0].message


def test_mcp_validates_the_manifest_before_configuration(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    (root / "plugin.json").write_text("{}", encoding="utf-8")
    _write_mcp(root / "mcp.json", {})
    mcp = ap.Plugin(root).mcp
    assert mcp is not None

    with pytest.raises(ap.ValidationError) as captured:
        _servers = mcp.servers

    assert captured.value.path == (root / "plugin.json").resolve()


def _plugin_root(tmp_path: Path) -> Path:
    root = tmp_path / "demo.agent-plugin"
    root.mkdir()
    (root / "plugin.json").write_text(
        json.dumps({"$schema": PLUGIN_SCHEMA, "name": "demo-plugin"}),
        encoding="utf-8",
    )
    (root / "mcp.json").write_text("{}", encoding="utf-8")
    return root


def _write_mcp(path: Path, servers: dict[str, object]) -> None:
    path.write_text(
        json.dumps({"$schema": MCP_SCHEMA, "mcpServers": servers}),
        encoding="utf-8",
    )


def _stdio(command: str, **values: object) -> dict[str, object]:
    return {"type": "stdio", "command": command, **values}
