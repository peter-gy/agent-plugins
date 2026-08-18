"""Lazy, file-backed Agent Plugin manifest model."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType

from .errors import ValidationIssue
from .json import read_json, resolve_file, validation_error
from .lazy import LazyResult
from .models import Author, ManifestData
from .v1 import PLUGIN_SCHEMA_1_0_0
from .v1.manifest import load_manifest_v1

_ManifestLoader = Callable[[Path, dict[str, object]], ManifestData]
_MANIFEST_LOADERS: Mapping[str, _ManifestLoader] = MappingProxyType(
    {PLUGIN_SCHEMA_1_0_0: load_manifest_v1}
)


class Manifest:
    """Expose a lazily validated `plugin.json` document."""

    __slots__ = ("_path", "_result")

    def __init__(self, path: str | os.PathLike[str]) -> None:
        resolved = resolve_file(path)
        self._path = resolved
        self._result = LazyResult(lambda: _load_manifest(resolved))

    @property
    def path(self) -> Path:
        """Return the absolute manifest path."""
        return self._path

    @property
    def schema(self) -> str:
        """Return the canonical Agent Plugins manifest schema identifier."""
        return self._data.schema

    @property
    def name(self) -> str:
        """Return the plugin name."""
        return self._data.name

    @property
    def version(self) -> str | None:
        """Return the plugin version when declared."""
        return self._data.version

    @property
    def description(self) -> str | None:
        """Return the plugin description when declared."""
        return self._data.description

    @property
    def author(self) -> Author | None:
        """Return author metadata when declared."""
        return self._data.author

    @property
    def homepage(self) -> str | None:
        """Return the plugin homepage when declared."""
        return self._data.homepage

    @property
    def repository(self) -> str | None:
        """Return the source repository when declared."""
        return self._data.repository

    @property
    def license(self) -> str | None:
        """Return the license value when declared."""
        return self._data.license

    @property
    def keywords(self) -> tuple[str, ...]:
        """Return the plugin keywords."""
        return self._data.keywords

    @property
    def extensions(self) -> Mapping[str, Mapping[str, object]]:
        """Return immutable client extension data."""
        return self._data.extensions

    @property
    def issues(self) -> tuple[ValidationIssue, ...]:
        """Return non-fatal manifest validation issues."""
        return self._data.issues

    @property
    def _data(self) -> ManifestData:
        return self._result.get()

    def __fspath__(self) -> str:
        """Return the manifest path for native filesystem APIs."""
        return str(self.path)

    def __str__(self) -> str:
        """Return the manifest path."""
        return str(self.path)

    def __repr__(self) -> str:
        """Return a path-oriented representation without loading the manifest."""
        return f"Manifest(path={self.path!r})"


def _load_manifest(path: Path) -> ManifestData:
    value = read_json(path)
    if not isinstance(value, dict):
        raise validation_error(path, (), "Expected an object")
    schema = value.get("$schema")
    if not isinstance(schema, str):
        raise validation_error(
            path, ("$schema",), "Unsupported or missing manifest schema"
        )
    loader = _MANIFEST_LOADERS.get(schema)
    if loader is None:
        raise validation_error(
            path, ("$schema",), "Unsupported or missing manifest schema"
        )
    return loader(path, value)
