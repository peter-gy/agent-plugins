---
name: agent-plugins
description: Ship and inspect Agent Skills, MCP server configuration, and client extension files with a Python distribution. Use when adding an Agent Plugin to a Python project, attaching a prebuilt wheel, loading the exact project or installed selection, selecting a named skill, reading checked skill resources, resolving a stdio MCP launch, or verifying package artifacts.
---

# Agent Plugins

Use `agent-plugins` when a Python distribution should carry the instructions and MCP
configuration that match its installed code version.

An [Agent Plugin](https://agent-plugins.org/) is an open, vendor-neutral
portable directory format for reusable agent components. Its fixed locations
let compatible clients find [Agent Skills](https://agentskills.io/specification)
and [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification)
server configuration in the same package. Distribution, permissions, and user
experience remain with each client.

## Build the plugin directory

Keep one Agent Plugin directory in the codebase:

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
- Reverse-domain directories contain client extension files.

Create a minimal `plugin.json` at the plugin root:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-project"
}
```

Find the Python project's `pyproject.toml` and set
`[tool.agent-plugins].root` to the authored plugin root. Prefer a path relative
to `pyproject.toml`. For uv_build:

```toml
[build-system]
requires = ["agent-plugins", "uv_build"]
build-backend = "agent_plugins.build.uv_build"

[tool.agent-plugins]
root = "../.."
```

For Hatchling:

```toml
[build-system]
requires = ["agent-plugins", "hatchling"]
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
filesystem entry. A matched directory contributes its regular files.

Use `attach_wheel()` when another build system already produced the wheel. It rewrites the input after the complete attached artifact succeeds. Pass `output_dir` to preserve the source.

```python
import agent_plugins as ap

result = ap.attach_wheel(
    "dist/my_package-1.0.0-py3-none-any.whl",
    project="packages/python",
)
print(result.output)
```

The CLI exposes the same operation:

```console
agent-plugins attach-wheel dist/my_package-1.0.0-py3-none-any.whl \
  --project packages/python
```

Reuse a previously computed plan by passing it directly:

```python
from pathlib import Path

plan = ap.build_plan("packages/python")
Path("dist/attached").mkdir(parents=True, exist_ok=True)
result = ap.attach_wheel(
    "dist/my_package-1.0.0-py3-none-any.whl",
    plan=plan,
    output_dir="dist/attached",
)
```

The output directory receives the same filename. Inspect `result.replaced_existing_plugin` and `result.removed_signatures`. The CLI writes removed-signature warnings to stderr.

`agent_plugins.build.BuildBackend` provides the wheel, source distribution, and
editable hooks used by the bundled adapters. A custom delegate must also expose
the three corresponding `get_requires_for_build_*` hooks.

## Choose build-time or runtime access

Keeping `agent-plugins` in `[build-system].requires` makes it available during
the build. Add the package to `[project].dependencies` when installed Python
code needs to locate or inspect Agent Plugins:

```toml
[project]
dependencies = ["agent-plugins"]
```

Load the exact project selection before building. After installing a build from that selection, locate it with the Python distribution name used by pip:

```python
import agent_plugins as ap

source = ap.Plugin.from_project("packages/python")
plugin = ap.locate("my-package")
skill = source.skill("use-my-package")

print(source.path)
print(plugin.path)
print(plugin.manifest.path)
print(plugin.manifest.name)
print(skill.source)
print(skill.file("SKILL.md"))

if mcp := plugin.mcp:
    for name, server in mcp.servers.items():
        print(name, server)
```

`Plugin.from_project()` uses the build plan, so its files match the source
paths selected for packaging. `plugin.path` is the absolute installed plugin
root. Each item in
`plugin.skills` is an `ap.Skill` rooted at one immediate directory under
`skills/`. Use `plugin.skill(name)` for exact structural lookup. Use
`Path(skill)` or `skill.path` for that directory. Use `skill.file()` for a
selected instruction, reference, script, or asset:

```python
print(skill.file("SKILL.md"))
print(skill.file("references/api.md"))
print(skill.tree(max_depth=2))
```

`skill.source` returns the complete `SKILL.md` text. Use `skill.frontmatter`
for the raw source text between the `---` delimiters and `skill.body` for the
Markdown after the frontmatter. The package checks UTF-8 text and delimiter
structure. It does not parse the frontmatter as YAML. The first access to any
source property reads and splits `SKILL.md`, then caches all three strings. Path
and tree access leave the document unread so an agent can choose which files
and content to load.

`plugin.manifest` is an `ap.Manifest`. `plugin.mcp` is an `ap.MCPConfig` when
`mcp.json` exists. Each object exposes `.path` immediately. Accessing a parsed
field such as `manifest.name` or `mcp.servers` reads, validates, and caches its
document. MCP access validates the manifest first.

MCP servers are frozen `ap.StdioServer`, `ap.StreamableHTTPServer`, or
`ap.SSEServer` values in a read-only mapping. `manifest.issues` records
non-fatal manifest violations. `mcp.issues` records invalid server entries
skipped during loading. Document-level failures raise `ap.ValidationError` on
parsed value access.

Resolve a validated stdio server after the client creates its plugin data directory:

```python
from pathlib import Path
import os

data_dir = Path(".agent-data/my-package").resolve()
data_dir.mkdir(parents=True, exist_ok=True)

mcp = plugin.mcp
if mcp is not None:
    launch = mcp.resolve_stdio(
        "my-package",
        data_dir=data_dir,
        base_env={"PATH": os.environ.get("PATH", "")},
    )
    print(launch.command, launch.args, launch.cwd)
```

The client owns data retention, process creation, permissions, logging, and the MCP lifecycle. `resolve_stdio()` returns immutable subprocess inputs and performs one-pass Agent Plugins placeholder expansion.

Display the plugin to inspect its selected directory tree:

```python
print(plugin)
print(plugin.tree(max_depth=2))
print(plugin.tree(max_depth=None, max_files=None))
```

`Path(plugin)`, `Path(skill)`, and `Path(plugin.manifest)` use the native path
protocol. When `plugin.mcp` is present, `Path(plugin.mcp)` does too.
`ap.installed()` returns each discovered plugin keyed by Python distribution
name. Discovery is fail-fast when a marked distribution has unusable metadata
or selected files.

## Verify the package

Inspect the selected paths before building:

```console
agent-plugins plan path/to/python-project
```

Then verify the package through its installation boundaries:

1. Build a wheel and source distribution through an adapter, or attach the Agent Plugin after an external wheel build.
2. Build a wheel from the source distribution.
3. Install the wheel in a clean environment.
4. Install the Python project as editable.
5. Compare `Plugin.from_project()` with `ap.locate()` by plugin-relative file inventory and public component values.
6. Access `plugin.manifest.name` and `plugin.mcp.servers` when MCP exists to run
   the supported Agent Plugins JSON validation.
7. Confirm each `skill.path`, `skill.file("SKILL.md")`, and `skill.files` points to
   the packaged skill tree.
8. Access `skill.source`, `skill.frontmatter`, and `skill.body` to verify UTF-8 text and the
   packaged `SKILL.md` delimiter structure.
9. Run an Agent Skills validator to check frontmatter fields and other Agent
   Skills rules.

Handle `ap.AgentPluginError` when a requested Python distribution or usable plugin
root is absent. Handle `ap.ValidationError` when an installed plugin document
or `SKILL.md` structure is invalid.
