"""Attach Agent Plugin payloads to wheel artifacts."""

from __future__ import annotations

import base64
import copy
import csv
import hashlib
import io
import lzma
import os
import stat
import tempfile
import zipfile
import zlib
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import IO

from .._errors import AgentPluginError
from .._marker import MARKER_NAME, PluginMarker
from .plan import BuildPlan, build_plan

_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class WheelAttachment:
    """Describe an Agent Plugin attached to a wheel."""

    source: Path
    output: Path
    dist_info: PurePosixPath
    plugin_root: PurePosixPath
    files: tuple[PurePosixPath, ...]
    replaced_existing_plugin: bool
    removed_signatures: tuple[PurePosixPath, ...]


@dataclass(frozen=True, slots=True)
class _WheelLayout:
    dist_info: PurePosixPath
    plugin_root: PurePosixPath
    replaced_existing_plugin: bool
    removed_signatures: tuple[PurePosixPath, ...]


def attach_wheel(
    wheel: str | Path,
    *,
    project: str | Path | None = None,
    plan: BuildPlan | None = None,
    output_dir: str | Path | None = None,
) -> WheelAttachment:
    """Attach a planned Agent Plugin to one existing wheel."""
    if project is not None and plan is not None:
        raise AgentPluginError(
            "Pass either project or plan to attach_wheel(), not both"
        )

    source, source_mode = _resolve_wheel(wheel)
    output = _resolve_output(source, output_dir)
    selected_plan = plan if plan is not None else build_plan(project or Path.cwd())
    files = _validate_plan(selected_plan)

    temporary = _temporary_wheel(output)
    try:
        try:
            layout = _rewrite(
                source,
                temporary,
                plan=selected_plan,
                editable_root=None,
            )
            temporary.chmod(source_mode)
            _publish(temporary, output, in_place=output == source)
        except AgentPluginError:
            raise
        except zipfile.BadZipFile as error:
            raise AgentPluginError(
                f"Wheel is corrupt: {source}. Rebuild the wheel and retry."
            ) from error
        except zipfile.LargeZipFile as error:
            raise AgentPluginError(
                f"Wheel exceeds the supported ZIP limits: {source}. "
                "Rebuild the wheel with ZIP64 support and retry."
            ) from error
        except NotImplementedError as error:
            raise AgentPluginError(
                f"Wheel uses unsupported ZIP compression: {source}. "
                "Rebuild the wheel with a supported compression method and retry."
            ) from error
        except OSError as error:
            raise AgentPluginError(
                f"Cannot write attached wheel: {output}. "
                "Check file access and available space, then retry."
            ) from error
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)

    return WheelAttachment(
        source=source,
        output=output,
        dist_info=layout.dist_info,
        plugin_root=layout.plugin_root,
        files=files,
        replaced_existing_plugin=layout.replaced_existing_plugin,
        removed_signatures=layout.removed_signatures,
    )


def _attach_editable_wheel(wheel: Path, plan: BuildPlan) -> None:
    """Attach an authored-root marker to an editable wheel."""
    source, source_mode = _resolve_wheel(wheel)
    _validate_plan(plan)
    temporary = _temporary_wheel(source)
    try:
        try:
            _rewrite(source, temporary, plan=plan, editable_root=plan.root)
            temporary.chmod(source_mode)
            temporary.replace(source)
        except AgentPluginError:
            raise
        except zipfile.BadZipFile as error:
            raise AgentPluginError(
                f"Wheel is corrupt: {source}. Rebuild the wheel and retry."
            ) from error
        except (zipfile.LargeZipFile, NotImplementedError) as error:
            raise AgentPluginError(
                f"Wheel uses an unsupported ZIP format: {source}. "
                "Rebuild the wheel and retry."
            ) from error
        except OSError as error:
            raise AgentPluginError(
                f"Cannot write editable wheel: {source}. "
                "Check file access and available space, then retry."
            ) from error
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def _resolve_wheel(wheel: str | Path) -> tuple[Path, int]:
    candidate = Path(wheel).expanduser()
    if candidate.suffix != ".whl":
        raise AgentPluginError(
            f"Wheel path must end in .whl: {candidate}. Select a built wheel and retry."
        )
    try:
        path = candidate.resolve(strict=True)
        metadata = path.stat()
    except (OSError, RuntimeError) as error:
        raise AgentPluginError(
            f"Wheel cannot be read: {candidate}. "
            "Check the path and file access, then retry."
        ) from error
    if not path.is_file():
        raise AgentPluginError(
            f"Wheel path is not a file: {path}. Select a built wheel and retry."
        )
    return path, stat.S_IMODE(metadata.st_mode)


