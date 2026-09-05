<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-lockup-horizontal-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-lockup-horizontal-light.svg">
    <img alt="agent-plugins" src="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-lockup-horizontal-light.svg" width="430">
  </picture>
</p>

<p align="center">
  Ship agent instructions and tool integrations with Python packages.
</p>

<p align="center">
  <a href="https://peter-gy.github.io/agent-plugins/"><strong>Documentation</strong></a> ·
  <a href="https://pypi.org/project/agent-plugins/"><strong>PyPI</strong></a> ·
  <a href="https://agent-plugins.org/"><strong>Agent Plugins format</strong></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/agent-plugins/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/agent-plugins"></a>
  <a href="https://pypi.org/project/agent-plugins/"><img alt="Supported Python versions" src="https://img.shields.io/pypi/pyversions/agent-plugins"></a>
  <a href="https://github.com/peter-gy/agent-plugins/actions/workflows/ci.yml"><img alt="CI status" src="https://github.com/peter-gy/agent-plugins/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/peter-gy/agent-plugins/blob/main/LICENSE"><img alt="Apache-2.0 license" src="https://img.shields.io/pypi/l/agent-plugins"></a>
</p>

`agent-plugins` adds a portable [Agent Plugin](https://agent-plugins.org/) directory to regular Python [wheels](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) and [source distributions](https://packaging.python.org/en/latest/specifications/source-distribution-format/). A wheel is an installable archive. A source distribution carries source files for a later build. Editable installs point discovery at the authored directory.

An Agent Plugin can contain [Agent Skills](https://agentskills.io/specification), [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification) server configuration, and [client extension files](https://peter-gy.github.io/agent-plugins/integrations/client-extensions).

## Quickstart

Keep the plugin directory beside its Python package:

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

Create `plugin.json`:

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

Create an empty `packages/python/src/my_project/__init__.py`, then configure the Python project:

Wrap the [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/) in `packages/python/pyproject.toml`:

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

With the [uv package manager](https://docs.astral.sh/uv/) installed, preview the selected files, build the package, install the wheel in a temporary environment, and locate its Agent Plugin:

```console
uv run --with agent-plugins agent-plugins plan packages/python
uv build packages/python --out-dir dist
uv run \
  --with agent-plugins \
  --with dist/my_project-0.1.0-py3-none-any.whl \
  agent-plugins locate my-project
```

```text
/path/to/site-packages/my_project-0.1.0.agent-plugin
```

The [complete quickstart](https://peter-gy.github.io/agent-plugins/guide/getting-started) includes the Python package and Agent Skill files needed for a runnable project.

## Inspect installed plugins

Add `agent-plugins` to runtime dependencies when Python code calls the inspection API:

```toml
[project]
dependencies = ["agent-plugins"]
```

```python
import agent_plugins as ap

plugin = ap.locate("my-project")

print(plugin.manifest.name)
print(plugin.tree())

for skill in plugin.skills:
    print(skill.tree(max_depth=2))
    print(skill.body)

if plugin.mcp is not None:
    for name, server in plugin.mcp.servers.items():
        print(name, server)
```

`locate()` accepts the Python distribution name used by `pip`. `plugin.manifest.name` is a separate Agent Plugin identity.

Agents that can execute Python in their working session, often called code-mode agents, can call the same API directly. They can traverse `plugin.skills`, inspect `skill.files` or `skill.tree()`, read `skill.frontmatter` and `skill.body`, and open referenced files through native `Path` operations. See [Inspect installed plugins](https://peter-gy.github.io/agent-plugins/guide/inspect-installed).

## Core model

```text
authored plugin directory
        → build plan
            ├── regular wheel → installed wheel + agent_plugins.json marker
            ├── source distribution → rebuilt and installed wheel + agent_plugins.json marker
            └── editable install → installed marker pointing to authored root
        → Plugin handle and selected file inventory
        → lazy manifest, skill, and MCP access
```

The build plan selects files and checks their paths. Manifest, MCP, and skill-document content is read on first access through the inspection API and cached for that handle.

## Development

[`development_docs/`](https://github.com/peter-gy/agent-plugins/tree/main/development_docs) covers contributor setup, architecture, testing, packaging, documentation, and releases. Serve the docs through [Portless](https://portless.sh/):

```console
pnpm --dir docs dev
```

The main checkout uses `https://docs.agent-plugins.localhost`. Linked worktrees receive a branch-prefixed subdomain.

## License

Licensed under the [Apache License 2.0](https://github.com/peter-gy/agent-plugins/blob/main/LICENSE).
