from __future__ import annotations

import json
import os
from importlib import metadata
from pathlib import Path

import pytest

import agent_plugins as ap
from agent_plugins._cli import main


def test_locate_returns_the_installed_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    distribution, root = _distribution(tmp_path)
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distribution",
        lambda _name: distribution,
    )

    plugin = ap.locate("demo-provider")

    assert plugin == ap.Plugin(root)
    assert plugin.path == root.resolve()


def test_installed_and_list_json_expose_absolute_skill_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    distribution, root = _distribution(
        tmp_path, files=("plugin.json", "skills/demo/SKILL.md")
    )
    skill = root / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: demo\ndescription: Demonstrate the package\n---\n# Demo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distributions",
        lambda: iter((distribution,)),
    )

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


def test_locate_limits_each_skill_to_packaged_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    distribution, root = _distribution(
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
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distribution",
        lambda _name: distribution,
    )

    plugin = ap.locate("demo-provider")

    assert len(plugin.skills) == 1
    assert plugin.skills[0].files == (instructions.resolve(),)
    assert "local.md" not in plugin.skills[0].tree()


def test_locate_limits_the_tree_to_packaged_plugin_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    distribution, root = _distribution(tmp_path)
    (root / "README.md").write_text("# Repository\n", encoding="utf-8")
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distribution",
        lambda _name: distribution,
    )

    plugin = ap.locate("demo-provider")

    assert plugin.files == ((root / "plugin.json").resolve(),)
    assert plugin.tree() == f"{root.resolve()}{os.sep}\n`-- plugin.json"


def test_locate_command_prints_the_absolute_root_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    distribution, root = _distribution(tmp_path)
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distribution",
        lambda _name: distribution,
    )

    assert main(["locate", "demo-provider"]) == 0
    assert capsys.readouterr().out == f"{root.resolve()}\n"


def test_locate_reports_a_distribution_without_a_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dist_info = tmp_path / "demo_provider-1.2.3.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.4\nName: demo-provider\nVersion: 1.2.3\n",
        encoding="utf-8",
    )
    distribution = metadata.PathDistribution(dist_info)
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distribution",
        lambda _name: distribution,
    )

    with pytest.raises(ap.AgentPluginError, match="has no Agent Plugin"):
        ap.locate("demo-provider")


def test_locate_tells_the_user_to_reinstall_outdated_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    distribution, root = _distribution(tmp_path)
    (tmp_path / "demo_provider-1.2.3.dist-info" / "agent_plugins.json").write_text(
        json.dumps({"root": root.name}), encoding="utf-8"
    )
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distribution",
        lambda _name: distribution,
    )

    with pytest.raises(
        ap.AgentPluginError,
        match=r"outdated Agent Plugin metadata.*Reinstall the distribution",
    ):
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
    distribution, _root = _distribution(tmp_path)
    (tmp_path / "demo_provider-1.2.3.dist-info" / "agent_plugins.json").write_text(
        marker,
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "agent_plugins._discovery.metadata.distribution",
        lambda _name: distribution,
    )

    with pytest.raises(
        ap.AgentPluginError,
        match=r"has an invalid agent_plugins\.json",
    ):
        ap.locate("demo-provider")


def _distribution(
    tmp_path: Path, *, files: tuple[str, ...] = ("plugin.json",)
) -> tuple[metadata.Distribution, Path]:
    dist_info = tmp_path / "demo_provider-1.2.3.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.4\nName: demo-provider\nVersion: 1.2.3\n",
        encoding="utf-8",
    )
    root = tmp_path / "demo_provider-1.2.3.agent-plugin"
    root.mkdir()
    (root / "plugin.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (dist_info / "agent_plugins.json").write_text(
        json.dumps({"root": root.name, "files": list(files)}), encoding="utf-8"
    )
    return metadata.PathDistribution(dist_info), root
