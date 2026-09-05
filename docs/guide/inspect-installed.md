---
title: Inspect installed plugins
description: Locate Agent Plugins by Python distribution name and inspect their selected files and documents.
---

# Inspect installed Agent Plugins

`agent-plugins` discovers plugins through Python distribution metadata. Each participating distribution installs an `agent_plugins.json` marker that records the plugin root and selected filenames.

## Locate one distribution

```python
import agent_plugins as ap

plugin = ap.locate("my-project")
print(plugin.path)
print(plugin.tree())
```

Pass the Python distribution name used by `pip`. This value is independent from `plugin.manifest.name`.

`locate()` raises `AgentPluginError` when the distribution is absent, has no `agent_plugins.json` marker, carries outdated or invalid marker metadata, or references an unusable file inventory.

## List the current environment

```python
import agent_plugins as ap

for distribution, plugin in ap.installed().items():
    print(distribution, plugin.path)
```

`installed()` returns a dictionary sorted by distribution name without regard to case. Distributions without a marker are skipped.

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

An installed `Plugin` handle exposes exactly the paths recorded by the marker. Direct `Plugin(path)` construction instead discovers every regular file currently below that directory.

`plugin.skills` contains immediate `skills/<name>` directories whose selected inventory contains exact-case `SKILL.md`. `plugin.mcp` is `None` unless selected files contain root-level `mcp.json`.

## Use the API from a code-mode agent

A code-mode agent that can execute Python can use the installed distribution as its skill source. It can use `agent-plugins` to discover the matching Agent Plugin, select an Agent Skill, read its instructions, and open supporting files when the current task needs them.

```python
import agent_plugins as ap

plugin = ap.locate("my-project")
skill = next(
    skill for skill in plugin.skills if skill.path.name == "use-my-project"
)

print(skill.tree(max_depth=2))
instructions = skill.body

reference = skill / "references" / "api.md"
if reference.is_file():
    reference_text = reference.read_text(encoding="utf-8")
```

`skill.tree()` exposes the bounded file structure before the agent chooses what to read. `skill.frontmatter` and `skill.body` load the `SKILL.md` source on first access. Paths created with `/` work with `pathlib`, so the agent can read a selected reference or run a selected script through its normal code-execution tools.

## Use native paths

`Plugin`, `Skill`, `Manifest`, and `MCPConfig` implement the native filesystem protocol:

```python
from pathlib import Path

manifest_path = Path(plugin.manifest)
skill_root = Path(plugin.skills[0])
```

`skill / "references" / "api.md"` also returns a `Path`.

## Render a bounded tree

```python
print(plugin.tree())
print(plugin.tree(max_depth=2))
print(plugin.tree(max_depth=None, max_files=None))
```

Tree rendering defaults to a maximum depth of 4 and a maximum of 100 files. Pass `None` to remove a bound. A negative limit raises `ValueError`.

`str(plugin)` and `repr(plugin)` return the default tree rendering. Notebook displays use an escaped preformatted rendering. `Skill` has the same display behavior.
