---
name: package-agent-plugin
description: Add Agent Plugin packaging to a Python project. Use when creating plugin.json and skills, configuring uv_build or Hatchling, attaching a plugin to a prebuilt wheel, exposing runtime plugin access, or verifying wheel, source distribution, and editable artifacts. For consuming instructions from an installed package, use the agent-plugins skill.
---

# Package an Agent Plugin

Package instructions beside the Python code they describe so the library and
its Agent Plugin share one release.

## Build the smallest complete integration

For a single-package project, keep the plugin at the project root:

```text
my-package/
|-- plugin.json
|-- pyproject.toml
|-- skills/
|   `-- use-my-package/
|       `-- SKILL.md
`-- src/
    `-- my_package/
```

Create `plugin.json`:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-package",
  "description": "Use My Package from Python."
}
```

Create `skills/use-my-package/SKILL.md` with a discriminating description and
the shortest complete workflow an agent needs:

```md
---
name: use-my-package
description: Use My Package to read and transform project records from Python.
---

# Use My Package

Import `my_package`, open the project input, and call `transform()`.
```

Configure an existing uv_build project in `pyproject.toml`:

```toml
[build-system]
requires = ["agent-plugins", "uv_build"]
build-backend = "agent_plugins.build.uv_build"

[tool.agent-plugins]
root = "."
```

Preview the exact selection, then build:

```console
uv run --with agent-plugins agent-plugins plan .
uv build
```

The plan must contain `plugin.json`, every intended file under `skills/`, and
`mcp.json` when configured. Add root-relative client extension files or other
plugin resources through `[tool.agent-plugins].include`.

## Verify the installed handoff

Read the wheel in an isolated environment, using the Python distribution name
from `[project].name`:

```console
uvx --with dist/my_package-0.1.0-py3-none-any.whl \
  agent-plugins read my-package
```

Confirm the reported distribution version, plugin metadata, bounded inventory,
and skill instructions. Use
[artifact verification](references/verify-artifacts.md) for exhaustive inventory
comparison. Put the public bootstrap in the package README:

```console
uvx --with my-package agent-plugins read my-package
```

Keep `agent-plugins` in `[build-system].requires` for packaging. Add it to
`[project].dependencies` when installed Python code calls `agent_plugins`
directly at runtime.

## Choose a different build path

- For Hatchling, monorepo roots, include patterns, custom backends, or an
  externally built wheel, read
  [build variants](references/build-variants.md).
- For wheel, source distribution, editable, document, and Agent Skills checks,
  read [artifact verification](references/verify-artifacts.md).
- For `mcp.json`, read the
  [MCP integration guide](https://peter-gy.github.io/agent-plugins/integrations/mcp-servers).
- For reverse-domain client directories, read the
  [client extension guide](https://peter-gy.github.io/agent-plugins/integrations/client-extensions).

Use the `agent-plugins` skill when the repository work is complete and the task
becomes consuming an installed package's instructions or resources.
