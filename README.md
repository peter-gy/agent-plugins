# agent-plugins

`agent-plugins` packages Agent Skills, Model Context Protocol configuration, and
client extension files with a Python distribution. Each installed wheel carries
the agent files that match its code version.

The package implements the portable [Agent Plugins](https://agent-plugins.org/)
directory format and supports Python 3.10 through 3.14.

## Ship an Agent Plugin

Keep one Agent Plugin tree beside the code it documents:

```text
my-project/
├── plugin.json
├── skills/
│   └── use-my-package/
│       ├── SKILL.md
│       ├── agents/
│       ├── references/
│       └── scripts/
├── mcp.json
└── packages/
    └── python/
        └── pyproject.toml
```

`skills/` contains [Agent Skills](https://agentskills.io/specification).
`mcp.json` contains [Model Context Protocol](https://modelcontextprotocol.io/specification)
server configuration when the plugin provides MCP servers.

Create `plugin.json` at the plugin root:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-project"
}
```

Configure the Python package to wrap `uv_build`:

```toml
[build-system]
requires = ["agent-plugins==0.1.1", "uv_build==0.12.2"]
build-backend = "agent_plugins.build.uv_build"

[tool.agent-plugins]
root = "../.."
```

`root` is relative to `pyproject.toml`. The build selects `plugin.json`, the
complete `skills/` tree, and `mcp.json` when present.

Build, install, and locate the packaged plugin:

```console
uv build packages/python --out-dir dist
python -m pip install "agent-plugins==0.1.1" dist/my_package-*.whl
agent-plugins locate my-package
```

```text
/.../site-packages/my_package-1.2.3.agent-plugin
```

The wheel contains the plugin directory and an `agent_plugins.json` marker in
the distribution metadata. A source distribution stages the same files for a
reproducible wheel rebuild. An editable install points the marker at the authored
plugin tree.

### Use Hatchling

Keep the plugin settings and select the Hatchling adapter:

```toml
[build-system]
requires = ["agent-plugins==0.1.1", "hatchling==1.31.0"]
build-backend = "agent_plugins.build.hatchling"

[tool.agent-plugins]
root = "../.."
```

### Include other plugin files

Add root-relative patterns for executables or client extensions:

```toml
[tool.agent-plugins]
root = "../.."
include = ["bin/**", "com.example.client/**"]
```

Each pattern must stay within the plugin root and match at least one file.

## Inspect an installed plugin

Add `agent-plugins` to the runtime dependencies of Python code that calls the
inspection API:

```toml
[project]
dependencies = ["agent-plugins==0.1.1"]
```

```python
import agent_plugins as ap

plugin = ap.locate("my-package")

print(plugin.manifest.name)
print(plugin.manifest.path)

for skill in plugin.skills:
    print(skill.path)
    print(skill / "SKILL.md")

if mcp := plugin.mcp:
    for name, server in mcp.servers.items():
        print(name, server)
```

`ap.locate()` accepts the distribution name used by `pip`. `ap.installed()`
returns every discovered Agent Plugin keyed by distribution name.

| Object | Access |
| --- | --- |
| `plugin.path` | Absolute plugin root |
| `plugin.manifest` | Lazy `plugin.json` document |
| `plugin.skills` | `ap.Skill` objects rooted under `skills/` |
| `plugin.mcp` | Lazy `mcp.json` document, when present |
| `plugin.files` | Files selected by the package build |
| `plugin.tree()` | Bounded ASCII tree of the installed plugin |
| `skill.frontmatter` | Source text between the `---` delimiters |
| `skill.body` | Markdown after the frontmatter |
| `skill.files` | Files selected below the skill root |

Manifest, MCP, and skill documents load on first parsed-field access and cache
their result. Call `ap.locate()` again to read a fresh snapshot. Invalid
documents raise `ap.ValidationError`.

MCP servers are frozen `ap.StdioServer`, `ap.StreamableHTTPServer`, or
`ap.SSEServer` values. Their fields preserve placeholders such as
`${PLUGIN_ROOT}` for the agent client to resolve.

## Inspect a build plan

Preview the files selected by `[tool.agent-plugins]` before building:

```console
agent-plugins plan packages/python
```

Use `--json` for machine-readable output. Python build integrations can consume
the same plan:

```python
import agent_plugins as ap

plan = ap.build_plan("packages/python")
for file in plan.files:
    print(file.source, "->", file.target)
```

List every plugin visible in the current environment:

```console
agent-plugins list --json
```

## Develop and release

From a repository checkout, install the locked development environment and run
the local checks:

```console
uv sync --locked
uv run ruff format --check src tests
uv run ruff check src tests
uv run ty check
uv run pyrefly check
uv run pytest -q
./scripts/build-dist.sh
```

Prepare the version and lockfile in a release pull request:

```console
uv version --bump patch
```

After the release commit reaches `main` and its push CI passes, update the local
branch and start the tag-driven release:

```console
git pull --ff-only origin main
./scripts/release.sh --dry-run
./scripts/release.sh
```

Before the first tag, configure PyPI to trust `.github/workflows/publish.yml`
through the repository's `pypi` environment. PyPI documents the setup in
[Adding a Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).
