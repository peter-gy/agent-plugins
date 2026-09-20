---
name: package-agent-plugin
description: Package version-matched agent briefings with a Python project. Use when authoring core skills and references, exposing guidance through Python module help, configuring a build adapter, attaching a plugin to a wheel, or verifying installed handoffs. For consuming an installed package's instructions, use agent-plugins.
---

# Package an Agent Plugin

Package instructions beside the Python code they describe so the library and
its Agent Plugin share one release. Author one compact core skill that works
from a CLI briefing, Python module help, or a directly loaded skill file.

## Design the briefing

Start from a fresh agent's task: what the package enables, which host or extras
it requires, the first complete action, how to verify success, and where to
read more. Include every import and binding needed by the first example.

Keep package concepts, workflow choices, essential invariants, and verification
in the core skill. Put substantial setup variants and specialized workflows in
linked references, with a condition explaining when each is needed. Let the
generated briefing supply installation identity and resource-access guidance.
Rereading the current skill should not be a prerequisite for following it.

Read [briefing design](references/briefings.md) when authoring the skill or
adding a Python help entrypoint. It covers ownership, a reusable skill shape,
documentation links, and fresh-agent acceptance scenarios.

## Build the smallest complete integration

For a single-package project, keep the plugin at the project root:

```text
my-package/
|-- plugin.json
|-- pyproject.toml
|-- skills/
|   `-- my-package/
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

Name the core skill `my-package` to match `[project].name`. This lets
`ap.read("my-package")` select it by default. A task-specific skill can use
another name and be selected explicitly.

Create `skills/my-package/SKILL.md` with `name` and a discriminating
`description` in YAML frontmatter, followed by the package's shortest complete
workflow. Use real public APIs and expected results from the project.

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
directly at runtime, with a lower bound that includes the APIs used.

## Expose the same briefing in Python

Use `ap.read()` in the package's agent module to deliver its core skill through
standard Python help:

```python
# src/my_package/agent.py
import agent_plugins as _ap

__doc__ = _ap.read("my-package")
```

The caller runs `import my_package.agent` followed by `help(my_package.agent)`.
`help()` prints the briefing and returns `None`. Use `print(ap.read(...))` when
the host needs explicit text output. Pass `skill="task-name"` for a differently
named core skill. Host capability registration remains the host's contract.

Keep ordinary package imports independent of this optional help module. Give
the agent module a small introspection surface and inspect its actual
`help()` output, since exported classes can add extensive API documentation.
Keep detailed signatures on the corresponding API objects. See
[briefing design](references/briefings.md#python-module-help) for runtime access
and documentation ownership.

Verify both the CLI and Python briefing from the installed wheel. A successful
read establishes access to instructions. Exercise the first workflow in its
required host to establish runtime readiness and a verified result.

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

Use the [documentation index](https://peter-gy.github.io/agent-plugins/llms.txt)
for additional packaging and integration guidance.
