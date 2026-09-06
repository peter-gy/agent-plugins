"""Rooted file inventories for Agent Plugin directories."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from ._errors import AgentPluginError


@dataclass(frozen=True, slots=True)
class FileInventory:
    """Keep one resolved root and its validated relative file names together."""

    root: Path
    names: tuple[PurePosixPath, ...]

    @classmethod
    def discover(
        cls,
        path: str | os.PathLike[str],
        *,
        required: str,
        kind: str,
    ) -> FileInventory:
        """Discover every file below a directory."""
        root = _resolve_root(path, kind=kind)
        names = (
            candidate.relative_to(root).as_posix()
            for candidate in root.rglob("*")
            if candidate.is_file()
        )
        return cls(
            root=root,
            names=_validate_names(root, names, required=required, kind=kind),
        )

    @classmethod
    def select(
        cls,
        path: str | os.PathLike[str],
        names: Iterable[str | PurePosixPath],
        *,
        required: str,
        kind: str,
    ) -> FileInventory:
        """Validate selected relative files below a directory."""
        root = _resolve_root(path, kind=kind)
        return cls(
            root=root,
            names=_validate_names(root, names, required=required, kind=kind),
        )

    def subtree(self, path: str | PurePosixPath) -> FileInventory:
        """Return the selected files below one relative directory."""
        relative = PurePosixPath(path)
        if (
            relative.is_absolute()
            or relative == PurePosixPath(".")
            or ".." in relative.parts
        ):
            raise ValueError(f"Invalid inventory subtree: {path}")
        candidate = self.root.joinpath(*relative.parts)
        try:
            root = candidate.resolve(strict=True)
            root.relative_to(self.root)
        except (OSError, RuntimeError, ValueError) as error:
            raise AgentPluginError(
                f"Inventory subtree cannot be resolved: {candidate}"
            ) from error
        if not root.is_dir():
            raise AgentPluginError(f"Inventory subtree is not a directory: {candidate}")
        return type(self)(
            root=root,
            names=tuple(
                name.relative_to(relative)
                for name in self.names
                if name.is_relative_to(relative)
            ),
        )

    def paths(self) -> tuple[Path, ...]:
        """Return absolute paths for the selected files."""
        return tuple(self.root.joinpath(*name.parts) for name in self.names)

    def file(
        self,
        path: str | os.PathLike[str],
        *,
        kind: str,
    ) -> Path:
        """Return one selected regular file below the inventory root."""
        try:
            relative = _relative_name(path, kind=kind)
        except AgentPluginError as error:
            raise AgentPluginError(
                f"Invalid {kind} file path under {self.root}: {os.fspath(path)!r}"
            ) from error
        value = relative.as_posix()
        if relative not in self.names:
            raise AgentPluginError(
                f"{kind} file is not selected under {self.root}: {value}"
            )
        candidate = self.root.joinpath(*relative.parts)
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.root)
        except (OSError, RuntimeError, ValueError) as error:
            raise AgentPluginError(
                f"{kind} file cannot be resolved: {candidate}"
            ) from error
        if not resolved.is_file():
            raise AgentPluginError(f"{kind} file is invalid: {candidate}")
        return candidate


def path_sort_key(path: PurePosixPath) -> tuple[str, str]:
    """Return the canonical ordering key for a relative file name."""
    value = path.as_posix()
    return value.casefold(), value


def _resolve_root(
    path: str | os.PathLike[str],
    *,
    kind: str,
) -> Path:
    candidate = Path(path)
    try:
        root = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise AgentPluginError(
            f"{kind} root cannot be resolved: {candidate}"
        ) from error
    if not root.is_dir():
        raise AgentPluginError(f"{kind} root is invalid: {root}")
    return root


def _validate_names(
    root: Path,
    names: Iterable[str | PurePosixPath],
    *,
    required: str,
    kind: str,
) -> tuple[PurePosixPath, ...]:
    selected: set[PurePosixPath] = set()
    for name in names:
        relative = _relative_name(name, kind=kind)
        candidate = root.joinpath(*relative.parts)
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, RuntimeError, ValueError) as error:
            raise AgentPluginError(
                f"{kind} file cannot be resolved: {candidate}"
            ) from error
        if not candidate.is_file():
            raise AgentPluginError(f"{kind} file is invalid: {candidate}")
        selected.add(relative)

    required_path = PurePosixPath(required)
    if required_path not in selected:
        raise AgentPluginError(f"{kind} files must include {required}")
    return tuple(sorted(selected, key=path_sort_key))


def _relative_name(
    path: str | os.PathLike[str] | PurePosixPath,
    *,
    kind: str,
) -> PurePosixPath:
    value = os.fspath(path)
    if not isinstance(value, str):
        raise AgentPluginError(f"Invalid {kind} file path: {value!r}")
    raw_parts = value.split("/")
    relative = PurePosixPath(value)
    if (
        not value
        or relative.is_absolute()
        or PureWindowsPath(value).drive
        or relative == PurePosixPath(".")
        or ".." in relative.parts
        or "\\" in value
        or "." in raw_parts
        or "" in raw_parts
    ):
        raise AgentPluginError(f"Invalid {kind} file path: {value}")
    return relative
