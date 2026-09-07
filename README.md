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

`agent-plugins` ships a Python library and its agent integrations in one package. An agent with Python execution can read its packaged instructions, then use the library in the same environment. Library code, skills, tool configuration, and resources share one release.

The [Agent Plugins format](https://agent-plugins.org/) defines the directory: a manifest, [Agent Skills](https://agentskills.io/specification) for instructions and resources, [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification) server configuration for tools, and client extensions. This library packages that directory and makes it discoverable through Python metadata. Agent clients choose which components to activate.

## Package your plugin

Keep `plugin.json` and `skills/` beside your code. For a project using the [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/), configure `pyproject.toml`:

```toml
[build-system]
requires = ["agent-plugins", "uv_build"]
build-backend = "agent_plugins.build.uv_build"

[tool.agent-plugins]
root = "."
```

Build with the [uv package manager](https://docs.astral.sh/uv/):

```console
uv build
```

The [quickstart](https://peter-gy.github.io/agent-plugins/guide/getting-started) creates a complete project, builds it, and locates the installed plugin. Use the [Hatchling adapter](https://peter-gy.github.io/agent-plugins/guide/build-backends#hatchling) for Hatchling projects, or [attach a prebuilt wheel](https://peter-gy.github.io/agent-plugins/guide/attach-wheel) when another tool owns the build:

```console
agent-plugins attach-wheel dist/my_project-0.1.0-py3-none-any.whl --project .
```

Attachment updates the wheel in place. Pass `--output-dir` to preserve the input.

## Inspect an installed plugin

Install `agent-plugins` in the environment you want to inspect. The package includes its own Agent Skill:

```console
pip install agent-plugins
```

```python
import agent_plugins as ap

plugin = ap.locate("agent-plugins")
skill = plugin.skill("agent-plugins")

print(skill.source)
print(skill.file("SKILL.md"))
```

Pass your library's distribution name to `locate()` to inspect its plugin. Use [`Plugin.from_project()`](https://peter-gy.github.io/agent-plugins/guide/inspect-project) to inspect the selected source files before building.

## Documentation

- [Get started](https://peter-gy.github.io/agent-plugins/guide/getting-started): package, install, and locate a plugin.
- [How packaging works](https://peter-gy.github.io/agent-plugins/guide/artifact-lifecycle): wheels, source distributions, and editable installs.
- [Integrate](https://peter-gy.github.io/agent-plugins/guide/inspect-installed): read skills, inspect files, and resolve MCP configuration.
- [Python API](https://peter-gy.github.io/agent-plugins/reference/python-api) · [CLI](https://peter-gy.github.io/agent-plugins/reference/cli) · [Configuration](https://peter-gy.github.io/agent-plugins/reference/pyproject)

<details>
<summary>Packaging lifecycle</summary>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-core-model-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-core-model-light.svg">
    <img alt="Core model: an authored Python project builds into one wheel that installs the library beside its version-matched Agent Plugin, which locate() returns as a plugin handle" src="https://raw.githubusercontent.com/peter-gy/agent-plugins/main/docs/public/brand/agent-plugins-core-model-light.svg" width="300">
  </picture>
</p>

</details>

## Development

See [development_docs/](https://github.com/peter-gy/agent-plugins/tree/main/development_docs) for setup, architecture, checks, and releases. Serve the documentation locally with `pnpm --dir docs dev`.

## License

[Apache-2.0](https://github.com/peter-gy/agent-plugins/blob/main/LICENSE).
