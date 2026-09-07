"""Wheel member validation, payload rewriting, and RECORD serialization."""

from __future__ import annotations

import base64
import copy
import csv
import hashlib
import io
import lzma
import stat
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import IO

from .._errors import AgentPluginError
from .._marker import MARKER_NAME, PluginMarker
from .plan import BuildPlan

_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class _WheelLayout:
    dist_info: PurePosixPath
    plugin_root: PurePosixPath
    replaced_existing_plugin: bool
    removed_signatures: tuple[PurePosixPath, ...]


def rewrite_wheel(
    source_path: Path,
    target_path: Path,
    *,
    plan: BuildPlan,
    editable_root: Path | None,
) -> _WheelLayout:
    records: list[tuple[str, str, str]] = []

    with (
        zipfile.ZipFile(source_path) as source,
        zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        layout = _inspect_archive(source, source_path)
        dist_info = layout.dist_info.as_posix()
        plugin_directory = layout.plugin_root.as_posix()
        record_path = f"{dist_info}/RECORD"
        marker_path = f"{dist_info}/{MARKER_NAME}"
        marker = PluginMarker(
            root=str(editable_root) if editable_root is not None else plugin_directory,
            files=tuple(mapping.target for mapping in plan.files),
        ).dumps()

        target.comment = source.comment
        for info in source.infolist():
            if _owned(info.filename, record_path, marker_path, plugin_directory):
                continue
            _copy_member(source, target, info, records)

        if editable_root is None:
            for mapping in plan.files:
                name = f"{plugin_directory}/{mapping.target.as_posix()}"
                _write_file(target, name, mapping.source, records)
        _write_bytes(target, marker_path, marker, records)
        _write_record(target, record_path, records)
    return layout


def _inspect_archive(archive: zipfile.ZipFile, path: Path) -> _WheelLayout:
    names = _validate_members(archive)
    candidates = tuple(
        PurePosixPath(info.filename).parent
        for info in archive.infolist()
        if not info.is_dir()
        and len(info.filename.split("/")) == 2
        and info.filename.split("/")[1] == "WHEEL"
        and info.filename.split("/")[0].endswith(".dist-info")
    )
    if len(candidates) != 1:
        raise AgentPluginError(
            f"Wheel must contain exactly one top-level .dist-info/WHEEL file: {path}. "
            "Rebuild the wheel and retry."
        )
    dist_info = candidates[0]
    for required in ("METADATA", "RECORD"):
        member = (dist_info / required).as_posix()
        if member not in names:
            raise AgentPluginError(
                f"Wheel is missing {member}: {path}. Rebuild the wheel and retry."
            )

    plugin_root = PurePosixPath(
        f"{dist_info.name.removesuffix('.dist-info')}.agent-plugin"
    )
    record = (dist_info / "RECORD").as_posix()
    marker = (dist_info / MARKER_NAME).as_posix()
    plugin_name = plugin_root.as_posix()
    installed_names = {_installation_path(name) for name in names}
    for name in names:
        installed = _installation_path(name)
        if (
            installed != name
            and not name.endswith("/")
            and PurePosixPath(installed).is_relative_to(dist_info)
            and not _owned(name, record, marker, plugin_name)
        ):
            raise AgentPluginError(
                f"Wheel contains relocated distribution metadata: {name}. "
                "Rebuild the wheel with one top-level metadata directory and retry."
            )
    replaced = marker in installed_names or any(
        name == plugin_name or name.startswith(f"{plugin_name}/")
        for name in installed_names
    )
    signatures = tuple(
        PurePosixPath(name)
        for name in sorted(names)
        if _installation_path(name) in {f"{record}.jws", f"{record}.p7s"}
    )
    return _WheelLayout(
        dist_info=dist_info,
        plugin_root=plugin_root,
        replaced_existing_plugin=replaced,
        removed_signatures=signatures,
    )


def _validate_members(archive: zipfile.ZipFile) -> set[str]:
    names: set[str] = set()
    for info in archive.infolist():
        name = info.orig_filename
        path = PurePosixPath(name)
        windows_path = PureWindowsPath(name)
        raw_parts = name.split("/")
        if not name or not path.parts:
            raise AgentPluginError(
                "Wheel contains an empty archive member. Rebuild the wheel and retry."
            )
        if (
            path.is_absolute()
            or windows_path.drive
            or ".." in path.parts
            or "\\" in name
            or "." in raw_parts
            or "" in raw_parts[:-1]
            or "\x00" in name
        ):
            raise AgentPluginError(
                f"Wheel contains an unsafe archive member: {name}. "
                "Rebuild the wheel with relative POSIX paths and retry."
            )
        if name in names:
            raise AgentPluginError(
                f"Wheel contains a duplicate archive member: {name}. "
                "Rebuild the wheel with unique member names and retry."
            )
        if info.flag_bits & 0x1:
            raise AgentPluginError(
                f"Wheel contains an encrypted archive member: {name}. "
                "Rebuild the wheel without ZIP encryption and retry."
            )
        names.add(name)
    return names


def _owned(
    name: str,
    record_path: str,
    marker_path: str,
    plugin_directory: str,
) -> bool:
    name = _installation_path(name)
    signed_records = {f"{record_path}.jws", f"{record_path}.p7s"}
    return name in {
        record_path,
        marker_path,
        plugin_directory,
        *signed_records,
    } or name.startswith(f"{plugin_directory}/")


def _installation_path(name: str) -> str:
    parts = name.split("/", 2)
    if (
        len(parts) == 3
        and parts[0].endswith(".data")
        and parts[1] in {"purelib", "platlib"}
    ):
        return parts[2]
    return name


def _copy_member(
    source: zipfile.ZipFile,
    target: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    records: list[tuple[str, str, str]],
) -> None:
    copied_info = copy.copy(info)
    if info.is_dir():
        target.writestr(copied_info, b"")
        return
    try:
        with (
            source.open(info) as input_file,
            target.open(copied_info, "w") as output_file,
        ):
            digest, size = _copy(input_file, output_file)
    except (EOFError, RuntimeError, lzma.LZMAError, zlib.error) as error:
        raise AgentPluginError(
            f"Wheel member cannot be read: {info.filename}. "
            "Rebuild the wheel and retry."
        ) from error
    records.append((info.filename, _digest(digest), str(size)))


def _write_file(
    archive: zipfile.ZipFile,
    name: str,
    source: Path,
    records: list[tuple[str, str, str]],
) -> None:
    try:
        source_stat = source.stat()
        mode = stat.S_IMODE(source_stat.st_mode)
        info = _file_info(name, mode)
        info.file_size = source_stat.st_size
        with (
            source.open("rb") as input_file,
            archive.open(
                info,
                "w",
                force_zip64=source_stat.st_size >= zipfile.ZIP64_LIMIT,
            ) as output_file,
        ):
            digest, size = _copy(input_file, output_file)
    except OSError as error:
        raise AgentPluginError(
            f"Plugin file cannot be read: {source}. Restore the file and retry."
        ) from error
    except RuntimeError as error:
        raise AgentPluginError(
            f"Plugin file cannot be written to the wheel: {source}. "
            "Check its size and retry."
        ) from error
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
