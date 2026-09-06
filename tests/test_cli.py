from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from agent_plugins._cli import main

DIST_INFO = "demo-1.0.0.dist-info"
WHEEL_NAME = "demo-1.0.0-py3-none-any.whl"


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
