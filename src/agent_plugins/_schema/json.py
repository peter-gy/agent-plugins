"""Strict JSON document loading for Agent Plugin files."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .._errors import AgentPluginError
from .._files import FileInventory
from .errors import ValidationError, ValidationIssue


def resolve_file(path: str | os.PathLike[str]) -> Path:
    """Return an absolute path to an existing regular file."""
    candidate = Path(path)
    try:
        configured = candidate.parent.resolve(strict=True) / candidate.name
        resolved = configured.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise AgentPluginError(
            f"Plugin document cannot be resolved: {candidate}"
        ) from error
    if not resolved.is_file():
        raise AgentPluginError(f"Plugin document is not a regular file: {configured}")
    return configured


def read_json(path: Path) -> object:
    """Read a UTF-8 JSON document and reject nonstandard numeric constants."""
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text, parse_constant=_reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise validation_error(path, (), "Expected valid JSON") from error


def selected_file(inventory: FileInventory, name: str) -> Path:
    """Recheck a selected document before its first content read."""
    try:
        return inventory.file(name, kind="Plugin document")
    except AgentPluginError as error:
        raise validation_error(
            inventory.root / name,
            (),
            "Document cannot be read inside its selected root",
        ) from error


def validation_error(
    path: Path,
    location: tuple[str | int, ...],
    message: str,
) -> ValidationError:
    """Create a validation error for one document location."""
    return ValidationError(path, (ValidationIssue(location, message),))


def _reject_constant(value: str) -> object:
    raise ValueError(f"Invalid JSON constant: {value}")
