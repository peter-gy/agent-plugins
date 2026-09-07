from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path, PurePosixPath
from typing import IO, Any

import pytest
from wheel_assertions import assert_wheel_record

import agent_plugins as ap

DIST_INFO = "demo-1.0.0.dist-info"
PLUGIN_ROOT = "demo-1.0.0.agent-plugin"
WHEEL_NAME = "demo-1.0.0-py3-none-any.whl"


def test_attach_wheel_reads_current_project_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, root = _project(tmp_path)
    wheel = _wheel(tmp_path / WHEEL_NAME)
    monkeypatch.chdir(project)

    result = ap.attach_wheel(wheel)

    assert result.files == (
        PurePosixPath("plugin.json"),
        PurePosixPath("skills/demo/SKILL.md"),
    )
    with zipfile.ZipFile(wheel) as archive:
        assert (
            archive.read(f"{PLUGIN_ROOT}/plugin.json")
            == (root / "plugin.json").read_bytes()
        )


def test_attach_wheel_reads_explicit_project_configuration(tmp_path: Path) -> None:
    project, _root = _project(tmp_path)
    wheel = _wheel(tmp_path / WHEEL_NAME)

    result = ap.attach_wheel(wheel, project=project)

    assert result.files == (
        PurePosixPath("plugin.json"),
        PurePosixPath("skills/demo/SKILL.md"),
    )


def test_attach_wheel_uses_supplied_plan_without_project_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path, ("plugin.json", "bin/server.py"))
    wheel = _wheel(tmp_path / WHEEL_NAME)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)

    result = ap.attach_wheel(wheel, plan=plan)

    assert result.files == (
        PurePosixPath("plugin.json"),
        PurePosixPath("bin/server.py"),
    )
    with zipfile.ZipFile(wheel) as archive:
        marker = json.loads(archive.read(f"{DIST_INFO}/agent_plugins.json"))
    assert marker["files"] == ["plugin.json", "bin/server.py"]


def test_attach_wheel_rejects_project_and_plan_before_mutation(tmp_path: Path) -> None:
    project, _root = _project(tmp_path)
    plan = ap.build_plan(project)
    wheel = _wheel(tmp_path / WHEEL_NAME)
    original = wheel.read_bytes()

    with pytest.raises(ap.AgentPluginError, match="either project or plan"):
        ap.attach_wheel(wheel, project=project, plan=plan)

    assert wheel.read_bytes() == original


