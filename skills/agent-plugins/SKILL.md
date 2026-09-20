---
name: agent-plugins
description: Read and inspect the version-matched Agent Plugin carried by an installed Python distribution. Use when a package README points to agent-plugins, when loading packaged Agent Skills and resources, listing or locating installed plugins, inspecting manifest or MCP summaries, or troubleshooting discovery. For adding Agent Plugin packaging to a repository, use the package-agent-plugin skill.
---

# Read installed Agent Plugins

Use `agent-plugins` to load the instructions and resources shipped with the
same version of a Python package that the agent will use.

## Start from a package README

Run the package and `agent-plugins` in one temporary environment:

```console
uvx --with my-package agent-plugins read my-package
```

The requirement after `--with` tells uv what to install. The final argument is
the installed Python distribution to inspect. Use a version constraint when
the task requires an exact release:

```console
uvx --with 'my-package==1.2.3' agent-plugins read my-package
```

Follow each applicable skill in the output. Resolve its relative links from the
instruction file's directory. Use `--skill NAME` when one plugin carries
several skills and the task needs a single workflow.

`read` reports MCP metadata for discovery. It does not start servers or print
configured commands, arguments, environment values, URLs, or headers. The
agent client owns component activation, permissions, processes, and data.

## Choose the CLI operation

| Task | Command |
| --- | --- |
| Read one installed plugin and all primary instructions | `agent-plugins read DISTRIBUTION` |
| Read one named skill with the plugin context | `agent-plugins read DISTRIBUTION --skill NAME` |
| List every discoverable plugin and skill path | `agent-plugins list` |
| List discoverable plugins as JSON | `agent-plugins list --json` |
| Print one installed plugin root | `agent-plugins locate DISTRIBUTION` |
| Preview files selected from a source project | `agent-plugins plan [PROJECT]` |
| Attach a configured plugin to a prebuilt wheel | `agent-plugins attach-wheel WHEEL` |

`plan` and `attach-wheel` are repository packaging operations. Load the
`package-agent-plugin` skill before changing a project or wheel.

Running `uvx agent-plugins` with no arguments reads the Agent Plugin carried by
`agent-plugins` itself. It is the shortcut for:

```console
uvx agent-plugins read agent-plugins
```

Use `agent-plugins --help` or `agent-plugins COMMAND --help` for command syntax.
Successful commands write data to stdout. Expected discovery, validation,
configuration, and filesystem failures return status `1` with an
`agent-plugins: error:` diagnostic on stderr. Argument errors return status
`2`.

## Read the current Python environment

When the target package is already installed in the active environment, run:

```console
agent-plugins read my-package
```

Use the Python API when the task needs one skill or a linked resource:

```python
import agent_plugins as ap

plugin = ap.locate("my-package")
skill = plugin.skill("use-my-package")

print(skill.source)
reference = skill.file("references/api.md")
print(reference.read_text(encoding="utf-8"))
```

`plugin.skills` contains every immediate `skills/<name>/SKILL.md` selected by
the installed package. `skill.file()` accepts an exact selected path below that
skill and rechecks containment. `plugin.tree()` and `skill.tree()` provide a
bounded inventory before reading more files.

Use `plugin.manifest` for validated plugin metadata. `plugin.mcp` is an
`MCPConfig` when the package selected `mcp.json`. Accessing parsed manifest or
MCP fields validates and caches the document. Handle `AgentPluginError` for
missing or unusable installed plugins and `ValidationError` for invalid plugin,
MCP, or skill documents.

## Keep the environment explicit

`uvx` creates a temporary environment for the command. Install the package in
the notebook, service, or project environment where its Python API will run.
The instructions printed by `read` describe the exact distribution version
resolved for that command.

Python distribution names and manifest plugin names are independent. Pass the
name used by pip or uv to `read`, `locate`, and `ap.locate()`.
