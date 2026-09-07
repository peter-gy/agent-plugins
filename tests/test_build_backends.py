from __future__ import annotations

import importlib
import json
import stat
import tarfile
import zipfile
from pathlib import Path
from typing import Protocol, cast

import pytest
from wheel_assertions import assert_wheel_record

import agent_plugins as ap
from agent_plugins._build.sdist import write_sdist_plugin


class _Backend(Protocol):
    def build_wheel(self, wheel_directory: str) -> str: ...

    def build_sdist(self, sdist_directory: str) -> str: ...

    def build_editable(self, wheel_directory: str) -> str: ...


@pytest.mark.parametrize("backend_name", ["uv_build", "hatchling"])
def test_backend_builds_regular_sdist_and_editable_plugins(
    backend_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, plugin_root = _project(tmp_path, backend_name)
    executable_mode = stat.S_IFREG | stat.S_IMODE(
        (plugin_root / "bin/server.py").stat().st_mode
    )
    backend = _backend(backend_name)
    monkeypatch.chdir(project)

    wheel_directory = tmp_path / "wheel"
    wheel_directory.mkdir()
    wheel = wheel_directory / backend.build_wheel(str(wheel_directory))
    direct_payload = _assert_regular_wheel(wheel, executable_mode=executable_mode)

    plain_directory = tmp_path / "plain"
    plain_directory.mkdir()
    delegate_name = "uv_build" if backend_name == "uv_build" else "hatchling.build"
    delegate = cast(_Backend, importlib.import_module(delegate_name))
    plain_wheel = plain_directory / delegate.build_wheel(str(plain_directory))
    ap.attach_wheel(plain_wheel, plan=ap.build_plan(project))
    assert (
        _assert_regular_wheel(plain_wheel, executable_mode=executable_mode)
        == direct_payload
    )

    sdist_directory = tmp_path / "sdist"
    sdist_directory.mkdir()
    sdist = sdist_directory / backend.build_sdist(str(sdist_directory))
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
        extracted = tmp_path / "extracted"
        archive.extractall(extracted, filter="data")
    assert any(name.endswith("/.agent-plugin/skills/demo/SKILL.md") for name in names)

    source_project = next(extracted.iterdir())
    monkeypatch.chdir(source_project)
    rebuilt_directory = tmp_path / "rebuilt"
    rebuilt_directory.mkdir()
    rebuilt = rebuilt_directory / backend.build_wheel(str(rebuilt_directory))
    assert (
        _assert_regular_wheel(rebuilt, executable_mode=executable_mode)
        == direct_payload
    )

    monkeypatch.chdir(project)
    editable_directory = tmp_path / "editable"
    editable_directory.mkdir()
    editable = editable_directory / backend.build_editable(str(editable_directory))
    with zipfile.ZipFile(editable) as archive:
        dist_info = _dist_info(archive)
        marker = json.loads(archive.read(f"{dist_info}/agent_plugins.json"))
        assert marker == {
            "root": str(plugin_root.resolve()),
            "files": [
                "bin/server.py",
                "mcp.json",
                "plugin.json",
                "skills/demo/SKILL.md",
                "skills/demo/references/guide.md",
            ],
        }
        assert not any(
            name.startswith("demo_provider-1.2.3.agent-plugin/")
            for name in archive.namelist()
        )
    assert_wheel_record(editable)


def test_sdist_rewrite_preserves_outer_mode(tmp_path: Path) -> None:
    project, _root = _project(tmp_path, "uv_build")
    source = tmp_path / "demo-provider-1.2.3.tar.gz"
    content = tmp_path / "PKG-INFO"
    content.write_text("Metadata-Version: 2.4\n", encoding="utf-8")
    with tarfile.open(source, "w:gz") as archive:
        archive.add(content, "demo-provider-1.2.3/PKG-INFO")
    source.chmod(0o664)
    source_mode = stat.S_IMODE(source.stat().st_mode)

    write_sdist_plugin(source, ap.build_plan(project))

    assert stat.S_IMODE(source.stat().st_mode) == source_mode


def test_sdist_rewrite_replaces_the_canonical_staged_inventory(
    tmp_path: Path,
) -> None:
    project, _root = _project(tmp_path, "uv_build")
    source = tmp_path / "demo-provider-1.2.3.tar.gz"
    archive_root = "demo-provider-1.2.3"
    content = tmp_path / "content.txt"
    content.write_text("source bytes\n", encoding="utf-8")
    stage = f"./{archive_root}//.agent-plugin"
    with tarfile.open(source, "w:gz") as archive:
        archive.add(content, f"{stage}/skills/previous/SKILL.md")
        archive.add(content, f"./{archive_root}/original.txt")
        archive.add(project / "pyproject.toml", f"{archive_root}/pyproject.toml")

    expected = ap.build_plan(project)
    write_sdist_plugin(source, expected)

    extracted = tmp_path / "extracted"
    with tarfile.open(source, "r:gz") as archive:
        archive.extractall(extracted, filter="data")
    rebuilt = ap.Plugin(extracted / archive_root / ".agent-plugin")
    assert {path.relative_to(rebuilt.path).as_posix() for path in rebuilt.files} == {
        "bin/server.py",
        "mcp.json",
        "plugin.json",
        "skills/demo/SKILL.md",
        "skills/demo/references/guide.md",
    }
    assert (extracted / archive_root / "original.txt").read_bytes() == (
        content.read_bytes()
    )


def _assert_regular_wheel(wheel: Path, *, executable_mode: int) -> dict[str, bytes]:
    prefix = "demo_provider-1.2.3.agent-plugin"
    expected = {
        "bin/server.py",
        "mcp.json",
        "plugin.json",
        "skills/demo/SKILL.md",
        "skills/demo/references/guide.md",
    }
    with zipfile.ZipFile(wheel) as archive:
        dist_info = _dist_info(archive)
        marker = json.loads(archive.read(f"{dist_info}/agent_plugins.json"))
        metadata = archive.read(f"{dist_info}/METADATA").decode()
        assert "Requires-Dist: agent-plugins" not in metadata
        assert marker == {"root": prefix, "files": sorted(expected)}
        assert archive.getinfo(f"{prefix}/bin/server.py").external_attr >> 16 == (
            executable_mode
        )
        payload = {
            name.removeprefix(f"{prefix}/"): archive.read(name)
            for name in archive.namelist()
            if name.startswith(f"{prefix}/")
        }
    assert payload.keys() == expected
    assert_wheel_record(wheel)
    return payload


def _dist_info(archive: zipfile.ZipFile) -> str:
    return next(
        name.removesuffix("/WHEEL")
        for name in archive.namelist()
        if name.endswith(".dist-info/WHEEL")
    )


def _backend(name: str) -> _Backend:
    module = importlib.import_module(f"agent_plugins.build.{name}")
    return cast(_Backend, module)


def _project(tmp_path: Path, backend: str) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    project = root / "packages" / "demo-provider"
    package = project / "src" / "demo_provider"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")

    backend_requirement = (
        "uv_build==0.12.2" if backend == "uv_build" else "hatchling==1.31.0"
    )
    (project / "pyproject.toml").write_text(
        f"""\
[build-system]
requires = ["{backend_requirement}"]
build-backend = "agent_plugins.build.{backend}"

[project]
name = "demo-provider"
version = "1.2.3"
requires-python = ">=3.10"

[tool.hatch.build.targets.wheel]
packages = ["src/demo_provider"]

[tool.agent-plugins]
root = "../.."
include = ["bin/**", "empty-assets/**"]
""",
        encoding="utf-8",
    )

    (root / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                "name": "demo",
            }
        ),
        encoding="utf-8",
    )
    (root / "mcp.json").write_text('{"mcpServers":{}}\n', encoding="utf-8")
    skill = root / "skills" / "demo"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demonstrate the package\n---\n# Demo\n",
        encoding="utf-8",
    )
    (skill / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    binary = root / "bin"
    binary.mkdir()
    (root / "empty-assets").mkdir()
    server = binary / "server.py"
    server.write_text("print('demo')\n", encoding="utf-8")
    server.chmod(0o755)
    return project, root
