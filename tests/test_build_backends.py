from __future__ import annotations

import base64
import csv
import hashlib
import importlib
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Protocol, cast

import pytest


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
    backend = _backend(backend_name)
    monkeypatch.chdir(project)

    wheel_directory = tmp_path / "wheel"
    wheel_directory.mkdir()
    wheel = wheel_directory / backend.build_wheel(str(wheel_directory))
    direct_payload = _assert_regular_wheel(wheel)

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
    assert _assert_regular_wheel(rebuilt) == direct_payload

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
    _assert_record(editable)


def _assert_regular_wheel(wheel: Path) -> dict[str, bytes]:
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
        assert (
            archive.getinfo(f"{prefix}/bin/server.py").external_attr >> 16 == 0o100755
        )
        payload = {
            name.removeprefix(f"{prefix}/"): archive.read(name)
            for name in archive.namelist()
            if name.startswith(f"{prefix}/")
        }
    assert payload.keys() == expected
    _assert_record(wheel)
    return payload


def _assert_record(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        dist_info = _dist_info(archive)
        record_name = f"{dist_info}/RECORD"
        rows = list(csv.reader(archive.read(record_name).decode().splitlines()))
        files = {name for name in archive.namelist() if not name.endswith("/")}
        assert {row[0] for row in rows} == files
        for name, digest, size in rows:
            if name == record_name:
                assert (digest, size) == ("", "")
                continue
            value = archive.read(name)
            encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest())
            assert digest == f"sha256={encoded.rstrip(b'=').decode()}"
            assert size == str(len(value))


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
include = ["bin/**"]
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
    server = binary / "server.py"
    server.write_text("print('demo')\n", encoding="utf-8")
    server.chmod(0o755)
    return project, root
