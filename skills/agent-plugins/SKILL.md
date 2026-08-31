---
name: agent-plugins
description: Ship Agent Skills, MCP server configuration, and extension files with a Python package, choosing build-time or runtime access as needed. Use when adding an Agent Plugin to a Python project, configuring uv_build or Hatchling, locating installed plugin and skill paths, traversing skill files, reading manifest, skill source, or MCP values, or verifying wheel, source distribution, and editable installs.
---

# Agent Plugins

Use `agent-plugins` when a Python package should carry the instructions and MCP
configuration that match its installed code version.

An [Agent Plugin](https://agent-plugins.org/) is an open, vendor-neutral
portable directory format for reusable agent components. Its fixed locations
let compatible clients find [Agent Skills](https://agentskills.io/specification)
and [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification)
server configuration in the same package. Distribution, permissions, and user
experience remain with each client.

## Build the plugin tree

Keep one Agent Plugin tree in the codebase:

```text
my-plugin/
├── plugin.json
├── skills/
│   └── use-my-package/
│       ├── SKILL.md
│       ├── scripts/
│       └── references/
├── mcp.json
└── com.example.client/
    └── hooks/
```

- `plugin.json` identifies the plugin and its Agent Plugins schema.
- `skills/` contains Agent Skills and their nested files.
- `mcp.json` describes stdio, Streamable HTTP, or legacy HTTP+SSE servers.
- Reverse-domain directories contain client-specific extension files.

Create a minimal `plugin.json` at the plugin root:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-project"
}
```

Find the Python package's `pyproject.toml` and set
`[tool.agent-plugins].root` relative to that file. For uv_build:

```toml
[build-system]
requires = ["agent-plugins==0.1.1", "uv_build==0.12.2"]
build-backend = "agent_plugins.build.uv_build"

[tool.agent-plugins]
root = "../.."
```

For Hatchling:

```toml
[build-system]
requires = ["agent-plugins==0.1.1", "hatchling==1.31.0"]
build-backend = "agent_plugins.build.hatchling"

[tool.agent-plugins]
root = "../.."
```

The build selects `plugin.json`, the complete `skills/` tree, and `mcp.json`
when present. Select other root-relative files explicitly:

```toml
[tool.agent-plugins]
root = "../.."
include = ["bin/**", "com.example.client/**"]
```

Every include pattern must stay within the plugin root and match at least one
file.

Use the build plan directly when another build system owns artifact writing:

```python
import agent_plugins as ap

plan = ap.build_plan("packages/python")
for file in plan.files:
    print(file.source, file.target)
```

`agent_plugins.build.BuildBackend` provides the wheel, source distribution, and
editable hooks used by the bundled adapters.

## Choose build-time or runtime access

Keeping `agent-plugins` in `[build-system].requires` makes it available during
the build. Add the package to `[project].dependencies` when installed Python
code needs to locate or inspect Agent Plugins:

```toml
[project]
dependencies = ["agent-plugins==0.1.1"]
```

Locate a plugin with the Python package name used by pip:

```python
import agent_plugins as ap

plugin = ap.locate("my-package")

print(plugin.path)
print(plugin.manifest.path)
print(plugin.manifest.name)

for skill in plugin.skills:
    print(skill.path)
    print(skill / "SKILL.md")

if mcp := plugin.mcp:
    for name, server in mcp.servers.items():
        print(name, server)
```

`plugin.path` is the absolute installed plugin root. Each item in
`plugin.skills` is an `ap.Skill` rooted at one immediate directory under
`skills/`. Use `Path(skill)` or `skill.path` for that directory. Use `/` to
build native paths to its instructions, references, scripts, or assets:

```python
skill = plugin.skills[0]

print(skill / "SKILL.md")
print(skill / "references" / "api.md")
print(skill.tree(max_depth=2))
```

Use `skill.frontmatter` for the source text between the `---` delimiters. Use
`skill.body` for the Markdown source after the frontmatter. The first access to
either property reads and splits `SKILL.md`, then caches both strings. Path and
tree access leave the document unread so an agent can choose which files and
content to load.

`plugin.manifest` is an `ap.Manifest`. `plugin.mcp` is an `ap.MCPConfig` when
`mcp.json` exists. Each object exposes `.path` immediately. Accessing a parsed
field such as `manifest.name` or `mcp.servers` reads, validates, and caches its
document. MCP access validates the manifest first.

MCP servers are frozen `ap.StdioServer`, `ap.StreamableHTTPServer`, or
`ap.SSEServer` values in a read-only mapping. `manifest.issues` records ignored
manifest fields. `mcp.issues` records invalid server entries skipped during
loading. Document-level failures raise `ap.ValidationError` on parsed value
access.

Display the plugin to inspect its packaged tree:

```python
print(plugin)
print(plugin.tree(max_depth=2))
print(plugin.tree(max_depth=None, max_files=None))
```

`Path(plugin)`, `Path(skill)`, and `Path(plugin.manifest)` use the native path
protocol. When `plugin.mcp` is present, `Path(plugin.mcp)` does too.
`ap.installed()` returns each discovered plugin keyed by installed Python
package name.

## Verify the package

Inspect the selected paths before building:

```console
agent-plugins plan path/to/python-project
```

Then verify the package through its installation boundaries:

1. Build a wheel and source distribution.
2. Build a wheel from the source distribution.
3. Install the wheel in a clean environment.
4. Install the Python package as editable.
5. Call `ap.locate()` in both environments.
6. Access `plugin.manifest.name` and `plugin.mcp.servers` when MCP exists to run
   schema validation and the Agent Plugins rules.
7. Confirm each `skill.path`, `skill / "SKILL.md"`, and `skill.files` points to
   the packaged skill tree.
8. Access `skill.frontmatter` and `skill.body` to verify the packaged
   `SKILL.md` structure.

Handle `ap.AgentPluginError` when a requested Python package or usable plugin
root is absent. Handle `ap.ValidationError` when an installed plugin document
or `SKILL.md` structure is invalid.
