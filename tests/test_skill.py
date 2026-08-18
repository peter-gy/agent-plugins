from __future__ import annotations

import os
from html import escape
from pathlib import Path

import pytest

import agent_plugins as ap


def test_skill_exposes_its_directory_and_nested_files(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)

    skill = ap.Skill(root)

    assert skill.path == root.resolve()
    assert Path(skill) == root.resolve()
    assert os.fspath(skill) == str(root.resolve())
    assert skill / "SKILL.md" == (root / "SKILL.md").resolve()
    assert (
        skill / "references" / "guide&notes.md"
        == (root / "references" / "guide&notes.md").resolve()
    )
    assert skill.files == tuple(
        path.resolve()
        for path in (
            root / "agents" / "openai.yaml",
            root / "references" / "guide&notes.md",
            root / "scripts" / "inspect.py",
            root / "SKILL.md",
        )
    )
    with pytest.raises(AttributeError):
        skill.__setattr__("path", tmp_path / "other")


def test_skill_tree_drives_text_and_notebook_display(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    skill = ap.Skill(root)
    expected = "\n".join(
        (
            f"{root.resolve()}{os.sep}",
            "|-- agents/",
            "|   `-- openai.yaml",
            "|-- references/",
            "|   `-- guide&notes.md",
            "|-- scripts/",
            "|   `-- inspect.py",
            "`-- SKILL.md",
        )
    )

    assert skill.tree() == expected
    assert str(skill) == expected
    assert repr(skill) == expected
    assert skill._repr_html_() == f"<pre>{escape(expected)}</pre>"
    assert skill.tree(max_depth=1) == "\n".join(
        (
            f"{root.resolve()}{os.sep}",
            "|-- agents/",
            "|   `-- ...",
            "|-- references/",
            "|   `-- ...",
            "|-- scripts/",
            "|   `-- ...",
            "`-- SKILL.md",
        )
    )
    assert skill.tree(max_files=1).endswith("... 3 more files")


def test_skill_lazily_splits_and_caches_its_source_text(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    skill = ap.Skill(root)

    assert "SKILL.md" in skill.tree()
    _write_skill(
        root,
        b"---\r\nname: first\r\ndescription: First version\r\n---\r\n\r\n# First\r\n",
    )

    assert skill.frontmatter == "name: first\r\ndescription: First version\r\n"
    assert skill.body == "\r\n# First\r\n"

    _write_skill(
        root,
        b"---\nname: second\ndescription: Second version\n---\n# Second\n",
    )
    assert skill.frontmatter == "name: first\r\ndescription: First version\r\n"
    assert skill.body == "\r\n# First\r\n"

    refreshed = ap.Skill(root)
    assert refreshed.frontmatter == "name: second\ndescription: Second version\n"
    assert refreshed.body == "# Second\n"


def test_skill_preserves_frontmatter_as_text(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    _write_skill(
        root,
        b"---\ncustom: [source, text]\nunknown: {nested: true}\n---\nBody\n",
    )

    skill = ap.Skill(root)

    assert skill.frontmatter == ("custom: [source, text]\nunknown: {nested: true}\n")
    assert skill.body == "Body\n"


def test_skill_allows_an_empty_markdown_body(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    _write_skill(
        root,
        b"---\nname: demo\ndescription: Demonstrate the package\n---",
    )

    skill = ap.Skill(root)

    assert skill.frontmatter == ("name: demo\ndescription: Demonstrate the package\n")
    assert skill.body == ""


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (b"# Demo\n", "must begin with a --- frontmatter delimiter"),
        (b"---\nname: demo\n", "frontmatter must end with a --- delimiter"),
        (b"\xff", "must contain UTF-8 text"),
    ],
)
def test_skill_reports_structural_document_errors(
    tmp_path: Path,
    source: bytes,
    message: str,
) -> None:
    root = _skill_root(tmp_path)
    _write_skill(root, source)

    with pytest.raises(ap.ValidationError, match=message) as captured:
        _frontmatter = ap.Skill(root).frontmatter

    assert captured.value.path == (root / "SKILL.md").resolve()
    assert captured.value.issues


def test_skill_caches_structural_errors(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    _write_skill(root, b"# Demo\n")
    skill = ap.Skill(root)

    with pytest.raises(ap.ValidationError) as first:
        _body = skill.body

    _write_skill(
        root,
        b"---\nname: repaired\ndescription: Repaired\n---\n# Repaired\n",
    )
    with pytest.raises(ap.ValidationError) as second:
        _body = skill.body

    assert first.value is second.value
    assert ap.Skill(root).body == "# Repaired\n"


def test_skill_requires_exact_uppercase_instruction_file(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    root.mkdir()
    (root / "skill.md").write_text("# Demo\n", encoding="utf-8")

    with pytest.raises(ap.AgentPluginError, match=r"must include SKILL\.md"):
        ap.Skill(root)


def test_skill_rejects_files_that_escape_its_root(tmp_path: Path) -> None:
    root = _skill_root(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    (root / "references" / "outside.md").symlink_to(outside)

    with pytest.raises(ap.AgentPluginError, match="file cannot be resolved"):
        ap.Skill(root)


def _skill_root(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    (root / "agents").mkdir(parents=True)
    (root / "references").mkdir()
    (root / "scripts").mkdir()
    _write_skill(
        root,
        b"---\nname: demo\ndescription: Demonstrate the package\n---\n\n# Demo\n",
    )
    (root / "agents" / "openai.yaml").write_text("interface: {}\n", encoding="utf-8")
    (root / "references" / "guide&notes.md").write_text("# Guide\n", encoding="utf-8")
    (root / "scripts" / "inspect.py").write_text("print('demo')\n", encoding="utf-8")
    return root


def _write_skill(root: Path, source: bytes) -> None:
    (root / "SKILL.md").write_bytes(source)
