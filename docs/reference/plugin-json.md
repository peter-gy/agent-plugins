---
title: plugin.json reference
description: Reference the Agent Plugins 1.0.0 manifest fields, normalized values, and validation behavior.
---

# `plugin.json` reference

`plugin.json` is the required manifest at the plugin root. `agent-plugins` recognizes the Agent Plugins 1.0.0 schema identifier exactly and validates locally without retrieving the schema URL.

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-project",
  "version": "1.2.3",
  "description": "Agent integrations for my-project.",
  "author": {
    "name": "Example Maintainer",
    "email": "maintainer@example.com",
    "url": "https://example.com"
  },
  "homepage": "https://example.com/my-project",
  "repository": "https://github.com/example/my-project",
  "license": "Apache-2.0",
  "keywords": ["python", "agent-skills"],
  "extensions": {
    "com.example.client": {
      "entrypoint": "com.example.client/activate.json"
    }
  }
}
```

## Fields

| Field | Required | Input | Normalized value |
| --- | --- | --- | --- |
| `$schema` | Yes | Exact supported schema identifier | `Manifest.schema: str` |
| `name` | Yes | Plugin name string | `Manifest.name: str` |
| `version` | No | String | `str \| None` |
| `description` | No | String | `str \| None` |
| `author` | No | Object | `Author \| None` |
| `homepage` | No | String | `str \| None` |
| `repository` | No | String | `str \| None` |
| `license` | No | String | `str \| None` |
| `keywords` | No | Array of strings | `tuple[str, ...]` |
| `extensions` | No | Object of namespaced objects | Read-only nested mappings and tuples |

## Plugin names

`name` contains 1 to 64 characters. It can use lowercase ASCII letters, digits, periods, and hyphens. It must begin and end with a letter or digit. Consecutive `--` and `..` are rejected.

The plugin name is independent from the Python distribution name passed to `locate()`.

## Optional strings

The parser checks that optional metadata values are strings. It does not validate Semantic Versioning, URLs, email syntax, SPDX expressions, or non-empty content.

`author` accepts `name`, `email`, and `url`. Unknown author fields are fatal. An empty author object becomes `Author(name=None, email=None, url=None)`.

## Manifest extension data

Each member of `extensions` must be an object. Nested objects become read-only mappings and arrays become tuples.

The parser preserves namespace data without interpreting it. Client extension files use the separate `[tool.agent-plugins].include` mechanism.

## Issues and errors

An unknown top-level manifest field is ignored and recorded in `manifest.issues`. A top-level `extensions` value that is not an object is also ignored and recorded as an issue.

Other type, required-field, schema, or extension-namespace failures raise `ValidationError` on the first manifest property access. Fatal validation stops at the first detected issue.

```python
manifest = plugin.manifest

print(manifest.name)
for issue in manifest.issues:
    print(issue.location, issue.message)
```
