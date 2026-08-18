"""Source distribution plugin staging."""

from __future__ import annotations

import copy
import gzip
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from .._errors import AgentPluginError
from .plan import STAGED_ROOT, BuildPlan


def write_sdist_plugin(sdist: Path, plan: BuildPlan) -> None:
    """Stage a plugin inside a PEP 517 source distribution."""
    sdist_path = sdist.resolve(strict=True)
    if not sdist_path.name.endswith(".tar.gz"):
        raise AgentPluginError(
            f"Source distribution must be a .tar.gz archive: {sdist_path}"
        )

    temporary = _temporary_sdist(sdist_path)
    try:
        _rewrite(sdist_path, temporary, plan)
        temporary.replace(sdist_path)
    finally:
        temporary.unlink(missing_ok=True)


def _rewrite(source_path: Path, target_path: Path, plan: BuildPlan) -> None:
    with tarfile.open(source_path, "r:gz") as source:
        members = source.getmembers()
        root = _archive_root(members)
        stage = f"{root}/{STAGED_ROOT}"

        with (
            target_path.open("wb") as raw_target,
            gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_target, mtime=0
            ) as compressed,
            tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
            ) as target,
        ):
            for member in members:
                if member.name == stage or member.name.startswith(f"{stage}/"):
                    continue
                file_object = source.extractfile(member) if member.isfile() else None
                try:
                    target.addfile(copy.copy(member), file_object)
                finally:
                    if file_object is not None:
                        file_object.close()

            for mapping in plan.files:
                _add_file(
                    target,
                    f"{stage}/{mapping.target.as_posix()}",
                    mapping.source,
                )


def _archive_root(members: list[tarfile.TarInfo]) -> str:
    roots: set[str] = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise AgentPluginError(f"Unsafe source distribution path: {member.name}")
        roots.add(path.parts[0])
    if len(roots) != 1:
        raise AgentPluginError(
            "Source distribution must contain one top-level directory"
        )
    return roots.pop()


def _add_file(archive: tarfile.TarFile, name: str, source: Path) -> None:
    source_stat = source.stat()
    info = tarfile.TarInfo(name)
    info.size = source_stat.st_size
    info.mode = stat.S_IMODE(source_stat.st_mode)
    info.mtime = int(source_stat.st_mtime)
    info.uid = 0
    info.gid = 0
    with source.open("rb") as file_object:
        archive.addfile(info, file_object)


def _temporary_sdist(sdist: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        dir=sdist.parent,
        prefix=f".{sdist.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        return Path(temporary.name)
