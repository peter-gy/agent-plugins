<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-lockup-horizontal-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-lockup-horizontal-light.svg">
    <img alt="agent-plugins" src="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-lockup-horizontal-light.svg" width="430">
  </picture>
</p>

<p align="center">
  Ship Agent Plugins with Python packages.
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

[Agent Plugins](https://agent-plugins.org/) gives reusable [Agent Skills](https://agentskills.io/specification) and [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification) servers one package structure that compatible clients can discover consistently. A `plugin.json` manifest identifies the format, fixed locations expose its portable components, and namespaced [client extensions](https://peter-gy.github.io/agent-plugins/integrations/client-extensions) preserve client-specific behavior. Authors maintain one plugin layout, and each client loads the parts it supports.

The specification defines that directory boundary. `agent-plugins` carries the complete plugin through Python packaging beside the library it extends. Regular Python [wheels](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) and [source distributions](https://packaging.python.org/en/latest/specifications/source-distribution-format/) can contain the manifest, skills, MCP configuration, and extension files. Installing the distribution makes its matching Agent Plugin available through Python metadata. Editable installs point discovery at the authored directory.

The library and plugin share one release boundary. Teams can update library behavior, skills, MCP configuration, and client extensions together, evaluate the resulting integration against that build, then version, publish, install, and roll them back as one unit. Users and agents install one package, and compatible clients can discover the plugin for that installed library version immediately.

Use a build-backend adapter when `agent-plugins` owns the Python build path. When another tool already produced the wheel, attach the configured plugin as a separate artifact step. The command and Python API rewrite the input after the complete attached artifact succeeds. Pass `--output-dir` or `output_dir` to preserve it.

```console
agent-plugins attach-wheel dist/example-1.0.0-py3-none-any.whl --project .
```

```python
import agent_plugins as ap

result = ap.attach_wheel("dist/example-1.0.0-py3-none-any.whl")
print(result.output)
```

Both paths use the same build plan and wheel writer. See [Attach a prebuilt wheel](https://peter-gy.github.io/agent-plugins/guide/attach-wheel) for output copies, result fields, reruns, and signature handling.

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

The printed Agent Plugin directory and the importable library came from the same wheel and share its distribution version.

The [complete quickstart](https://peter-gy.github.io/agent-plugins/guide/getting-started) includes the Python package and Agent Skill files needed for a runnable project.

## Inspect a project or installation

Add `agent-plugins` to runtime dependencies when Python code calls the inspection API:

```toml
[project]
dependencies = ["agent-plugins"]
```

```python
import agent_plugins as ap

source = ap.Plugin.from_project("packages/python")
installed = ap.locate("my-project")
skill = source.skill("use-my-project")

print(source.manifest.name)
print(skill.source)
print(skill.file("SKILL.md"))

if installed.mcp is not None:
    for name, server in installed.mcp.servers.items():
        print(name, server)
```

`Plugin.from_project()` exposes exactly the files selected by `[tool.agent-plugins]`. After installing a build produced from that selection, `locate()` exposes the same plugin-relative inventory. `Plugin(path)` remains the directory-tree constructor for every current file below a plugin root.

`skill.source` returns the complete cached `SKILL.md` text. `skill.file()` checks that a resource belongs to the selected inventory before returning its path.

`locate()` accepts the Python distribution name used by `pip`. `installed.manifest.name` is a separate Agent Plugin identity.

Code-mode agents that can execute Python can use the installed distribution as their plugin source. Through the same API, they can inspect the manifest and MCP configuration, traverse `plugin.skills`, read skill instructions, and open client extension files through native `Path` operations. See [Inspect installed plugins](https://peter-gy.github.io/agent-plugins/guide/inspect-installed).

## Core model

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-core-model-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-core-model-light.svg">
    <img alt="Core model: an authored Python project builds into one wheel that installs the library beside its version-matched Agent Plugin, which locate() returns as a plugin handle" src="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-core-model-light.svg" width="300">
  </picture>
</p>

The build plan selects the plugin files and checks their paths before a build-backend adapter or `attach_wheel()` packages them beside the library. Manifest, MCP, and skill-document content is read on first access through the inspection API and cached for that handle.

## Related work

[TanStack Intent](https://tanstack.com/intent/) versions Agent Skills with npm library releases and lets agents discover them from installed dependencies. `agent-plugins` applies that package-manager principle to Python and carries the broader Agent Plugins format: the manifest, optional skills and MCP configuration, and client extension files.

## Development

[`development_docs/`](https://github.com/peter-gy/agent-plugins/tree/main/development_docs) covers contributor setup, architecture, testing, packaging, documentation, and releases. Serve the docs through [Portless](https://portless.sh/):

```console
pnpm --dir docs dev
```

The main checkout uses `https://docs.agent-plugins.localhost`. Linked worktrees receive a branch-prefixed subdomain.

## License

Licensed under the [Apache License 2.0](https://github.com/peter-gy/agent-plugins/blob/main/LICENSE).
