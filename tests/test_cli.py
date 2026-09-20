from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from agent_plugins._cli import main

DIST_INFO = "demo-1.0.0.dist-info"
WHEEL_NAME = "demo-1.0.0-py3-none-any.whl"
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"


def test_attach_wheel_command_prints_output_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _project(tmp_path)
    wheel = _wheel(tmp_path / WHEEL_NAME)
    monkeypatch.chdir(project)

    assert main(["attach-wheel", str(wheel)]) == 0

    output = capsys.readouterr()
    assert output.out == f"{wheel.resolve()}\n"
    assert output.err == ""


def test_attach_wheel_command_prints_stable_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)
    wheel = _wheel(tmp_path / WHEEL_NAME)
    output_dir = tmp_path / "attached"
    output_dir.mkdir()

    assert (
        main(
            [
                "attach-wheel",
                str(wheel),
                "--project",
                str(project),
                "--output-dir",
                str(output_dir),
                "--json",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    value = json.loads(captured.out)
    assert value == {
        "source": str(wheel.resolve()),
        "output": str((output_dir / WHEEL_NAME).resolve()),
        "dist_info": DIST_INFO,
        "plugin_root": "demo-1.0.0.agent-plugin",
        "files": ["plugin.json"],
        "replaced_existing_plugin": False,
        "removed_signatures": [],
    }
    assert captured.err == ""


def test_attach_wheel_command_reports_signature_removal_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)
    wheel = _wheel(tmp_path / WHEEL_NAME, signatures=True)

    assert main(["attach-wheel", str(wheel), "--project", str(project), "--json"]) == 0

    output = capsys.readouterr()
    assert json.loads(output.out)["removed_signatures"] == [
        f"{DIST_INFO}/RECORD.jws",
        f"{DIST_INFO}/RECORD.p7s",
    ]
    assert output.err == (
        "agent-plugins: warning: removed invalidated wheel signature: "
        f"{DIST_INFO}/RECORD.jws\n"
        "agent-plugins: warning: removed invalidated wheel signature: "
        f"{DIST_INFO}/RECORD.p7s\n"
    )


def test_attach_wheel_command_reports_expected_failure_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = _project(tmp_path)
    missing = tmp_path / "missing.whl"

    assert main(["attach-wheel", str(missing), "--project", str(project)]) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.startswith("agent-plugins: error: Wheel cannot be read:")
    assert "Traceback" not in output.err


def test_attach_wheel_command_keeps_argument_error_status() -> None:
    with pytest.raises(SystemExit) as error:
        main(["attach-wheel"])

    assert error.value.code == 2


def test_read_command_prints_generated_guidance_and_complete_skills(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, first_source, second_source = _installed_plugin(tmp_path, extended=True)
    monkeypatch.syspath_prepend(str(tmp_path))

    assert main(["read", "demo-provider"]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.startswith("# Agent Plugin: `demo`\n")
    assert "Python distribution: `demo-provider==1.2.3`" in output.out
    assert "Distribution summary: Demonstrate installed plugins" in output.out
    assert "Plugin description: Agent instructions for Demo" in output.out
    assert f"Installed root: `{root.resolve()}`" in output.out
    assert "## Plugin inventory" in output.out
    assert "file-99.md" not in output.out
    assert "final.md" not in output.out
    assert "more files" in output.out
    assert "`-- ..." in output.out
    assert "````text\n" in output.out
    assert "## Agent Skill: ```tick``skill```" in output.out
    assert "## Client extensions\n\n- `com.example.client`" in output.out
    assert "- `demo-server` (`stdio`)" in output.out
    assert "- `remote-server` (`streamable-http`)" in output.out
    assert "- `legacy-server` (`sse`)" in output.out
    for secret in (
        "private-command",
        "private-argument",
        "PRIVATE_ENV_VALUE",
        "https://private.example.com/mcp",
        "PRIVATE_HEADER_VALUE",
        "https://private.example.com/sse",
    ):
        assert secret not in output.out
    assert "## Agent Skill: `first`" in output.out
    assert "## Agent Skill: `second`" in output.out
    assert first_source in output.out
    assert second_source in output.out


def test_read_command_can_select_one_skill(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _root, first_source, second_source = _installed_plugin(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    assert main(["read", "demo-provider", "--skill", "second"]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert "## Agent Skill: `first`" not in output.out
    assert "## Agent Skill: `second`" in output.out
    assert first_source not in output.out
    assert second_source in output.out


def test_read_command_reports_an_unavailable_skill(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _installed_plugin(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    assert main(["read", "demo-provider", "--skill", "missing"]) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        "agent-plugins: error: Agent Skill 'missing' is unavailable. "
        "Available skills: first, second\n"
    )


def test_read_command_reports_an_uninstalled_distribution(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["read", "distribution-that-does-not-exist"]) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        "agent-plugins: error: Python distribution "
        "'distribution-that-does-not-exist' is not installed\n"
    )


def test_no_command_reads_the_agent_plugins_distribution(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str | None]] = []

    def render(distribution: str, *, skill_name: str | None = None) -> str:
        calls.append((distribution, skill_name))
        return "installed agent guidance\n"

    monkeypatch.setattr("agent_plugins._cli.render_read", render)

    assert main([]) == 0
    shortcut = capsys.readouterr()

    assert main(["read", "agent-plugins"]) == 0
    explicit = capsys.readouterr()

    assert shortcut == explicit
    assert shortcut.out == "installed agent guidance\n"
    assert shortcut.err == ""
    assert calls == [("agent-plugins", None), ("agent-plugins", None)]


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[tool.agent-plugins]\nroot = "."\n', encoding="utf-8"
    )
    (project / "plugin.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    return project


def _wheel(path: Path, *, signatures: bool = False) -> Path:
    members = {
        "demo/__init__.py": b"",
        f"{DIST_INFO}/WHEEL": b"Wheel-Version: 1.0\n",
        f"{DIST_INFO}/METADATA": b"Metadata-Version: 2.4\nName: demo\nVersion: 1.0.0\n",
        f"{DIST_INFO}/RECORD": b"",
    }
    if signatures:
        members[f"{DIST_INFO}/RECORD.jws"] = b"jws"
        members[f"{DIST_INFO}/RECORD.p7s"] = b"p7s"
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in members.items():
            archive.writestr(name, value)
    return path


def _installed_plugin(
    tmp_path: Path, *, extended: bool = False
) -> tuple[Path, str, str]:
    dist_info = tmp_path / "demo_provider-1.2.3.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.4\n"
        "Name: demo-provider\n"
        "Version: 1.2.3\n"
        "Summary: Demonstrate installed plugins\n",
        encoding="utf-8",
    )

    root = tmp_path / "demo_provider-1.2.3.agent-plugin"
    first = root / "skills/first"
    second = root / "skills/second"
    reference = first / "references/api.md"
    extension = root / "com.example.client/config.json"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    reference.parent.mkdir(parents=True)
    extension.parent.mkdir(parents=True)

    first_source = (
        "---\n"
        "name: first\n"
        "description: Use the first capability.\n"
        "---\n"
        "# First skill\n\n"
        "Read [the API reference](references/api.md).\n\n\n"
    )
    second_source = (
        "---\n"
        "name: second\n"
        "description: Use the second capability.\n"
        "---\n"
        "# Second skill"
    )
    (first / "SKILL.md").write_text(first_source, encoding="utf-8")
    (second / "SKILL.md").write_text(second_source, encoding="utf-8")
    reference.write_text("# API\n", encoding="utf-8")
    extension.write_text('{"enabled":true}\n', encoding="utf-8")
    (root / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": PLUGIN_SCHEMA,
                "name": "demo",
                "version": "4.5.6",
                "description": "Agent instructions for Demo",
                "author": {
                    "name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "url": "https://example.com/ada",
                },
                "homepage": "https://example.com/demo",
                "repository": "https://example.com/demo.git",
                "license": "MIT",
                "keywords": ["demo", "agents"],
                "extensions": {"com.example.client": {"enabled": True}},
            }
        ),
        encoding="utf-8",
    )
    (root / "mcp.json").write_text(
        json.dumps(
            {
                "$schema": MCP_SCHEMA,
                "mcpServers": {
                    "demo-server": {
                        "type": "stdio",
                        "command": "private-command",
                        "args": ["private-argument"],
                        "env": {"PRIVATE_ENV": "PRIVATE_ENV_VALUE"},
                    },
                    "remote-server": {
                        "type": "streamable-http",
                        "url": "https://private.example.com/mcp",
                        "headers": {"X-Private": "PRIVATE_HEADER_VALUE"},
                    },
                    "legacy-server": {
                        "type": "sse",
                        "url": "https://private.example.com/sse",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    files = [
        "plugin.json",
        "mcp.json",
        "skills/first/SKILL.md",
        "skills/first/references/api.md",
        "skills/second/SKILL.md",
        "com.example.client/config.json",
    ]
    if extended:
        deep = first / "references/deep/level/final.md"
        deep.parent.mkdir(parents=True)
        deep.write_text("# Final\n", encoding="utf-8")
        files.append("skills/first/references/deep/level/final.md")
        for index in range(101):
            relative = f"skills/first/references/file-{index}.md"
            (root / relative).write_text(f"# File {index}\n", encoding="utf-8")
            files.append(relative)
        tricky_reference = first / "references/```marker.md"
        tricky_reference.write_text("# Marker\n", encoding="utf-8")
        files.append("skills/first/references/```marker.md")
        tricky_skill = root / "skills/tick``skill/SKILL.md"
        tricky_skill.parent.mkdir(parents=True)
        tricky_skill.write_text(
            "---\nname: tick-skill\ndescription: Exercise Markdown delimiters.\n---\n",
            encoding="utf-8",
        )
        files.append("skills/tick``skill/SKILL.md")
    (dist_info / "agent_plugins.json").write_text(
        json.dumps({"root": root.name, "files": files}), encoding="utf-8"
    )
    return (
        root,
        (first / "SKILL.md").read_bytes().decode("utf-8"),
        (second / "SKILL.md").read_bytes().decode("utf-8"),
    )