def _resolve_output(source: Path, output_dir: str | Path | None) -> Path:
    if output_dir is None:
        return source
    candidate = Path(output_dir).expanduser()
    try:
        directory = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AgentPluginError(
            f"Output directory cannot be used: {candidate}. "
            "Create the directory and check its access, then retry."
        ) from error
    if not directory.is_dir():
        raise AgentPluginError(
            f"Output directory is not a directory: {directory}. "
            "Select an existing directory and retry."
        )
    output = directory / source.name
    if output.exists() or output.is_symlink():
        raise AgentPluginError(
            f"Output wheel already exists: {output}. "
            "Remove it or select another output directory."
        )
    return output


def _validate_plan(plan: BuildPlan) -> tuple[PurePosixPath, ...]:
    files: list[PurePosixPath] = []
    seen: set[PurePosixPath] = set()
    for mapping in plan.files:
        target = mapping.target
        value = target.as_posix()
        if (
            target.is_absolute()
            or PureWindowsPath(value).drive
            or not target.parts
            or ".." in target.parts
            or "\\" in value
        ):
            raise AgentPluginError(
                f"Plugin target must stay within the plugin root: {value}"
            )
        if target in seen:
            raise AgentPluginError(f"Plugin plan contains a duplicate target: {value}")
        collision = next(
            (
                existing
                for existing in seen
                if existing in target.parents or target in existing.parents
            ),
            None,
        )
        if collision is not None:
            raise AgentPluginError(
                "Plugin plan contains file-directory target collisions: "
                f"{collision.as_posix()} and {value}"
            )
        seen.add(target)
        try:
            source = mapping.source.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise AgentPluginError(
                f"Plugin file cannot be read: {mapping.source}. "
                "Restore the file and retry."
            ) from error
        if not source.is_file():
            raise AgentPluginError(
                f"Plugin source is not a file: {source}. "
                "Select a regular file and retry."
            )
        files.append(target)
    return tuple(files)


def _rewrite(
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
    marker = (dist_info / MARKER_NAME).as_posix()
    plugin_name = plugin_root.as_posix()
    replaced = marker in names or any(
        name == plugin_name or name.startswith(f"{plugin_name}/") for name in names
    )
    signatures = tuple(
        signature
        for signature in (
            dist_info / "RECORD.jws",
            dist_info / "RECORD.p7s",
        )
        if signature.as_posix() in names
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
        name = info.filename
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
    copied_info = copy.copy(info)
    if info.is_dir():
        target.writestr(copied_info, b"")
        return
    try:
        with source.open(info) as input_file, target.open(
            copied_info, "w"
        ) as output_file:
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
        with source.open("rb") as input_file, archive.open(
            info,
            "w",
            force_zip64=source_stat.st_size >= zipfile.ZIP64_LIMIT,
        ) as output_file:
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


def _temporary_wheel(output: Path) -> Path:
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            return Path(temporary.name)
    except OSError as error:
        raise AgentPluginError(
            f"Cannot create a temporary wheel in {output.parent}. "
            "Check directory access and available space, then retry."
        ) from error


def _publish(temporary: Path, output: Path, *, in_place: bool) -> None:
    if in_place:
        temporary.replace(output)
        return
    try:
        os.link(temporary, output)
    except FileExistsError as error:
        raise AgentPluginError(
            f"Output wheel already exists: {output}. "
            "Remove it or select another output directory."
        ) from error
    except OSError:
        _publish_reserved(temporary, output)


def _publish_reserved(temporary: Path, output: Path) -> None:
    descriptor: int | None = None
    try:
        mode = stat.S_IMODE(temporary.stat().st_mode)
        descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
        if os.name != "nt":
            os.fchmod(descriptor, mode)
        with (
            temporary.open("rb") as source,
            os.fdopen(descriptor, "wb", closefd=False) as target,
        ):
            _copy(source, target)
            target.flush()
            os.fsync(descriptor)
        if not os.path.samestat(os.fstat(descriptor), output.lstat()):
            raise AgentPluginError(
                f"Output wheel changed during publication: {output}. "
                "Inspect the destination and retry."
            )
    except FileExistsError as error:
        raise AgentPluginError(
            f"Output wheel already exists: {output}. "
            "Remove it or select another output directory."
        ) from error
    except AgentPluginError:
        raise
    except OSError as error:
        raise AgentPluginError(
            f"Cannot publish attached wheel: {output}. "
            "Remove an incomplete destination, check file access, and retry."
        ) from error
    finally:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)
