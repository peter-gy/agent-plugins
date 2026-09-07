---
title: Inspect installed plugins
description: Locate Agent Plugins by Python distribution name and inspect their selected files and documents.
---

# Inspect installed Agent Plugins

Use `locate()` to read the Agent Plugin shipped with an installed Python library. Install `agent-plugins` in the same environment as that library:

```console
pip install agent-plugins
```

## Locate one distribution

```python
import agent_plugins as ap

plugin = ap.locate("agent-plugins")
print(plugin.path)
print(plugin.tree())
```

This example opens the Agent Plugin bundled with `agent-plugins` itself. Pass your library's Python distribution name to inspect its plugin. The name used by `pip` is independent from `plugin.manifest.name`.

`locate()` raises `AgentPluginError` when the distribution is absent, has no `agent_plugins.json` marker, carries outdated or invalid marker metadata, or references an unusable file inventory.

## List the current environment

```python
import agent_plugins as ap

for distribution, plugin in ap.installed().items():
    print(distribution, plugin.path)
```

`installed()` returns a dictionary sorted by distribution name without regard to case. Distributions without a marker are skipped. When the environment exposes multiple installations of the same normalized distribution name, the first one found by Python metadata discovery takes precedence. The scan agrees with `locate()` for that installation.

Discovery is fail-fast. A marked distribution with invalid metadata or files raises `AgentPluginError` and stops the scan.

## Inspect the selected inventory

```python
for path in plugin.files:
    print(path)

for skill in plugin.skills:
    print(skill.path)

if plugin.mcp is not None:
    print(plugin.mcp.path)
```

An installed `Plugin` handle exposes exactly the paths recorded by the marker. [`Plugin.from_project()`](/guide/inspect-project) exposes the corresponding build-plan selection from a source project. Direct `Plugin(path)` construction inventories every regular file currently below a directory.

`plugin.skills` contains immediate `skills/<name>` directories whose selected inventory contains exact-case `SKILL.md`. `plugin.mcp` is `None` unless selected files contain root-level `mcp.json`.

## Use the API from a code-mode agent

An agent with Python execution can inspect the dependencies in its environment, read a relevant skill, then write Python for the task. This works for a short script, an interactive session, or a notebook. The host supplies the model and execution policy.

```python
import agent_plugins as ap

plugin = ap.locate("my-project")
skill = plugin.skill("use-my-project")

print(skill.tree(max_depth=2))
print(skill.source)

reference = skill.file("references/api.md")
print(reference.read_text(encoding="utf-8"))
```

This example assumes the plugin includes `references/api.md`. Use the names shown by `skill.tree()` to choose resources.

`skill.tree()` exposes the bounded file structure before the agent chooses what to read. `skill.source`, `skill.frontmatter`, and `skill.body` share one lazy read. `skill.file()` checks the selected inventory and containment before the agent reads a reference or runs a script through its normal code-execution tools.

Read instructions from a distribution trusted by the host before using its code or scripts. The API returns text and paths. The host decides how to pass that text to a model and whether to execute a packaged script.

## Use native paths

`Plugin`, `Skill`, `Manifest`, and `MCPConfig` implement the native filesystem protocol:

```python
from pathlib import Path

manifest_path = Path(plugin.manifest)
skill_root = Path(plugin.skills[0])
```

`skill / "references" / "api.md"` also returns a `Path` through ordinary unchecked joining. Use `skill.file("references/api.md")` for a selected resource.

## Render a bounded tree

```python
print(plugin.tree())
print(plugin.tree(max_depth=2))
print(plugin.tree(max_depth=None, max_files=None))
```

Tree rendering defaults to a maximum depth of 4 and a maximum of 100 files. Pass `None` to remove a bound. A negative limit raises `ValueError`.

`str(plugin)` and `repr(plugin)` return the default tree rendering. Notebook displays use an escaped preformatted rendering. `Skill` has the same display behavior.