def test_planning_failure_preserves_input_and_creates_no_temporary_file(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_bytes(b"\xff")
    wheel = _wheel(tmp_path / WHEEL_NAME)
    original = wheel.read_bytes()
    entries = set(tmp_path.iterdir())

    with pytest.raises(ap.AgentPluginError, match="Cannot read project configuration"):
        ap.attach_wheel(wheel, project=project)

    assert wheel.read_bytes() == original
    assert set(tmp_path.iterdir()) == entries


def test_in_place_attachment_returns_resolved_artifact_details(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ("plugin.json", "bin/server.py"))
    wheel = _wheel(
        tmp_path / WHEEL_NAME,
        extra_members={
            f"{DIST_INFO}/RECORD.jws": b"jws",
            f"{DIST_INFO}/RECORD.p7s": b"p7s",
        },
    )

    result = ap.attach_wheel(wheel, plan=plan)

    assert result == ap.WheelAttachment(
        source=wheel.resolve(),
        output=wheel.resolve(),
        dist_info=PurePosixPath(DIST_INFO),
        plugin_root=PurePosixPath(PLUGIN_ROOT),
        files=(PurePosixPath("plugin.json"), PurePosixPath("bin/server.py")),
        replaced_existing_plugin=False,
        removed_signatures=(
            PurePosixPath(f"{DIST_INFO}/RECORD.jws"),
            PurePosixPath(f"{DIST_INFO}/RECORD.p7s"),
        ),
    )
    with zipfile.ZipFile(wheel) as archive:
        assert f"{DIST_INFO}/RECORD.jws" not in archive.namelist()
        assert f"{DIST_INFO}/RECORD.p7s" not in archive.namelist()
    assert_wheel_record(wheel)


def test_output_directory_preserves_source_and_refuses_overwrite(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path, ("plugin.json",))
    wheel = _wheel(tmp_path / WHEEL_NAME)
    wheel.chmod(0o640)
    wheel_mode = stat.S_IMODE(wheel.stat().st_mode)
    original = wheel.read_bytes()
    output_dir = tmp_path / "attached"
    output_dir.mkdir()

    result = ap.attach_wheel(wheel, plan=plan, output_dir=output_dir)

    assert result.source == wheel.resolve()
    assert result.output == (output_dir / wheel.name).resolve()
    assert stat.S_IMODE(result.output.stat().st_mode) == wheel_mode
    assert wheel.read_bytes() == original
    attached = result.output.read_bytes()

    with pytest.raises(ap.AgentPluginError, match="already exists"):
        ap.attach_wheel(wheel, plan=plan, output_dir=output_dir)

    assert wheel.read_bytes() == original
    assert result.output.read_bytes() == attached


def test_output_directory_works_without_hard_link_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path, ("plugin.json",))
    wheel = _wheel(tmp_path / WHEEL_NAME)
    output_dir = tmp_path / "attached"
    output_dir.mkdir()

    def fail_link(_source: Path, _output: Path) -> None:
        raise OSError("hard links unavailable")

    monkeypatch.setattr(os, "link", fail_link)

    result = ap.attach_wheel(wheel, plan=plan, output_dir=output_dir)

    with zipfile.ZipFile(result.output) as archive:
        marker = json.loads(archive.read(f"{DIST_INFO}/agent_plugins.json"))
        assert marker["files"] == ["plugin.json"]
        assert archive.read(f"{PLUGIN_ROOT}/plugin.json") == (
            plan.files[0].source.read_bytes()
        )


def test_repeated_attachment_replaces_owned_payload_deterministically(
    tmp_path: Path,
) -> None:
    wheel = _wheel(
        tmp_path / WHEEL_NAME,
        extra_members={f"{PLUGIN_ROOT}-copy/keep.txt": b"keep"},
    )
    first_plan = _plan(tmp_path / "first", ("plugin.json", "old.txt"))
    second_plan = _plan(tmp_path / "second", ("plugin.json",))

    first = ap.attach_wheel(wheel, plan=first_plan)
    second = ap.attach_wheel(wheel, plan=second_plan)
    stable = wheel.read_bytes()
    third = ap.attach_wheel(wheel, plan=second_plan)

    assert first.replaced_existing_plugin is False
    assert second.replaced_existing_plugin is True
    assert third.replaced_existing_plugin is True
    assert wheel.read_bytes() == stable
    with zipfile.ZipFile(wheel) as archive:
        assert f"{PLUGIN_ROOT}/old.txt" not in archive.namelist()
        assert archive.read(f"{PLUGIN_ROOT}-copy/keep.txt") == b"keep"


@pytest.mark.parametrize(
    "owned_member",
    [f"{DIST_INFO}/agent_plugins.json", f"{PLUGIN_ROOT}/plugin.json"],
)
def test_existing_marker_or_payload_reports_replacement(
    tmp_path: Path, owned_member: str
) -> None:
    wheel = _wheel(tmp_path / WHEEL_NAME, extra_members={owned_member: b"old"})

    result = ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))

    assert result.replaced_existing_plugin is True


