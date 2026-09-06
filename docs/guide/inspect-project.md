---
title: Inspect an authored project
description: Load the exact Agent Plugin selected by a Python project's build plan.
---

# Inspect an authored project

`Plugin.from_project()` returns the Agent Plugin that a Python project will package:

```python
import agent_plugins as ap

plugin = ap.Plugin.from_project("packages/python")
skill = plugin.skill("use-my-project")

print(skill.source)
print(skill.file("SKILL.md"))
```

The method reads `[tool.agent-plugins]` through `build_plan()`, then constructs a `Plugin` from the selected target paths. Unselected repository files do not enter the handle.

## Compare project and directory handles

Use `Plugin.from_project()` when package selection defines the boundary:

```python
selected = ap.Plugin.from_project("packages/python")
```

Use `Plugin(path)` when every current regular file below a plugin directory belongs to the boundary:

```python
directory = ap.Plugin("my-plugin")
```

Both forms expose the same `Plugin`, `Skill`, manifest, and MCP APIs. Their file inventories can differ when `[tool.agent-plugins]` excludes repository files.

During a source-distribution rebuild, `build_plan()` selects the staged `.agent-plugin/` directory. `Plugin.from_project()` therefore inspects the same staged files that the rebuilt wheel receives.

## Compare source and installed selections

An installed handle comes from the `agent_plugins.json` marker. Compare it with the source handle after installing a wheel or editable build produced from that project selection and before changing selected source files:

```python
source = ap.Plugin.from_project("packages/python")
installed = ap.locate("my-project")

source_files = tuple(path.relative_to(source.path) for path in source.files)
installed_files = tuple(path.relative_to(installed.path) for path in installed.files)

assert source_files == installed_files
assert source.manifest.name == installed.manifest.name
assert source.skill("use-my-project").source == installed.skill(
    "use-my-project"
).source
```

Absolute roots differ because one handle points at project files and the other points at installed files. Plugin-relative inventory and component behavior stay aligned.

See [Inspect installed Agent Plugins](/guide/inspect-installed) for distribution discovery and [Plugin directory](/guide/plugin-directory) for file selection.
