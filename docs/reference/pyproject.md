---
title: pyproject.toml reference
description: Configure the authored plugin root and additional file selection.
---

# `pyproject.toml` reference

`[tool.agent-plugins]` tells `build_plan()`, build-backend adapters, and `attach_wheel(project=...)` where the authored plugin directory lives and which additional files to package.

```toml
[tool.agent-plugins]
root = "../.."
include = ["bin/**", "com.example.client/**"]
```

## `root`

Type: non-empty string. Required.

The value resolves from the Python project directory containing `pyproject.toml`. A monorepo package can use `..` components to reach a plugin root higher in the repository.

The resolved directory must exist. `plugin.json` must be a regular file at its root.

The implementation also accepts an absolute path. Relative paths keep a project portable across checkouts and build environments.

## `include`

Type: array of non-empty strings. Default: `[]`.

Each value is a `pathlib` glob evaluated from the resolved plugin root. A matched file is added directly. A matched directory adds its complete regular-file tree.

Patterns must be plugin-root-relative. The planner rejects:

- Absolute patterns.
- `..` path components.
- Backslashes.
- Invalid glob syntax.
- Patterns that match no filesystem entry.

Selected files must resolve inside the plugin root. Directory symlinks in recursively selected trees are rejected. File symlinks are accepted when their resolved target stays inside the root.

A pattern that matches an empty directory currently succeeds and contributes no files.

## Fixed selection

The planner adds these paths independently of `include`:

| Path | Rule |
| --- | --- |
| `plugin.json` | Required regular file |
| `skills/` | Complete tree when the path exists and is a directory |
| `mcp.json` | Optional regular file |

The final `BuildPlan.files` tuple is sorted by target POSIX path. Duplicate targets contribute one mapping.

## Source-distribution staging

When the Python project directory contains `.agent-plugin/plugin.json`, the planner selects every regular file in `.agent-plugin/`. A build-backend adapter creates this reserved directory inside a source distribution to capture the authored selection. A wheel rebuilt from that artifact uses the captured files directly.

Keep authored plugin files at the configured `root`. Treat `.agent-plugin/` as build-system staging.

## Common configuration errors

Configuration and selection failures raise `AgentPluginError` with the affected path or pattern. See [Troubleshooting](/troubleshooting) for recovery by message.