@pytest.mark.parametrize("scheme", ["purelib", "platlib"])
def test_attachment_installs_selected_payload_over_relocated_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scheme: str
) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required for wheel installation")
    plan = _plan(tmp_path, ("plugin.json",))
    plan.files[0].source.write_text(
        json.dumps(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                "name": "selected-plugin",
            }
        ),
        encoding="utf-8",
    )
    prefix = f"demo-1.0.0.data/{scheme}"
    wheel = _wheel(
        tmp_path / WHEEL_NAME,
        extra_members={
            f"{DIST_INFO}/WHEEL": (
                "Wheel-Version: 1.0\n"
                f"Root-Is-Purelib: {str(scheme == 'purelib').lower()}\n"
                "Tag: py3-none-any\n"
            ).encode(),
            f"{prefix}/{PLUGIN_ROOT}/plugin.json": b'{"name":"stale"}',
            f"{prefix}/{PLUGIN_ROOT}/old.txt": b"stale resource",
            f"{prefix}/{DIST_INFO}/agent_plugins.json": b"stale marker",
            f"{prefix}/{DIST_INFO}/RECORD.jws": b"stale signature",
            f"{prefix}/demo_resource.txt": b"library resource",
        },
    )

    result = ap.attach_wheel(wheel, plan=plan)
    installed = tmp_path / "installed"
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--python",
            sys.executable,
            "--target",
            str(installed),
            "--no-deps",
            str(wheel),
        ],
        env={**os.environ, "UV_CACHE_DIR": str(tmp_path / "uv-cache")},
        check=True,
        timeout=60,
        capture_output=True,
        text=True,
    )
    monkeypatch.syspath_prepend(str(installed))

    plugin = ap.locate("demo")
    assert plugin.manifest.name == "selected-plugin"
    assert tuple(path.relative_to(plugin.path).as_posix() for path in plugin.files) == (
        "plugin.json",
    )
    assert {path.name for path in plugin.path.iterdir()} == {"plugin.json"}
    assert (installed / "demo_resource.txt").read_bytes() == b"library resource"
    assert result.replaced_existing_plugin is True
    assert result.removed_signatures == (
        PurePosixPath(f"{prefix}/{DIST_INFO}/RECORD.jws"),
    )
    assert_wheel_record(wheel)


def test_attachment_rejects_relocated_distribution_metadata(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / WHEEL_NAME,
        extra_members={
            f"demo-1.0.0.data/purelib/{DIST_INFO}/METADATA": (
                b"Metadata-Version: 2.4\nName: demo\nVersion: 9.0.0\n"
            ),
        },
    )
    original = wheel.read_bytes()

    with pytest.raises(ap.AgentPluginError, match="relocated distribution metadata"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))

    assert wheel.read_bytes() == original


def test_attachment_preserves_archive_metadata_modes_and_record(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ("plugin.json", "bin/server.py"))
    server = plan.files[1].source
    server.chmod(0o755)
    server_mode = stat.S_IMODE(server.stat().st_mode)
    wheel = _wheel(tmp_path / WHEEL_NAME, archive_comment=b"release artifact")
    wheel.chmod(0o664)
    wheel_mode = stat.S_IMODE(wheel.stat().st_mode)
    with zipfile.ZipFile(wheel) as archive:
        original_info = archive.getinfo("demo/__init__.py")
        original_directory_info = archive.getinfo("demo/data/")
        original_bytes = archive.read("demo/__init__.py")

    result = ap.attach_wheel(wheel, plan=plan)

    assert stat.S_IMODE(wheel.stat().st_mode) == wheel_mode
    with zipfile.ZipFile(wheel) as archive:
        copied_info = archive.getinfo("demo/__init__.py")
        assert archive.comment == b"release artifact"
        assert archive.read("demo/__init__.py") == original_bytes
        assert _metadata(copied_info) == _metadata(original_info)
        assert _metadata(archive.getinfo("demo/data/")) == _metadata(
            original_directory_info
        )
        assert archive.getinfo(f"{PLUGIN_ROOT}/bin/server.py").external_attr >> 16 == (
            stat.S_IFREG | server_mode
        )
    assert result.removed_signatures == ()
    assert_wheel_record(wheel)


