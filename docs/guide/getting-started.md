---
title: Get started
description: Package an Agent Skill in a wheel and locate the installed Agent Plugin.
---

# Package and locate your first Agent Plugin

Create a Python distribution that carries one Agent Skill beside the library it explains. The completed flow builds one wheel, installs it, and locates the skill from that installed distribution. The library and instructions therefore share one versioned artifact.

## Prerequisites

- Python 3.10 through 3.14.
- The [uv package manager](https://docs.astral.sh/uv/) with its `uv build` command.

## Create the project

Use this directory layout:

```text
my-project/
├── plugin.json
├── skills/
│   └── use-my-project/
│       └── SKILL.md
└── packages/
    └── python/
        ├── pyproject.toml
        └── src/
            └── my_project/
                └── __init__.py
```

Create `plugin.json` at the plugin root:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-project"
}
```

Create `skills/use-my-project/SKILL.md`:

```md
---
name: use-my-project
description: Use my-project to process project records.
---

# Use my-project

Import `my_project` and call its public API.
```

Create an empty `packages/python/src/my_project/__init__.py`, then configure `packages/python/pyproject.toml`:

```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.10"

[build-system]
requires = ["agent-plugins", "uv_build"]
build-backend = "agent_plugins.build.uv_build"

[tool.agent-plugins]
root = "../.."
```

`root` starts at the directory containing `pyproject.toml`. The value `../..` resolves to `my-project/`, where `plugin.json` lives.

## Inspect the build plan

Run the inspection command in a temporary uv environment and print the Agent Plugin build plan:

```console
uv run --with agent-plugins agent-plugins plan packages/python
```

The output begins with the resolved authored plugin root, followed by one target and source path per selected file:

```text
root    /path/to/my-project
plugin.json    /path/to/my-project/plugin.json
skills/use-my-project/SKILL.md    /path/to/my-project/skills/use-my-project/SKILL.md
```

The command separates columns with tabs and prints absolute local paths. Add `--json` when another program consumes the plan.

::: info Selection before validation
`plan` checks project configuration, selected paths, and containment. It does not parse `plugin.json` or validate the Agent Skills frontmatter.
:::

## Build and install

Build the wheel and source distribution from the repository root:

```console
uv build packages/python --out-dir dist
```

Install the wheel in a temporary environment with `agent-plugins`, then locate its Agent Plugin:

```console
uv run \
  --with agent-plugins \
  --with dist/my_project-0.1.0-py3-none-any.whl \
  agent-plugins locate my-project
```

The command prints an absolute plugin root inside uv's temporary environment, similar to:

```text
/path/to/site-packages/my_project-0.1.0.agent-plugin
```

The `.agent-plugin` directory came from the installed wheel. Its `SKILL.md` and the importable `my_project` package share the wheel's distribution version. A compatible client can discover the skill immediately from the installed metadata.

## Inspect from application code

Add `agent-plugins` to the runtime dependencies of a Python project that needs to inspect its own or another installed distribution:

```toml
[project]
dependencies = ["agent-plugins"]
```

Then inspect the installation from Python:

```python
import agent_plugins as ap

plugin = ap.locate("my-project")

print(plugin.manifest.name)
print(plugin.skills[0] / "SKILL.md")
```

```text
my-project
/path/to/site-packages/my_project-0.1.0.agent-plugin/skills/use-my-project/SKILL.md
```

`plugin.manifest.name` reads and validates `plugin.json` on first access. Learn how the three artifact modes differ in [How packaging works](/guide/artifact-lifecycle).
