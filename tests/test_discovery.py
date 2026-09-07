from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

import agent_plugins as ap
from agent_plugins._cli import main


@pytest.mark.parametrize(
    ("first_name", "second_name"),
    [("demo-provider", "demo-provider"), ("Demo.Provider", "demo_provider")],
)
def test_installed_matches_locate_for_shadowed_distributions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    first_name: str,
    second_name: str,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_root = _distribution(first, name=first_name)
    _distribution(second, name=second_name)
    monkeypatch.setattr(sys, "path", [str(first), str(second)])

    assert ap.locate("demo-provider").path == first_root.resolve()
    assert ap.installed() == {first_name: ap.locate("demo-provider")}


def test_unmarked_distribution_shadows_later_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _distribution(first)
    _distribution(second)
    (first / "demo_provider-1.2.3.dist-info" / "agent_plugins.json").unlink()
    monkeypatch.setattr(sys, "path", [str(first), str(second)])

    with pytest.raises(ap.AgentPluginError, match="has no Agent Plugin"):
        ap.locate("demo-provider")
    assert ap.installed() == {}


def test_installed_reports_invalid_marker_in_active_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _distribution(first)
    _distribution(second)
    (first / "demo_provider-1.2.3.dist-info" / "agent_plugins.json").write_text(
        "{", encoding="utf-8"
    )
    monkeypatch.setattr(sys, "path", [str(first), str(second)])

    with pytest.raises(ap.AgentPluginError, match=r"invalid agent_plugins\.json"):
        ap.installed()


def test_installed_and_list_json_expose_absolute_skill_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _distribution(tmp_path, files=("plugin.json", "skills/demo/SKILL.md"))
    skill = root / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: demo\ndescription: Demonstrate the package\n---\n# Demo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    assert ap.installed() == {"demo-provider": ap.Plugin(root)}
    assert main(["list", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == [
        {
            "distribution": "demo-provider",
            "root": str(root.resolve()),
            "skills": [str(skill.resolve())],
        }
    ]


def test_locate_limits_plugin_and_skill_to_packaged_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _distribution(
        tmp_path,
        files=("plugin.json", "skills/demo/SKILL.md"),
    )
    skill_root = root / "skills" / "demo"
    references = skill_root / "references"
    references.mkdir(parents=True)
    instructions = skill_root / "SKILL.md"
    instructions.write_text(
        "---\nname: demo\ndescription: Demonstrate the package\n---\n# Demo\n",
        encoding="utf-8",
    )
    (references / "local.md").write_text("# Local\n", encoding="utf-8")
    (root / "README.md").write_text("# Repository\n", encoding="utf-8")
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    plugin = ap.locate("demo-provider")

    assert plugin.files == ((root / "plugin.json").resolve(), instructions.resolve())
    skill = plugin.skill("demo")
    assert skill.files == (instructions.resolve(),)
    assert skill.tree() == f"{skill.path}{os.sep}\n`-- SKILL.md"
    assert plugin.tree() == "\n".join(
        (
            f"{root.resolve()}{os.sep}",
            "|-- plugin.json",
            "`-- skills/",
            "    `-- demo/",
            "        `-- SKILL.md",
        )
    )


def test_locate_preserves_structural_name_for_contained_skill_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _distribution(
        tmp_path,
        files=("plugin.json", "skills/alias/SKILL.md"),
    )
    target = root / "skills" / "target"
    target.mkdir(parents=True)
    instructions = target / "SKILL.md"
    instructions.write_text(
        "---\nname: target\ndescription: Target\n---\n# Target\n",
        encoding="utf-8",
    )
    try:
        (root / "skills" / "alias").symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    plugin = ap.locate("demo-provider")
    skill = plugin.skill("alias")

    assert skill.path == target.resolve()
    assert skill.file("SKILL.md") == instructions.resolve()


def test_locate_command_prints_the_absolute_root_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _distribution(tmp_path)
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    assert main(["locate", "demo-provider"]) == 0
    assert capsys.readouterr().out == f"{root.resolve()}\n"


def test_locate_tells_the_user_to_reinstall_outdated_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _distribution(tmp_path)
    (tmp_path / "demo_provider-1.2.3.dist-info" / "agent_plugins.json").write_text(
        json.dumps({"root": root.name}), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    with pytest.raises(
        ap.AgentPluginError,
        match=r"outdated Agent Plugin metadata.*Reinstall the distribution",
    ):
        ap.locate("demo-provider")


def test_locate_reports_unusable_marker_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _distribution(tmp_path)
    (tmp_path / "demo_provider-1.2.3.dist-info" / "agent_plugins.json").write_text(
        json.dumps({"root": "bad\0root", "files": ["plugin.json"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    with pytest.raises(ap.AgentPluginError, match="root cannot be resolved"):
        ap.locate("demo-provider")


@pytest.mark.parametrize(
    "marker",
    [
        "{",
        json.dumps({"root": "demo.agent-plugin", "files": "plugin.json"}),
        json.dumps({"root": 1, "files": ["plugin.json"]}),
    ],
)
def test_locate_reports_invalid_marker_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    marker: str,
) -> None:
    _distribution(tmp_path)
    (tmp_path / "demo_provider-1.2.3.dist-info" / "agent_plugins.json").write_text(
        marker,
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "path", [str(tmp_path)])

    with pytest.raises(
        ap.AgentPluginError,
        match=r"has an invalid agent_plugins\.json",
    ):
        ap.locate("demo-provider")


def _distribution(
    tmp_path: Path,
    *,
    files: tuple[str, ...] = ("plugin.json",),
    name: str = "demo-provider",
) -> Path:
    dist_info = tmp_path / "demo_provider-1.2.3.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.4\nName: {name}\nVersion: 1.2.3\n",
        encoding="utf-8",
    )
    root = tmp_path / "demo_provider-1.2.3.agent-plugin"
    root.mkdir()
    (root / "plugin.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (dist_info / "agent_plugins.json").write_text(
        json.dumps({"root": root.name, "files": list(files)}), encoding="utf-8"
    )
    return root