@pytest.mark.parametrize(
    "member",
    [
        "/absolute.py",
        "C:drive-relative.py",
        "demo/../outside.py",
        "demo\\outside.py",
        "demo/name\x00suffix.py",
    ],
)
def test_attach_wheel_rejects_unsafe_members(tmp_path: Path, member: str) -> None:
    stored_member = member.replace("\x00", "?")
    wheel = _wheel(tmp_path / WHEEL_NAME, extra_members={stored_member: b"unsafe"})
    if "\x00" in member:
        wheel.write_bytes(
            wheel.read_bytes().replace(stored_member.encode(), member.encode())
        )
    if "\\" in member:
        contents = wheel.read_bytes()
        normalized = member.replace("\\", "/").encode()
        if member.encode() not in contents:
            assert normalized in contents
            wheel.write_bytes(contents.replace(normalized, member.encode()))
    original = wheel.read_bytes()

    with pytest.raises(ap.AgentPluginError, match="unsafe archive member"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))

    assert wheel.read_bytes() == original


def test_attach_wheel_rejects_duplicate_members(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / WHEEL_NAME)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(wheel, "a") as archive:
            archive.writestr("demo/__init__.py", b"duplicate")
    original = wheel.read_bytes()

    with pytest.raises(ap.AgentPluginError, match="duplicate archive member"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))

    assert wheel.read_bytes() == original


@pytest.mark.parametrize("required", ["METADATA", "RECORD"])
def test_attach_wheel_requires_dist_info_files(tmp_path: Path, required: str) -> None:
    wheel = _wheel(tmp_path / WHEEL_NAME, omit={required})

    with pytest.raises(ap.AgentPluginError, match=rf"missing .*{required}"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))


@pytest.mark.parametrize("wheel_count", [0, 2])
def test_attach_wheel_requires_one_dist_info_wheel(
    tmp_path: Path, wheel_count: int
) -> None:
    omit = {"WHEEL"} if wheel_count == 0 else set()
    extra = (
        {"other-2.0.0.dist-info/WHEEL": b"Wheel-Version: 1.0\n"}
        if wheel_count == 2
        else None
    )
    wheel = _wheel(tmp_path / WHEEL_NAME, omit=omit, extra_members=extra)

    with pytest.raises(ap.AgentPluginError, match="exactly one"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))


@pytest.mark.parametrize(
    "alias",
    [
        f"{DIST_INFO}/WHEEL/",
        f"{DIST_INFO}/./WHEEL",
    ],
)
def test_attach_wheel_rejects_noncanonical_wheel_members(
    tmp_path: Path, alias: str
) -> None:
    wheel = _wheel(
        tmp_path / WHEEL_NAME,
        omit={"WHEEL"},
        extra_members={alias: b"Wheel-Version: 1.0\n"},
    )

    with pytest.raises(ap.AgentPluginError, match=r"exactly one|unsafe archive"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))


def test_attach_wheel_reports_missing_corrupt_and_non_wheel_inputs(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path, ("plugin.json",))
    missing = tmp_path / "missing.whl"
    corrupt = tmp_path / WHEEL_NAME
    corrupt.write_bytes(b"not a zip")
    text = tmp_path / "artifact.zip"
    text.write_bytes(b"zip")

    with pytest.raises(ap.AgentPluginError, match="cannot be read"):
        ap.attach_wheel(missing, plan=plan)
    with pytest.raises(ap.AgentPluginError, match="corrupt"):
        ap.attach_wheel(corrupt, plan=plan)
    with pytest.raises(ap.AgentPluginError, match=r"must end in \.whl"):
        ap.attach_wheel(text, plan=plan)


