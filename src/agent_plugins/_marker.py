"""Installed Agent Plugin marker format."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import cast

MARKER_NAME = "agent_plugins.json"


class InvalidMarker(ValueError):
    """An installed Agent Plugin marker has an invalid shape."""


class OutdatedMarker(InvalidMarker):
    """An installed Agent Plugin marker predates the file inventory."""


@dataclass(frozen=True, slots=True)
class PluginMarker:
    """Describe one installed plugin root and its packaged files."""

    root: str
    files: tuple[PurePosixPath, ...]

    @classmethod
    def loads(cls, text: str) -> PluginMarker:
        """Parse an installed marker."""
        try:
            value: object = json.loads(text)
        except json.JSONDecodeError as error:
            raise InvalidMarker from error
        if not isinstance(value, dict) or not isinstance(value.get("root"), str):
            raise InvalidMarker
        files = value.get("files")
        if files is None:
            raise OutdatedMarker
        if not isinstance(files, list) or not all(
            isinstance(file_name, str) for file_name in files
        ):
            raise InvalidMarker
        return cls(
            root=value["root"],
            files=tuple(
                PurePosixPath(file_name) for file_name in cast(list[str], files)
            ),
        )

    def dumps(self) -> bytes:
        """Serialize the marker as stable UTF-8 JSON."""
        return (
            json.dumps(
                {
                    "root": self.root,
                    "files": [file.as_posix() for file in self.files],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
