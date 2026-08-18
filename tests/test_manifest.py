from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import agent_plugins as ap

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def test_manifest_is_a_lazy_cached_file_backed_model(tmp_path: Path) -> None:
    path = tmp_path / "plugin.json"
    _write_manifest(path, name="before-access")
    manifest = ap.Manifest(path)

    assert manifest.path == path.resolve()
    assert Path(manifest) == path.resolve()
    assert str(manifest) == str(path.resolve())
    assert repr(manifest) == f"Manifest(path={path.resolve()!r})"
    with pytest.raises(AttributeError):
        object.__setattr__(manifest, "path", tmp_path / "other.json")

    _write_manifest(path, name="first-access", description="Cached description")
    assert manifest.name == "first-access"

    _write_manifest(path, name="after-access", description="Changed")
    assert manifest.name == "first-access"
    assert manifest.description == "Cached description"


def test_manifest_exposes_typed_immutable_values(tmp_path: Path) -> None:
    path = tmp_path / "plugin.json"
    path.write_text(
        json.dumps(
            {
                "$schema": PLUGIN_SCHEMA,
                "name": "demo-plugin",
                "version": "1.2.3",
                "description": "Demo plugin",
                "author": {
                    "name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "url": "https://example.com/ada",
                },
                "homepage": "https://example.com",
                "repository": "https://example.com/repository",
                "license": "MIT",
                "keywords": ["demo", "agents"],
                "extensions": {
                    "com.example.client": {
                        "enabled": True,
                        "settings": {"levels": [1, 2]},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = ap.Manifest(path)

    assert manifest.schema == PLUGIN_SCHEMA
    assert manifest.name == "demo-plugin"
    assert manifest.version == "1.2.3"
    assert manifest.description == "Demo plugin"
    assert manifest.author == ap.Author(
        name="Ada Lovelace",
        email="ada@example.com",
        url="https://example.com/ada",
    )
    assert manifest.homepage == "https://example.com"
    assert manifest.repository == "https://example.com/repository"
    assert manifest.license == "MIT"
    assert manifest.keywords == ("demo", "agents")
    assert manifest.extensions["com.example.client"]["enabled"] is True
    assert manifest.extensions["com.example.client"]["settings"] == {"levels": (1, 2)}
    assert manifest.issues == ()

    with pytest.raises(TypeError):
        cast(dict[str, object], manifest.extensions)["other"] = {}
    with pytest.raises(TypeError):
        cast(dict[str, object], manifest.extensions["com.example.client"])[
            "enabled"
        ] = False


def test_manifest_reports_and_ignores_nonfatal_fields(tmp_path: Path) -> None:
    path = tmp_path / "plugin.json"
    path.write_text(
        json.dumps(
            {
                "$schema": PLUGIN_SCHEMA,
                "name": "demo-plugin",
                "extensions": ["invalid"],
                "futureField": True,
            }
        ),
        encoding="utf-8",
    )

    manifest = ap.Manifest(path)

    assert manifest.name == "demo-plugin"
    assert manifest.extensions == {}
    assert manifest.issues == (
        ap.ValidationIssue(
            location=("futureField",),
            message="Unknown manifest field was ignored",
        ),
        ap.ValidationIssue(
            location=("extensions",),
            message="Expected an object. The field was ignored",
        ),
    )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"name": "demo-plugin"}, "Unsupported or missing manifest schema"),
        (
            {"$schema": PLUGIN_SCHEMA, "name": "Demo"},
            "Invalid plugin name",
        ),
        (
            {"$schema": PLUGIN_SCHEMA, "name": "demo", "keywords": [1]},
            "Expected an array of strings",
        ),
        (
            {
                "$schema": PLUGIN_SCHEMA,
                "name": "demo",
                "author": {"organization": "Example"},
            },
            "Unknown author field",
        ),
        (
            {
                "$schema": PLUGIN_SCHEMA,
                "name": "demo",
                "extensions": {"com.example.client": True},
            },
            "Expected an object",
        ),
    ],
)
def test_manifest_rejects_fatal_schema_violations(
    tmp_path: Path, value: object, message: str
) -> None:
    path = tmp_path / "plugin.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ap.ValidationError, match=message) as captured:
        _name = ap.Manifest(path).name

    assert captured.value.path == path.resolve()
    assert captured.value.issues


def test_manifest_caches_validation_failures(tmp_path: Path) -> None:
    path = tmp_path / "plugin.json"
    _write_manifest(path, name="Invalid Name")
    manifest = ap.Manifest(path)

    with pytest.raises(ap.ValidationError) as first:
        _name = manifest.name

    _write_manifest(path, name="valid-name")
    with pytest.raises(ap.ValidationError) as second:
        _name = manifest.name

    assert first.value is second.value
    assert ap.Manifest(path).name == "valid-name"


def test_manifest_rejects_nonstandard_json_constants(tmp_path: Path) -> None:
    path = tmp_path / "plugin.json"
    path.write_text(
        f'{{"$schema": {json.dumps(PLUGIN_SCHEMA)}, "name": NaN}}',
        encoding="utf-8",
    )

    with pytest.raises(ap.ValidationError, match="valid JSON"):
        _name = ap.Manifest(path).name


@pytest.mark.parametrize(
    "name",
    ["a", "my-plugin", "acme.tools", "lint3r", "a" * 64],
)
def test_manifest_accepts_specification_names(tmp_path: Path, name: str) -> None:
    path = tmp_path / "plugin.json"
    _write_manifest(path, name=name)

    assert ap.Manifest(path).name == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "Demo",
        "-start",
        ".start",
        "end-",
        "end.",
        "has--double",
        "has..double",
        "has/slash",
        "a" * 65,
    ],
)
def test_manifest_rejects_names_outside_the_schema(tmp_path: Path, name: str) -> None:
    path = tmp_path / "plugin.json"
    _write_manifest(path, name=name)

    with pytest.raises(ap.ValidationError, match="Invalid plugin name"):
        _name = ap.Manifest(path).name


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", 1),
        ("description", None),
        ("homepage", []),
        ("repository", {}),
        ("license", True),
    ],
)
def test_manifest_requires_exact_metadata_types(
    tmp_path: Path, field: str, value: object
) -> None:
    path = tmp_path / "plugin.json"
    document: dict[str, object] = {
        "$schema": PLUGIN_SCHEMA,
        "name": "demo",
        field: value,
    }
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ap.ValidationError, match="Expected a string"):
        _name = ap.Manifest(path).name


def test_manifest_requires_exact_author_field_types(tmp_path: Path) -> None:
    path = tmp_path / "plugin.json"
    path.write_text(
        json.dumps(
            {
                "$schema": PLUGIN_SCHEMA,
                "name": "demo",
                "author": {"name": 1},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ap.ValidationError, match="Expected a string"):
        _author = ap.Manifest(path).author


def _write_manifest(path: Path, *, name: str, description: str | None = None) -> None:
    value: dict[str, object] = {"$schema": PLUGIN_SCHEMA, "name": name}
    if description is not None:
        value["description"] = description
    path.write_text(json.dumps(value), encoding="utf-8")
