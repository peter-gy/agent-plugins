"""Agent Plugins 1.0.0 manifest validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import cast

from ..errors import ValidationIssue
from ..json import validation_error
from ..models import Author, ManifestData
from . import PLUGIN_SCHEMA_1_0_0

_NAME = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
_FIELDS = frozenset(
    {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "extensions",
    }
)
_AUTHOR_FIELDS = frozenset({"name", "email", "url"})


def load_manifest_v1(path: Path, value: dict[str, object]) -> ManifestData:
    """Validate an Agent Plugins 1.0.0 manifest."""
    issues = [
        ValidationIssue((field,), "Unknown manifest field was ignored")
        for field in value
        if field not in _FIELDS
    ]
    name = _required_string(path, value, "name")
    if len(name) > 64 or _NAME.fullmatch(name) is None:
        raise validation_error(path, ("name",), "Invalid plugin name")

    extensions_value = value.get("extensions", {})
    if not isinstance(extensions_value, dict):
        issues.append(
            ValidationIssue(
                ("extensions",), "Expected an object. The field was ignored"
            )
        )
        extensions: Mapping[str, Mapping[str, object]] = MappingProxyType({})
    else:
        extensions = _extensions(path, extensions_value)

    keywords_value = value.get("keywords", [])
    if not isinstance(keywords_value, list) or not all(
        isinstance(item, str) for item in keywords_value
    ):
        raise validation_error(path, ("keywords",), "Expected an array of strings")

    return ManifestData(
        schema=PLUGIN_SCHEMA_1_0_0,
        name=name,
        version=_optional_string(path, value, "version"),
        description=_optional_string(path, value, "description"),
        author=_author(path, value),
        homepage=_optional_string(path, value, "homepage"),
        repository=_optional_string(path, value, "repository"),
        license=_optional_string(path, value, "license"),
        keywords=tuple(cast(list[str], keywords_value)),
        extensions=extensions,
        issues=tuple(issues),
    )


def _author(path: Path, value: dict[str, object]) -> Author | None:
    if "author" not in value:
        return None
    author_value = value["author"]
    if not isinstance(author_value, dict):
        raise validation_error(path, ("author",), "Expected an object")
    author = cast(dict[str, object], author_value)
    unknown = next((field for field in author if field not in _AUTHOR_FIELDS), None)
    if unknown is not None:
        raise validation_error(
            path, ("author", unknown), f"Unknown author field: {unknown}"
        )
    return Author(
        name=_optional_string(path, author, "name", ("author",)),
        email=_optional_string(path, author, "email", ("author",)),
        url=_optional_string(path, author, "url", ("author",)),
    )


def _extensions(
    path: Path, value: dict[str, object]
) -> Mapping[str, Mapping[str, object]]:
    extensions: dict[str, Mapping[str, object]] = {}
    for namespace, extension in value.items():
        if not isinstance(extension, dict):
            raise validation_error(
                path, ("extensions", namespace), "Expected an object"
            )
        extensions[namespace] = _freeze_object(extension)
    return MappingProxyType(extensions)


def _freeze_object(value: dict[str, object]) -> Mapping[str, object]:
    return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})


def _freeze_json(value: object) -> object:
    if isinstance(value, dict):
        return _freeze_object(value)
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _required_string(path: Path, value: dict[str, object], field: str) -> str:
    if field not in value:
        raise validation_error(
            path, (field,), f"Missing required manifest field: {field}"
        )
    item = value[field]
    if not isinstance(item, str):
        raise validation_error(path, (field,), "Expected a string")
    return item


def _optional_string(
    path: Path,
    value: dict[str, object],
    field: str,
    prefix: tuple[str | int, ...] = (),
) -> str | None:
    if field not in value:
        return None
    item = value[field]
    if not isinstance(item, str):
        raise validation_error(path, (*prefix, field), "Expected a string")
    return item
