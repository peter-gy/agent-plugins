"""Bounded ASCII rendering for filesystem selections."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from ._files import path_sort_key

DEFAULT_MAX_DEPTH = 4
DEFAULT_MAX_FILES = 100


def render_tree(
    root: Path,
    files: tuple[PurePosixPath, ...],
    *,
    max_depth: int | None = DEFAULT_MAX_DEPTH,
    max_files: int | None = DEFAULT_MAX_FILES,
) -> str:
    """Render selected files as a bounded ASCII tree."""
    if max_depth is not None and max_depth < 0:
        raise ValueError("max_depth must be zero or greater")
    if max_files is not None and max_files < 0:
        raise ValueError("max_files must be zero or greater")

    displayed = files if max_files is None else files[:max_files]
    lines = [f"{root}{os.sep}"]
    if max_depth != 0:
        _append_tree(
            lines,
            _tree_children(displayed),
            directory=PurePosixPath("."),
            prefix="",
            depth=1,
            max_depth=max_depth,
        )
    remaining = len(files) - len(displayed)
    if remaining:
        noun = "file" if remaining == 1 else "files"
        lines.append(f"... {remaining} more {noun}")
    return "\n".join(lines)


def _tree_children(
    files: tuple[PurePosixPath, ...],
) -> dict[PurePosixPath, list[tuple[PurePosixPath, bool]]]:
    root = PurePosixPath(".")
    directories: set[PurePosixPath] = set()
    for file in files:
        for parent in file.parents:
            if parent == root:
                break
            directories.add(parent)

    children: dict[PurePosixPath, list[tuple[PurePosixPath, bool]]] = {}
    for directory in directories:
        children.setdefault(directory.parent, []).append((directory, True))
    for file in files:
        children.setdefault(file.parent, []).append((file, False))
    for entries in children.values():
        entries.sort(key=lambda entry: path_sort_key(entry[0]))
    return children


def _append_tree(
    lines: list[str],
    children: dict[PurePosixPath, list[tuple[PurePosixPath, bool]]],
    *,
    directory: PurePosixPath,
    prefix: str,
    depth: int,
    max_depth: int | None,
) -> None:
    entries = children.get(directory, [])
    for index, (relative, is_directory) in enumerate(entries):
        last = index == len(entries) - 1
        connector = "`-- " if last else "|-- "
        suffix = "/" if is_directory else ""
        lines.append(f"{prefix}{connector}{relative.name}{suffix}")
        if not is_directory:
            continue

        child_prefix = prefix + ("    " if last else "|   ")
        if max_depth is None or depth < max_depth:
            _append_tree(
                lines,
                children,
                directory=relative,
                prefix=child_prefix,
                depth=depth + 1,
                max_depth=max_depth,
            )
        elif children.get(relative):
            lines.append(f"{child_prefix}`-- ...")