@pytest.mark.parametrize(
    ("targets", "message"),
    [
        (("../plugin.json",), "plugin root"),
        (("C:plugin.json",), "plugin root"),
        (("plugin.json", "plugin.json"), "duplicate target"),
        (("assets", "assets/icon.svg"), "file-directory target collisions"),
        (("plugin.json", "assets/name\x00suffix.txt"), "plugin root"),
        (("skills/demo/SKILL.md",), "must include plugin.json"),
    ],
)
def test_attach_wheel_rejects_invalid_supplied_plan(
    tmp_path: Path, targets: tuple[str, ...], message: str
) -> None:
    wheel = _wheel(tmp_path / WHEEL_NAME)
    original = wheel.read_bytes()
    plan = _plan(tmp_path, targets)

    with pytest.raises(ap.AgentPluginError, match=message):
        ap.attach_wheel(wheel, plan=plan)

    assert wheel.read_bytes() == original


@pytest.mark.parametrize("invalid_location", ["wheel", "output", "source"])
def test_attach_wheel_reports_invalid_filesystem_names(
    tmp_path: Path, invalid_location: str
) -> None:
    wheel = _wheel(tmp_path / WHEEL_NAME)
    original = wheel.read_bytes()
    plan = _plan(tmp_path, ("plugin.json",))
    invalid = tmp_path / "invalid\0path.whl"
    if invalid_location == "source":
        plan = ap.BuildPlan(
            project=plan.project,
            root=plan.root,
            files=(ap.FileMapping(invalid, PurePosixPath("plugin.json")),),
        )

    with pytest.raises(ap.AgentPluginError, match=r"cannot be read|cannot be used"):
        ap.attach_wheel(
            invalid if invalid_location == "wheel" else wheel,
            plan=plan,
            output_dir=invalid if invalid_location == "output" else None,
        )

    assert wheel.read_bytes() == original


def test_symlink_loop_is_reported_as_an_artifact_error(tmp_path: Path) -> None:
    wheel = tmp_path / WHEEL_NAME
    try:
        wheel.symlink_to(wheel.name)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")

    with pytest.raises(ap.AgentPluginError, match="Wheel cannot be read"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))


def test_corrupt_member_stream_preserves_input_and_reports_artifact_error(
    tmp_path: Path,
) -> None:
    wheel = _wheel(tmp_path / WHEEL_NAME, compression=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(wheel) as archive:
        info = archive.getinfo("demo/__init__.py")
        data_offset = (
            info.header_offset
            + 30
            + len(info.filename.encode("utf-8"))
            + len(info.extra)
        )
    contents = bytearray(wheel.read_bytes())
    contents[data_offset] ^= 0xFF
    wheel.write_bytes(contents)
    original = wheel.read_bytes()

    with pytest.raises(ap.AgentPluginError, match=r"corrupt|cannot be read"):
        ap.attach_wheel(wheel, plan=_plan(tmp_path, ("plugin.json",)))

    assert wheel.read_bytes() == original


def test_large_plugin_member_uses_zip64(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = _wheel(tmp_path / WHEEL_NAME)
    plan = _plan(tmp_path, ("plugin.json",))
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 8)

    ap.attach_wheel(wheel, plan=plan)

    with zipfile.ZipFile(wheel) as archive:
        assert archive.read(f"{PLUGIN_ROOT}/plugin.json") == (
            plan.files[0].source.read_bytes()
        )


def test_source_read_failure_preserves_input_and_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path, ("plugin.json",))
    source = plan.files[0].source
    wheel = _wheel(tmp_path / WHEEL_NAME)
    original = wheel.read_bytes()
    entries = set(tmp_path.iterdir())
    original_open = Path.open

    def fail_source_open(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[Any]:
        if path == source:
            raise OSError("source read failed")
        return original_open(path, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(Path, "open", fail_source_open)

    with pytest.raises(ap.AgentPluginError, match="Plugin file cannot be read"):
        ap.attach_wheel(wheel, plan=plan)

    assert wheel.read_bytes() == original
    assert set(tmp_path.iterdir()) == entries


def test_zip_write_failure_preserves_input_and_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path, ("plugin.json",))
    wheel = _wheel(tmp_path / WHEEL_NAME)
    original = wheel.read_bytes()
    entries = set(tmp_path.iterdir())
    original_writestr = zipfile.ZipFile.writestr

    def fail_marker_write(
        archive: zipfile.ZipFile,
        data: str | zipfile.ZipInfo,
        value: bytes | str,
        compress_type: int | None = None,
        compresslevel: int | None = None,
    ) -> None:
        name = data.filename if isinstance(data, zipfile.ZipInfo) else data
        if name.endswith("/agent_plugins.json"):
            raise OSError("write failed")
        original_writestr(
            archive,
            data,
            value,
            compress_type=compress_type,
            compresslevel=compresslevel,
        )

    monkeypatch.setattr(zipfile.ZipFile, "writestr", fail_marker_write)

    with pytest.raises(ap.AgentPluginError, match="Cannot write attached wheel"):
        ap.attach_wheel(wheel, plan=plan)

    assert wheel.read_bytes() == original
    assert set(tmp_path.iterdir()) == entries


def test_replacement_failure_preserves_input_and_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _plan(tmp_path, ("plugin.json",))
    wheel = _wheel(tmp_path / WHEEL_NAME)
    original = wheel.read_bytes()
    entries = set(tmp_path.iterdir())
    original_replace = Path.replace

    def fail_replacement(path: Path, target: Path) -> Path:
        if target == wheel.resolve():
            raise OSError("replacement failed")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_replacement)

    with pytest.raises(ap.AgentPluginError, match="Cannot write attached wheel"):
        ap.attach_wheel(wheel, plan=plan)

    assert wheel.read_bytes() == original
    assert set(tmp_path.iterdir()) == entries


