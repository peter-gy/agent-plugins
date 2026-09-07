---
title: Validation and caching
description: Understand file-plan checks, lazy document validation, non-fatal issues, and refresh behavior.
---

# Validation and caching

The package validates different contracts at different transitions. Keeping these boundaries separate makes build and inspection failures predictable.

## Validation boundaries

| Transition | Checks | Result |
| --- | --- | --- |
| `build_plan()` | Project configuration, selected paths, containment, required files | `BuildPlan` or `AgentPluginError` |
| `attach_wheel()` | Build plan, wheel structure, archive member paths, destination, plugin source reads | `WheelAttachment` or `AgentPluginError` |
| `Plugin.from_project()` | Build plan and exact selected inventory | `Plugin` or `AgentPluginError` |
| `Plugin(path)` | Plugin root, recursive file inventory, required `plugin.json` | `Plugin` or `AgentPluginError` |
| `locate()` | `agent_plugins.json` marker, installed root, exact selected inventory | `Plugin` or `AgentPluginError` |
| Manifest property access | UTF-8 JSON, schema identifier, manifest fields | Normalized value, issues, or `ValidationError` |
| MCP property access | Manifest first, then MCP top level and server entries | Server values, issues, or `ValidationError` |
| Skill content access | UTF-8 text and frontmatter delimiters | Raw source strings or `ValidationError` |
| `Skill.file()` | Selected membership, regular file, current containment | Absolute `Path` or `AgentPluginError` |
| `MCPConfig.resolve_stdio()` | Server transport, data directory, contained command, working directory, and selected membership for `plugin.mcp` | `ResolvedStdioServer` or `AgentPluginError` |

Build planning does not parse document contents. Skill content access does not parse YAML frontmatter.

## Fatal failures and non-fatal issues

Fatal document failures raise `ValidationError`, a subclass of `AgentPluginError`. The error exposes the document path and one or more `ValidationIssue` values.

Two document cases are recoverable:

- An unknown manifest field, or a malformed top-level `extensions` value, is ignored and recorded in `manifest.issues`.
- An invalid MCP server entry is skipped and recorded in `mcp.issues`.

Read the issues even when the requested values load successfully:

```python
manifest = plugin.manifest
print(manifest.name)
for issue in manifest.issues:
    print(issue.location, issue.message)
```

## Two cache boundaries

A `Plugin` or `Skill` handle captures its selected file inventory during construction. Adding or deleting files does not change that handle.

Each manifest, MCP configuration, and skill document reads content on first content access. The object then caches the loaded value or raised exception under a lock. Skill `source`, `frontmatter`, and `body` share one cached read.

An interrupted first read can be retried on the same handle. Completed reads and validation failures remain cached.

Documents obtained through a `Plugin` or `Skill` recheck containment before that first read. If the selected path has become unavailable or resolves outside its root, content access raises a cached `ValidationError`.

Create a new handle to refresh document contents:

```python
plugin = ap.locate("my-project")
print(plugin.manifest.name)
```

For editable installs, reinstall the distribution after changing the selected filenames. A new handle cannot see a path absent from the `agent_plugins.json` marker.

## Immutable normalized values

Manifest extension data and MCP server mappings are read-only mappings. Nested manifest arrays become tuples. `Author` and MCP server values are frozen dataclasses.

Direct construction of `StdioServer`, `StreamableHTTPServer`, and `SSEServer` creates immutable values but does not run document schema validation. Obtain them through `MCPConfig.servers` when configuration validation is required.
