---
title: Plugin directory
description: Organize the manifest, Agent Skills, MCP configuration, and client extension files in one plugin root.
---

# Organize the plugin directory

Keep one Agent Plugin directory beside the code it describes. The plugin root contains `plugin.json` and the optional integration surfaces selected for packaging.

```text
my-project/
├── plugin.json
├── skills/
│   └── use-my-project/
│       ├── SKILL.md
│       ├── agents/
│       ├── references/
│       └── scripts/
├── mcp.json
├── bin/
│   └── my-server
└── com.example.client/
    └── hooks/
```

## Fixed plugin files

The build plan recognizes three locations directly:

- `plugin.json` is required at the plugin root.
- `skills/` is selected recursively when present.
- `mcp.json` is selected when present at the plugin root.

`plugin.skills` recognizes immediate `skills/<name>/SKILL.md` directories. An extra grouping directory such as `skills/group/name/SKILL.md` remains a packaged file but does not become a `Skill` handle.

File names are case-sensitive. Use the exact names `plugin.json`, `mcp.json`, and `SKILL.md`.

## Additional plugin files

Select executables and client extension files with root-relative patterns:

```toml
[tool.agent-plugins]
root = "../.."
include = ["bin/**", "com.example.client/**"]
```

An include pattern must stay inside the plugin root. Absolute patterns, `..` path components, and backslashes are rejected. Each pattern must match at least one filesystem entry. A matched directory contributes every regular file below it.

Directory symlinks inside selected trees are rejected. A file symlink is accepted when its resolved target remains inside the plugin root.

## Preview the selected directory

Run the build plan from any working directory by passing the Python project directory:

```console
agent-plugins plan packages/python --json
```

Use `BuildPlan.files` from Python when another build system owns artifact writing:

```python
import agent_plugins as ap

plan = ap.build_plan("packages/python")
for file in plan.files:
    print(file.source, "->", file.target)
```

The plan is the authoritative preview of packaged paths. `Plugin(path)` serves a different job and discovers every current file under the directory.
