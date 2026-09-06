from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

import agent_plugins as ap

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"


def test_resolve_stdio_preserves_bare_command_and_defaults_to_plugin_root(
    tmp_path: Path,
) -> None:
    root = _plugin(tmp_path, {"local": _stdio("python", args=["-m", "server"])})
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    mcp = _mcp(root)

    launch = mcp.resolve_stdio("local", data_dir=data_dir)

    assert launch == ap.ResolvedStdioServer(
        command="python",
        args=("-m", "server"),
        env={
            "PLUGIN_ROOT": str(root.resolve()),
            "PLUGIN_DATA": str(data_dir.resolve()),
        },
        cwd=root.resolve(),
    )


def test_resolve_stdio_expands_values_and_applies_environment_precedence(
    tmp_path: Path,
) -> None:
    root = _plugin(
        tmp_path,
        {
            "local": _stdio(
                "./bin/server",
                args=[
                    "--root=${PLUGIN_ROOT}",
                    "--data",
                    "${PLUGIN_DATA}/cache",
                ],
                env={
                    "SHARED": "configured",
                    "I": "configured-unicode",
                    "CONFIG": "${PLUGIN_ROOT}/config.json",
                    "plugin_root": "configured-lowercase",
                },
                cwd="${PLUGIN_ROOT}/work",
            )
        },
    )
    binary = root / "bin"
    binary.mkdir()
    server = binary / "server"
    server.write_text("server\n", encoding="utf-8")
    work = root / "work"
    work.mkdir()
    (work / "state.json").write_text("{}\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    (data_dir / "cache").mkdir(parents=True)
    base_env = {
        "SHARED": "base",
        "shared": "base-lowercase",
        "\u0131": "base-unicode",
        "PLUGIN_ROOT": "hostile-root",
        "PLUGIN_DATA": "hostile-data",
    }

    launch = _mcp(root).resolve_stdio("local", data_dir=data_dir, base_env=base_env)

    assert launch.command == str(server.resolve())
    assert launch.args == (
        f"--root={root.resolve()}",
        "--data",
        f"{data_dir.resolve()}/cache",
    )
    assert launch.cwd == work.resolve()
    assert launch.env["SHARED"] == "configured"
    assert launch.env["I"] == "configured-unicode"
    assert launch.env["CONFIG"] == f"{root.resolve()}/config.json"
    assert launch.env["PLUGIN_ROOT"] == str(root.resolve())
    assert launch.env["PLUGIN_DATA"] == str(data_dir.resolve())
    if os.name == "nt":
        assert "shared" not in launch.env
        assert "\u0131" not in launch.env
        assert "plugin_root" not in launch.env
    else:
        assert launch.env["shared"] == "base-lowercase"
        assert launch.env["\u0131"] == "base-unicode"
        assert launch.env["plugin_root"] == "configured-lowercase"


def test_resolve_stdio_expansion_is_single_pass_and_leaves_keys_literal(
    tmp_path: Path,
) -> None:
    root = _plugin(
        tmp_path,
        {
            "local": _stdio(
                "${PLUGIN_ROOT}",
                args=["${PLUGIN_DATA}", "${UNKNOWN}"],
                env={"${PLUGIN_ROOT}": "${PLUGIN_DATA}"},
            )
        },
    )
    data_dir = tmp_path / "${PLUGIN_ROOT}" / "data"
    data_dir.mkdir(parents=True)

    launch = _mcp(root).resolve_stdio("local", data_dir=data_dir)

    assert launch.command == "${PLUGIN_ROOT}"
    assert launch.args == (str(data_dir.resolve()), "${UNKNOWN}")
    assert "${PLUGIN_ROOT}" in launch.args[0]
    assert launch.env["${PLUGIN_ROOT}"] == str(data_dir.resolve())


@pytest.mark.parametrize(
    ("name", "server", "message"),
    [
        (
            "missing",
            {"type": "stdio", "command": "python"},
            "MCP server 'missing' is unavailable",
        ),
        (
            "remote",
            {"type": "streamable-http", "url": "https://example.com/mcp"},
            "uses 'streamable-http', not 'stdio'",
        ),
    ],
)
def test_resolve_stdio_rejects_unknown_or_non_stdio_server(
    tmp_path: Path,
    name: str,
    server: dict[str, object],
    message: str,
) -> None:
    root = _plugin(tmp_path, {"local": _stdio("python"), "remote": server})
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with pytest.raises(ap.AgentPluginError, match=message):
        _mcp(root).resolve_stdio(name, data_dir=data_dir)


@pytest.mark.parametrize("data_kind", ["missing", "file"])
def test_resolve_stdio_requires_existing_data_directory(
    tmp_path: Path, data_kind: str
) -> None:
    root = _plugin(tmp_path, {"local": _stdio("python")})
    data_dir = tmp_path / "data"
    if data_kind == "file":
        data_dir.write_text("data\n", encoding="utf-8")

    with pytest.raises(ap.AgentPluginError, match="Plugin data directory"):
        _mcp(root).resolve_stdio("local", data_dir=data_dir)


def test_resolve_stdio_rejects_unselected_plugin_command(tmp_path: Path) -> None:
    root = _plugin(tmp_path, {"local": _stdio("./bin/missing")})
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with pytest.raises(
        ap.AgentPluginError,
        match="command is unavailable in the selected plugin",
    ):
        _mcp(root).resolve_stdio("local", data_dir=data_dir)


def test_resolve_stdio_requires_existing_plugin_working_directory(
    tmp_path: Path,
) -> None:
    root = _plugin(tmp_path, {"local": _stdio("python", cwd="./missing")})
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with pytest.raises(ap.AgentPluginError, match="working directory"):
        _mcp(root).resolve_stdio("local", data_dir=data_dir)


def test_resolve_stdio_tracks_data_working_directory_state(tmp_path: Path) -> None:
    root = _plugin(
        tmp_path,
        {"local": _stdio("python", cwd="${PLUGIN_DATA}/work")},
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    work = data_dir / "work"
    mcp = _mcp(root)

    with pytest.raises(ap.AgentPluginError, match="working directory"):
        mcp.resolve_stdio("local", data_dir=data_dir)

    work.write_text("work\n", encoding="utf-8")
    with pytest.raises(ap.AgentPluginError, match="not a directory"):
        mcp.resolve_stdio("local", data_dir=data_dir)

    work.unlink()
    work.mkdir()
    launch = mcp.resolve_stdio("local", data_dir=data_dir)

    assert launch.cwd == work.resolve()


def test_resolve_stdio_rechecks_command_and_cwd_containment(tmp_path: Path) -> None:
    root = _plugin(
        tmp_path,
        {"local": _stdio("./bin/server", cwd="${PLUGIN_DATA}/work")},
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "server").write_text("server\n", encoding="utf-8")
    binary = root / "bin"
    binary.mkdir()
    server = binary / "server"
    server.write_text("server\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    work = data_dir / "work"
    work.mkdir()
    mcp = _mcp(root)
    assert tuple(mcp.servers) == ("local",)
    server.unlink()
    server.symlink_to(outside / "server")
    work.rmdir()
    work.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ap.AgentPluginError, match="selected plugin"):
        mcp.resolve_stdio("local", data_dir=data_dir)

    server.unlink()
    server.write_text("server\n", encoding="utf-8")
    with pytest.raises(ap.AgentPluginError, match="working directory"):
        mcp.resolve_stdio("local", data_dir=data_dir)


def test_resolve_stdio_rejects_plugin_root_replacement(tmp_path: Path) -> None:
    root = _plugin(tmp_path, {"local": _stdio("python")})
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    mcp = _mcp(root)
    assert tuple(mcp.servers) == ("local",)
    moved = tmp_path / "moved"
    root.rename(moved)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        root.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")

    with pytest.raises(ap.AgentPluginError, match="Plugin root changed"):
        mcp.resolve_stdio("local", data_dir=data_dir)


def test_resolve_stdio_rejects_unselected_project_paths(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    project = root / "packages" / "python"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[tool.agent-plugins]\nroot = "../.."\ninclude = ["bin/**"]\n',
        encoding="utf-8",
    )
    (root / "plugin.json").write_text(
        json.dumps({"$schema": PLUGIN_SCHEMA, "name": "demo"}),
        encoding="utf-8",
    )
    _write_mcp(root, {"local": _stdio("./bin/server", cwd="./work")})
    (root / "bin").mkdir()
    (root / "bin" / "server").write_text("server\n", encoding="utf-8")
    (root / "work").mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    mcp = ap.Plugin.from_project(project).mcp
    assert mcp is not None

    with pytest.raises(
        ap.AgentPluginError,
        match="working directory is unavailable in the selected plugin",
    ):
        mcp.resolve_stdio("local", data_dir=data_dir)


def test_direct_mcp_config_resolves_contained_physical_paths(tmp_path: Path) -> None:
    root = _plugin(
        tmp_path,
        {"local": _stdio("./bin/server", cwd="./work")},
    )
    binary = root / "bin"
    binary.mkdir()
    server = binary / "server"
    server.write_text("server\n", encoding="utf-8")
    work = root / "work"
    work.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    manifest = ap.Manifest(root / "plugin.json")
    mcp = ap.MCPConfig(root / "mcp.json", manifest)

    launch = mcp.resolve_stdio("local", data_dir=data_dir)

    assert launch.command == str(server.resolve())
    assert launch.cwd == work.resolve()

    server.unlink()
    server.mkdir()
    with pytest.raises(ap.AgentPluginError, match="not a regular file"):
        mcp.resolve_stdio("local", data_dir=data_dir)


def test_plugin_relative_command_accepts_portable_backslash_separator(
    tmp_path: Path,
) -> None:
    root = _plugin(tmp_path, {"local": _stdio("./bin\\server")})
    binary = root / "bin"
    binary.mkdir()
    server = binary / "server"
    server.write_text("server\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    launch = _mcp(root).resolve_stdio("local", data_dir=data_dir)

    assert launch.command == str(server.resolve())


@pytest.mark.skipif(os.name == "nt", reason="POSIX absolute path expansion case")
def test_plugin_relative_cwd_keeps_expanded_root_relative(tmp_path: Path) -> None:
    parent = tmp_path / "parent\\part"
    parent.mkdir()
    root = _plugin(
        parent,
        {"local": _stdio("python", cwd="./${PLUGIN_ROOT}")},
    )
    relative_root = Path(str(root.resolve()).lstrip("/"))
    expected = root.joinpath(relative_root)
    expected.mkdir(parents=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    mcp = ap.MCPConfig(root / "mcp.json", ap.Manifest(root / "plugin.json"))

    launch = mcp.resolve_stdio("local", data_dir=data_dir)

    assert launch.cwd == expected.resolve()


def test_resolved_stdio_result_is_immutable_and_copies_environment(
    tmp_path: Path,
) -> None:
    root = _plugin(tmp_path, {"local": _stdio("python")})
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    base_env = {"VALUE": "before"}
    mcp = _mcp(root)
    launch = mcp.resolve_stdio("local", data_dir=data_dir, base_env=base_env)
    base_env["VALUE"] = "after"

    assert launch.env["VALUE"] == "before"
    with pytest.raises(TypeError):
        cast(dict[str, str], launch.env)["VALUE"] = "changed"
    with pytest.raises(AttributeError):
        launch.__setattr__("cwd", tmp_path)

    other_data = tmp_path / "other-data"
    other_data.mkdir()
    other = mcp.resolve_stdio("local", data_dir=other_data, base_env={"VALUE": "other"})
    assert other.env["VALUE"] == "other"
    assert other.env["PLUGIN_DATA"] == str(other_data.resolve())


def test_resolved_stdio_inputs_run_without_a_shell(tmp_path: Path) -> None:
    command = Path(sys.executable).name
    program = (
        "import json, os; "
        "print(json.dumps({'cwd': os.getcwd(), "
        "'root': os.environ['PLUGIN_ROOT'], "
        "'data': os.environ['PLUGIN_DATA']}))"
    )
    root = _plugin(tmp_path, {"local": _stdio(command, args=["-c", program])})
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    base_env = dict(os.environ)
    base_env["PATH"] = (
        f"{Path(sys.executable).parent}{os.pathsep}{base_env.get('PATH', '')}"
    )
    launch = _mcp(root).resolve_stdio("local", data_dir=data_dir, base_env=base_env)

    completed = subprocess.run(
        [launch.command, *launch.args],
        cwd=launch.cwd,
        env=dict(launch.env),
        check=True,
        capture_output=True,
        text=True,
    )
    output = json.loads(completed.stdout)

    assert output == {
        "cwd": str(root.resolve()),
        "root": str(root.resolve()),
        "data": str(data_dir.resolve()),
    }


def _plugin(tmp_path: Path, servers: dict[str, object]) -> Path:
    root = tmp_path / "demo.agent-plugin"
    root.mkdir()
    (root / "plugin.json").write_text(
        json.dumps({"$schema": PLUGIN_SCHEMA, "name": "demo"}),
        encoding="utf-8",
    )
    _write_mcp(root, servers)
    return root


def _write_mcp(root: Path, servers: dict[str, object]) -> None:
    (root / "mcp.json").write_text(
        json.dumps({"$schema": MCP_SCHEMA, "mcpServers": servers}),
        encoding="utf-8",
    )


def _stdio(command: str, **values: object) -> dict[str, object]:
    return {"type": "stdio", "command": command, **values}


def _mcp(root: Path) -> ap.MCPConfig:
    mcp = ap.Plugin(root).mcp
    assert mcp is not None
    return mcp
