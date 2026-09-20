from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

import agent_plugins as ap
from agent_plugins._cli import main


@pytest.mark.parametrize("skill", [None, "example-package", "publish"])
def test_read_returns_selected_briefing_shared_with_cli_and_module_help(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    skill: str | None,
) -> None:
    _install_plugin(tmp_path, monkeypatch, "example-package", "publish")
    selected = "example-package" if skill is None else skill
    plugin = ap.locate("example-package")

    text = ap.read("example-package", skill=skill)

    assert capsys.readouterr().out == ""
    assert plugin.skill(selected).source in text
    other = "publish" if selected == "example-package" else "example-package"
    assert plugin.skill(other).source not in text
    assert "Python distribution: `example-package==1.2.3`" in text
    assert f"Python interpreter: `{sys.executable}`" in text
    assert f"Installed root: `{plugin.path}`" in text
    assert "Documentation: https://example.org/docs/" in text
    assert "Documentation Index: https://example.org/docs/llms.txt" in text
    assert "uvx" in text
    assert "example_package" not in sys.modules

    assert main(["read", "example-package", "--skill", selected]) == 0
    assert capsys.readouterr().out == text

    module = ModuleType("example_agent")
    module.__doc__ = text
    help(module)
    help_text = capsys.readouterr().out
    assert "Python distribution: `example-package==1.2.3`" in help_text
    assert f"Use the {selected} workflow." in help_text


def test_read_requires_the_default_skill_even_with_one_other_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_plugin(tmp_path, monkeypatch, "publish")

    with pytest.raises(ap.AgentPluginError, match="Available skills: publish"):
        ap.read("example-package")


@pytest.mark.parametrize(
    ("skill", "message"),
    [
        ("", "Invalid Agent Skill directory name"),
        ("missing", "Available skills: example-package"),
    ],
)
def test_read_reports_an_unavailable_explicit_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, skill: str, message: str
) -> None:
    _install_plugin(tmp_path, monkeypatch, "example-package")

    with pytest.raises(ap.AgentPluginError, match=message):
        ap.read("example-package", skill=skill)


def test_read_reports_an_uninstalled_distribution() -> None:
    with pytest.raises(ap.AgentPluginError, match="is not installed"):
        ap.read("distribution-that-does-not-exist")


def _install_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *skills: str
) -> None:
    dist_info = tmp_path / "example_package-1.2.3.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.4\n"
        "Name: example-package\n"
        "Version: 1.2.3\n"
        "Project-URL: Documentation, https://example.org/docs/\n"
        "Project-URL: Documentation Index, https://example.org/docs/llms.txt\n",
        encoding="utf-8",
    )
    root = tmp_path / "example_package-1.2.3.agent-plugin"
    root.mkdir()
    (root / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                "name": "independent-plugin-name",
            }
        ),
        encoding="utf-8",
    )
    files = ["plugin.json"]
    for name in skills:
        relative = f"skills/{name}/SKILL.md"
        path = root / relative
        path.parent.mkdir(parents=True)
        path.write_text(
            f"---\nname: {name}\ndescription: Use {name}.\n---\n\n"
            f"Use the {name} workflow.\n",
            encoding="utf-8",
        )
        files.append(relative)
    (dist_info / "agent_plugins.json").write_text(
        json.dumps({"root": root.name, "files": files}), encoding="utf-8"
    )
    (tmp_path / "example_package.py").write_text(
        'raise AssertionError("Reading instructions must not import the package")\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
