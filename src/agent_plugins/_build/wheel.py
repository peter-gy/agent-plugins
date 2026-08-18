"""Wheel payload and metadata writing."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import IO

from .._errors import AgentPluginError
from .._marker import MARKER_NAME, PluginMarker
from .plan import BuildPlan

_CHUNK_SIZE = 1024 * 1024


def write_wheel_plugin(
    wheel: Path,
    plan: BuildPlan,
    *,
    editable: bool = False,
) -> None:
    """Write a regular or editable Agent Plugin marker into a wheel."""
    wheel_path = wheel.resolve(strict=True)
    with zipfile.ZipFile(wheel_path) as archive:
        dist_info = _dist_info(archive)
    plugin_directory = f"{dist_info.removesuffix('.dist-info')}.agent-plugin"
    marker_root = str(plan.root) if editable else plugin_directory
    marker = PluginMarker(
        root=marker_root,
        files=tuple(mapping.target for mapping in plan.files),
    ).dumps()

    temporary = _temporary_wheel(wheel_path)
    try:
        _rewrite(
            wheel_path,
            temporary,
            dist_info=dist_info,
            plugin_directory=plugin_directory,
            marker=marker,
            plan=None if editable else plan,
        )
        temporary.replace(wheel_path)
    finally:
        temporary.unlink(missing_ok=True)


def _rewrite(
    source_path: Path,
    target_path: Path,
    *,
    dist_info: str,
    plugin_directory: str,
    marker: bytes,
    plan: BuildPlan | None,
) -> None:
    record_path = f"{dist_info}/RECORD"
    marker_path = f"{dist_info}/{MARKER_NAME}"
    records: list[tuple[str, str, str]] = []

    with (
        zipfile.ZipFile(source_path) as source,
        zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        for info in source.infolist():
            if _owned(info.filename, record_path, marker_path, plugin_directory):
                continue
            _copy_member(source, target, info, records)

        if plan is not None:
            for mapping in plan.files:
                name = f"{plugin_directory}/{mapping.target.as_posix()}"
                _write_file(target, name, mapping.source, records)
        _write_bytes(target, marker_path, marker, records)
        _write_record(target, record_path, records)


def _dist_info(archive: zipfile.ZipFile) -> str:
    candidates = {
        PurePosixPath(name).parts[0]
        for name in archive.namelist()
        if name.endswith(".dist-info/WHEEL") and len(PurePosixPath(name).parts) == 2
    }
    if len(candidates) != 1:
        raise AgentPluginError("Wheel must contain exactly one .dist-info/WHEEL file")
    return candidates.pop()


def _owned(
    name: str,
    record_path: str,
    marker_path: str,
    plugin_directory: str,
) -> bool:
    signed_records = {f"{record_path}.jws", f"{record_path}.p7s"}
    return name in {
        record_path,
        marker_path,
        plugin_directory,
        *signed_records,
    } or name.startswith(f"{plugin_directory}/")


def _copy_member(
    source: zipfile.ZipFile,
    target: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    records: list[tuple[str, str, str]],
) -> None:
    if info.is_dir():
        target.writestr(info, b"")
        return
    with source.open(info) as input_file, target.open(info, "w") as output_file:
        digest, size = _copy(input_file, output_file)
    records.append((info.filename, _digest(digest), str(size)))


def _write_file(
    archive: zipfile.ZipFile,
    name: str,
    source: Path,
    records: list[tuple[str, str, str]],
) -> None:
    info = _file_info(name, stat.S_IMODE(source.stat().st_mode))
    with source.open("rb") as input_file, archive.open(info, "w") as output_file:
        digest, size = _copy(input_file, output_file)
    records.append((name, _digest(digest), str(size)))


def _write_bytes(
    archive: zipfile.ZipFile,
    name: str,
    value: bytes,
    records: list[tuple[str, str, str]],
) -> None:
    archive.writestr(_file_info(name, 0o644), value)
    records.append((name, _digest(hashlib.sha256(value).digest()), str(len(value))))


def _write_record(
    archive: zipfile.ZipFile,
    record_path: str,
    records: list[tuple[str, str, str]],
) -> None:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows([*records, (record_path, "", "")])
    archive.writestr(_file_info(record_path, 0o644), output.getvalue().encode())


def _copy(source: IO[bytes], target: IO[bytes]) -> tuple[bytes, int]:
    digest = hashlib.sha256()
    size = 0
    while chunk := source.read(_CHUNK_SIZE):
        target.write(chunk)
        digest.update(chunk)
        size += len(chunk)
    return digest.digest(), size


def _digest(value: bytes) -> str:
    encoded = base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _file_info(name: str, mode: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def _temporary_wheel(wheel: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        dir=wheel.parent,
        prefix=f".{wheel.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        return Path(temporary.name)