def _project(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    project = root / "packages" / "demo"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[tool.agent-plugins]\nroot = "../.."\n', encoding="utf-8"
    )
    (root / "plugin.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    skill = root / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
    return project, root


def _plan(tmp_path: Path, targets: tuple[str, ...]) -> ap.BuildPlan:
    root = tmp_path / "plugin"
    root.mkdir(parents=True, exist_ok=True)
    mappings: list[ap.FileMapping] = []
    for index, target in enumerate(targets):
        source = root / f"source-{index}.txt"
        source.write_text(f"payload {index}\n", encoding="utf-8")
        mappings.append(
            ap.FileMapping(source=source.resolve(), target=PurePosixPath(target))
        )
    return ap.BuildPlan(
        project=tmp_path.resolve(), root=root.resolve(), files=tuple(mappings)
    )


def _wheel(
    path: Path,
    *,
    omit: set[str] | None = None,
    extra_members: dict[str, bytes] | None = None,
    archive_comment: bytes = b"",
    compression: int = zipfile.ZIP_STORED,
) -> Path:
    members: dict[str, bytes] = {
        "demo/__init__.py": b"VALUE = 1\n",
        "demo/data/": b"",
        f"{DIST_INFO}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\n",
        f"{DIST_INFO}/METADATA": b"Metadata-Version: 2.4\nName: demo\nVersion: 1.0.0\n",
        f"{DIST_INFO}/RECORD": b"",
    }
    for required in omit or set():
        members.pop(f"{DIST_INFO}/{required}", None)
    members.update(extra_members or {})
    with zipfile.ZipFile(path, "w") as archive:
        archive.comment = archive_comment
        for name, value in members.items():
            info = zipfile.ZipInfo(name, date_time=(2024, 2, 3, 4, 5, 6))
            info.compress_type = compression
            info.comment = b"member comment"
            info.extra = b"\x01\x00\x00\x00"
            info.create_system = 3
            info.create_version = 45
            info.extract_version = 20
            info.internal_attr = 1
            info.external_attr = (stat.S_IFREG | 0o640) << 16
            archive.writestr(info, value)
    return path


def _metadata(info: zipfile.ZipInfo) -> tuple[object, ...]:
    return (
        info.date_time,
        info.compress_type,
        info.comment,
        info.extra,
        info.create_system,
        info.create_version,
        info.extract_version,
        info.internal_attr,
        info.external_attr,
    )
