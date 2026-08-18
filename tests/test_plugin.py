from __future__ import annotations

import os
from html import escape
from pathlib import Path

import pytest

import agent_plugins as ap


def test_plugin_exposes_absolute_component_paths(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)

    plugin = ap.Plugin(root)

    assert plugin.path == root.resolve()
    assert isinstance(plugin.manifest, ap.Manifest)
    assert plugin.manifest.path == (root / "plugin.json").resolve()
    assert plugin.files == tuple(
        path.resolve()
        for path in (
            root / "mcp.json",
            root / "plugin.json",
            root / "skills" / "demo" / "references" / "guide&notes.md",
            root / "skills" / "demo" / "SKILL.md",
        )
    )
    assert plugin.skills == (ap.Skill(root / "skills" / "demo"),)
    assert plugin.skills is plugin.skills
    assert plugin.skills[0].path == (root / "skills" / "demo").resolve()
    assert plugin.skills[0].frontmatter == (
        "name: demo\ndescription: Demonstrate the package\n"
    )
    assert plugin.skills[0].body == "\n# Demo\n"
    assert isinstance(plugin.mcp, ap.MCPConfig)
    assert plugin.mcp.path == (root / "mcp.json").resolve()
    assert plugin.manifest is plugin.manifest
    assert plugin.mcp is plugin.mcp
    assert os.fspath(plugin) == str(root.resolve())
    assert Path(plugin) == root.resolve()


def test_plugin_tree_drives_text_and_notebook_display(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    plugin = ap.Plugin(root)
    expected = "\n".join(
        (
            f"{root.resolve()}{os.sep}",
            "|-- mcp.json",
            "|-- plugin.json",
            "`-- skills/",
            "    `-- demo/",
            "        |-- references/",
            "        |   `-- guide&notes.md",
            "        `-- SKILL.md",
        )
    )

    assert plugin.tree() == expected
    assert str(plugin) == expected
    assert repr(plugin) == expected
    assert plugin._repr_html_() == f"<pre>{escape(expected)}</pre>"


def test_plugin_tree_can_limit_progressive_disclosure(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    plugin = ap.Plugin(root)

    assert plugin.tree(max_depth=2) == "\n".join(
        (
            f"{root.resolve()}{os.sep}",
            "|-- mcp.json",
            "|-- plugin.json",
            "`-- skills/",
            "    `-- demo/",
            "        `-- ...",
        )
    )
    assert plugin.tree(max_files=2) == "\n".join(
        (
            f"{root.resolve()}{os.sep}",
            "|-- mcp.json",
            "`-- plugin.json",
            "... 2 more files",
        )
    )
    with pytest.raises(ValueError, match="max_depth must be zero or greater"):
        plugin.tree(max_depth=-1)
    with pytest.raises(ValueError, match="max_files must be zero or greater"):
        plugin.tree(max_files=-1)


def test_plugin_default_tree_limits_depth(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    deep = root / "skills" / "demo" / "references" / "topic" / "examples"
    deep.mkdir(parents=True)
    (deep / "walkthrough.md").write_text("# Walkthrough\n", encoding="utf-8")
    plugin = ap.Plugin(root)

    assert "        |   `-- topic/\n        |       `-- ..." in plugin.tree()
    assert "walkthrough.md" in plugin.tree(max_depth=None)


def test_plugin_default_tree_limits_file_count(tmp_path: Path) -> None:
    root = tmp_path / "large.agent-plugin"
    root.mkdir()
    (root / "plugin.json").write_text('{"name":"large"}\n', encoding="utf-8")
    for index in range(100):
        (root / f"reference-{index:03}.md").write_text(
            "# Reference\n", encoding="utf-8"
        )

    assert ap.Plugin(root).tree().endswith("... 1 more file")


def test_plugin_requires_a_manifest(tmp_path: Path) -> None:
    with pytest.raises(ap.AgentPluginError, match=r"must include plugin\.json"):
        ap.Plugin(tmp_path)


def test_plugin_reports_a_file_as_an_invalid_root(tmp_path: Path) -> None:
    path = tmp_path / "plugin.json"
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ap.AgentPluginError, match="root is invalid"):
        ap.Plugin(path)


def test_plugin_mcp_is_none_when_configuration_is_absent(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path)
    (root / "mcp.json").unlink()

    assert ap.Plugin(root).mcp is None


def _plugin_root(tmp_path: Path) -> Path:
    root = tmp_path / "demo.agent-plugin"
    skill = root / "skills" / "demo"
    references = skill / "references"
    references.mkdir(parents=True)
    (root / "plugin.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (root / "mcp.json").write_text('{"mcpServers":{}}\n', encoding="utf-8")
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demonstrate the package\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    (references / "guide&notes.md").write_text("# Guide\n", encoding="utf-8")
    return root
