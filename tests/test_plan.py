from __future__ import annotations

import json
from pathlib import Path

import pytest

import agent_plugins as ap
from agent_plugins._cli import main


def test_project_build_plan_includes_its_agent_plugin() -> None:
    project = Path(__file__).parents[1]

    plan = ap.build_plan(project)

    assert isinstance(plan, ap.BuildPlan)

    assert [mapping.target.as_posix() for mapping in plan.files] == [
        "plugin.json",
        "skills/agent-plugins/SKILL.md",
        "skills/agent-plugins/agents/openai.yaml",
    ]


def test_build_plan_carries_fixed_and_declared_plugin_files(tmp_path: Path) -> None:
    project, root = _project(tmp_path)

    plan = ap.build_plan(project)

    assert plan.root == root.resolve()
    assert [mapping.target.as_posix() for mapping in plan.files] == [
        "bin/server.py",
        "mcp.json",
        "plugin.json",
        "skills/demo/SKILL.md",
        "skills/demo/references/guide.md",
    ]


def test_plan_json_reports_absolute_sources(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project, root = _project(tmp_path)

    assert main(["plan", str(project), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["project"] == str(project.resolve())
    assert output["root"] == str(root.resolve())
    assert output["files"][0] == {
        "source": str((root / "bin" / "server.py").resolve()),
        "target": "bin/server.py",
    }


def test_include_pattern_must_match_a_plugin_file(tmp_path: Path) -> None:
    project, _root = _project(tmp_path, include="missing/**")

    with pytest.raises(ap.AgentPluginError, match="matched no files: missing/\\*\\*"):
        ap.build_plan(project)


def test_plan_command_reports_configuration_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["plan", str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        f"agent-plugins: error: Project has no pyproject.toml: {tmp_path.resolve()}\n"
    )


def _project(tmp_path: Path, *, include: str = "bin/**") -> tuple[Path, Path]:
    root = tmp_path / "repository"
    project = root / "packages" / "demo"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        f"""\
[tool.agent-plugins]
root = "../.."
include = ["{include}"]
""",
        encoding="utf-8",
    )
    (root / "plugin.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (root / "mcp.json").write_text('{"mcpServers":{}}\n', encoding="utf-8")
    skill = root / "skills" / "demo"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
    (skill / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    binary = root / "bin"
    binary.mkdir()
    (binary / "server.py").write_text("print('demo')\n", encoding="utf-8")
    return project, root
