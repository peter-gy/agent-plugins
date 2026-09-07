---
title: Get started
description: Build a Python library with an Agent Skill, install the wheel, and read its instructions from Python.
---

# Package and use your first Agent Plugin

Build a Python library with instructions for using it. Install the resulting wheel, then read the packaged skill and call the library from the same Python environment.

## Prerequisites

- Python 3.10 through 3.14.
- The [uv package manager](https://docs.astral.sh/uv/) for building and creating temporary environments. The commands download their declared dependencies.

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

```json [plugin.json]
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-project"
}
```

Write `skills/use-my-project/SKILL.md`. An [Agent Skill](https://agentskills.io/specification) provides instructions, metadata, and optional supporting resources:

```md [skills/use-my-project/SKILL.md]
---
name: use-my-project
description: Use my-project to greet a person by name.
---

# Use my-project

Import `greet` from `my_project` and call it with the person's name.
The function returns a greeting string.
```

Create the library in `packages/python/src/my_project/__init__.py`:

```python [packages/python/src/my_project/__init__.py]
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

Configure `packages/python/pyproject.toml`. The [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/) builds the Python package, and the `agent-plugins` adapter adds the selected plugin files:

```toml [packages/python/pyproject.toml]
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

`root` resolves from the directory containing `pyproject.toml`. Here it reaches `my-project/`, where `plugin.json` lives.

## Build and install

Run from `my-project/`:

```console
uv run --with agent-plugins agent-plugins plan packages/python
uv build packages/python --out-dir dist
```

`plan` lists the manifest and skill selected for packaging. It checks paths and containment. Document validation happens when the Python API reads content.

The build creates a [wheel](https://packaging.python.org/en/latest/specifications/binary-distribution-format/), an installable archive, and a [source distribution](https://packaging.python.org/en/latest/specifications/source-distribution-format/) from which another wheel can be built.

Open Python in a temporary environment containing the wheel and the inspection library:

```console
uv run \
  --with agent-plugins \
  --with dist/my_project-0.1.0-py3-none-any.whl \
  python
```

## Read the skill and use the library

Run in that Python session:

```python
import agent_plugins as ap
from my_project import greet

plugin = ap.locate("my-project")
skill = plugin.skill("use-my-project")

print(skill.source)
print(greet("Ada"))
```

The first print shows the packaged instructions. The final line is:

```text
Hello, Ada!
```

The importable library and the skill came from the same wheel. An agent with Python execution can read the instructions through this API, then use the library for its task. The host agent controls which instructions to load and which code to run.

## Apply this to your library

Keep `agent-plugins` in `[build-system].requires` for packaging. Add it to runtime dependencies when your installed Python code calls the inspection API:

```toml
[project]
dependencies = ["agent-plugins"]
```

Use the [Hatchling adapter](/guide/build-backends#hatchling) for Hatchling builds or [attach a prebuilt wheel](/guide/attach-wheel) when another tool produces the artifact. Use [project inspection](/guide/inspect-project) before building and [package verification](/guide/verify-package) before publishing.
