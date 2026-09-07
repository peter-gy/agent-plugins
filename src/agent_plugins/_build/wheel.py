"""Attach Agent Plugin payloads to wheel artifacts."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .._errors import AgentPluginError
from .plan import BuildPlan, build_plan, validate_plan
from .wheel_archive import rewrite_wheel


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
    files = validate_plan(selected_plan)

    temporary = _temporary_wheel(output)
    try:
        try:
            layout = rewrite_wheel(
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
    validate_plan(plan)
    temporary = _temporary_wheel(source)
    try:
        try:
            rewrite_wheel(source, temporary, plan=plan, editable_root=plan.root)
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
    except (OSError, RuntimeError, ValueError) as error:
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
    except (OSError, RuntimeError, ValueError) as error:
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
            shutil.copyfileobj(source, target, length=1024 * 1024)
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
