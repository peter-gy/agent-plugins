---
title: Python API reference
description: Reference the complete public API for build planning, discovery, filesystem handles, documents, values, and diagnostics.
---

# Python API reference

Import the top-level API as `agent_plugins`:

```python
import agent_plugins as ap
```

The distribution supports Python 3.10 through 3.14 and ships a `py.typed` marker.

## Build planning

### `build_plan(project=".")`

```python
def build_plan(project: str | Path = ".") -> BuildPlan: ...
```

Reads `[tool.agent-plugins]` from `project/pyproject.toml`, resolves the authored plugin root, and returns the complete ordered file plan.

`project` can be a string or `Path`. It must identify the Python project directory.

Raises `AgentPluginError` for missing configuration, configuration I/O failures, invalid TOML syntax, invalid settings, an unusable plugin root, unsafe patterns, directory symlinks, missing required files, or selected files that resolve outside the plugin root. An invalid UTF-8 `pyproject.toml` currently raises `UnicodeDecodeError`.

### `BuildPlan`

```python
@dataclass(frozen=True, slots=True)
class BuildPlan:
    project: Path
    root: Path
    files: tuple[FileMapping, ...]
```

- `project` is the resolved Python project directory.
- `root` is the resolved authored or staged plugin root.
- `files` is the ordered source-to-target mapping.

### `FileMapping`

```python
@dataclass(frozen=True, slots=True)
class FileMapping:
    source: Path
    target: PurePosixPath
```

`source` is an absolute local path. `target` is relative to the plugin root inside an artifact.

## Installed discovery

### `locate(distribution_name)`

```python
def locate(distribution_name: str) -> Plugin: ...
```

Finds an installed Python distribution, reads its `agent_plugins.json` marker, validates the selected file inventory, and returns a new `Plugin` handle.

Pass the Python distribution name used by `pip` and `importlib.metadata`. An empty name, absent distribution, absent marker, outdated marker, invalid marker, unusable root, or invalid selected file raises `AgentPluginError`.

### `installed()`

```python
def installed() -> dict[str, Plugin]: ...
```

Returns marked distributions keyed by Python distribution name and sorted without regard to case. Unmarked distributions are skipped.

Discovery is fail-fast. An invalid marked distribution raises `AgentPluginError` and stops the scan.

## `Plugin`

```python
Plugin(path: str | os.PathLike[str])
```

Creates a handle for an authored plugin directory. Construction resolves the root, recursively inventories every regular file, and requires root-level `plugin.json`. It creates document and skill handles but does not read their content.

Raises `AgentPluginError` when the root cannot be resolved, is not a directory, lacks a regular `plugin.json`, or contains a discovered file that cannot be resolved inside the root.

Installed `Plugin` handles returned by discovery use the exact marker-selected inventory.

### Properties

| Property | Type | Behavior |
| --- | --- | --- |
| `path` | `Path` | Resolved absolute plugin root |
| `files` | `tuple[Path, ...]` | Absolute paths in this handle's selected inventory |
| `manifest` | `Manifest` | Stable lazy handle for `plugin.json` |
| `skills` | `tuple[Skill, ...]` | Immediate selected Agent Skill directories |
| `mcp` | `MCPConfig \| None` | Stable lazy handle when root-level `mcp.json` is selected |

### `tree()`

```python
plugin.tree(*, max_depth: int | None = 4, max_files: int | None = 100) -> str
```

Returns a deterministic ASCII rendering. `None` removes a bound. Negative values raise `ValueError`.

`str(plugin)` and `repr(plugin)` return the default tree. `Path(plugin)` and `os.fspath(plugin)` return the plugin root. Notebook display uses an escaped `<pre>` rendering.

Two `Plugin` handles compare equal and have the same hash when their resolved root and selected relative filenames match. File content and loaded document values do not participate.

## `Skill`

```python
Skill(path: str | os.PathLike[str])
```

Creates a handle for an authored skill directory. Construction inventories every regular file and requires exact-case `SKILL.md`.

Raises `AgentPluginError` when the root cannot be resolved, is not a directory, lacks a regular `SKILL.md`, or contains a discovered file that cannot be resolved inside the root.

### Properties

| Property | Type | Behavior |
| --- | --- | --- |
| `path` | `Path` | Resolved absolute skill root |
| `files` | `tuple[Path, ...]` | Absolute paths in the selected skill inventory |
| `frontmatter` | `str` | Raw text between the `---` delimiter lines |
| `body` | `str` | Raw Markdown after the closing delimiter |

The first access to `frontmatter` or `body` reads UTF-8 text, checks delimiter structure, and caches both strings or the first `ValidationError`. YAML fields are not parsed.

```python
skill / "references" / "api.md"
```

The `/` operator delegates to ordinary `pathlib.Path` joining. It is not a containment check.

`Skill.tree()`, native path conversion, display, equality, and hashing follow the `Plugin` contracts.

## `Manifest`

```python
Manifest(path: str | os.PathLike[str])
```

Creates a lazy file-backed `plugin.json` handle. Construction resolves an existing regular file. `path`, string conversion, native path conversion, and `repr()` leave JSON unread.

Raises `AgentPluginError` during construction when the path cannot be resolved to a regular file. Content failures raise `ValidationError` on first data access.

Any data property triggers one UTF-8 JSON read and validation. The normalized value or exception is cached for the handle.

| Property | Type |
| --- | --- |
| `path` | `Path` |
| `schema` | `str` |
| `name` | `str` |
| `version` | `str \| None` |
| `description` | `str \| None` |
| `author` | `Author \| None` |
| `homepage` | `str \| None` |
| `repository` | `str \| None` |
| `license` | `str \| None` |
| `keywords` | `tuple[str, ...]` |
| `extensions` | `Mapping[str, Mapping[str, object]]` |
| `issues` | `tuple[ValidationIssue, ...]` |

See [`plugin.json`](/reference/plugin-json) for field validation.

## `MCPConfig`

```python
MCPConfig(path: str | os.PathLike[str], manifest: Manifest)
```

Creates a lazy file-backed `mcp.json` handle. The manifest's parent directory supplies the plugin root for path-containment checks.

Raises `AgentPluginError` during construction when the MCP path cannot be resolved to a regular file. Manifest or MCP content failures raise `ValidationError` on first data access.

First data access validates the manifest, then reads and validates the MCP document. The normalized result or exception is cached.

| Property | Type |
| --- | --- |
| `path` | `Path` |
| `schema` | `str` |
| `servers` | `Mapping[str, MCPServer]` |
| `issues` | `tuple[ValidationIssue, ...]` |

String and native path conversion return the configuration path without loading JSON.

See [`mcp.json`](/reference/mcp-json) for server rules and partial validation.

## Normalized values

### `Author`

```python
Author(name: str | None = None, email: str | None = None, url: str | None = None)
```

Frozen author metadata returned by `Manifest.author`.

### `StdioServer`

```python
StdioServer(
    command: str,
    args: tuple[str, ...] = (),
    env: Mapping[str, str] = {},
    cwd: str | None = None,
)
```

Frozen stdio configuration with class attribute `type == "stdio"`. Construction copies `args` to a tuple and `env` to a read-only mapping.

### `StreamableHTTPServer`

```python
StreamableHTTPServer(url: str, headers: Mapping[str, str] = {})
```

Frozen Streamable HTTP configuration with class attribute `type == "streamable-http"` and a copied read-only header mapping.

### `SSEServer`

```python
SSEServer(url: str, headers: Mapping[str, str] = {})
```

Frozen legacy SSE configuration with class attribute `type == "sse"` and a copied read-only header mapping.

### `MCPServer`

```python
MCPServer = StdioServer | StreamableHTTPServer | SSEServer
```

This is a type alias for normalized server values.

Direct value construction provides immutability and normalization of tuple or mapping containers. Obtain values through `MCPConfig.servers` when schema validation is required.

## Diagnostics

### `AgentPluginError`

Base exception for build planning, packaging, discovery, filesystem, and document failures.

### `ValidationIssue`

```python
ValidationIssue(location: tuple[str | int, ...], message: str)
```

Frozen diagnostic value used by fatal errors and non-fatal issue collections.

### `ValidationError`

```python
ValidationError(path: Path, issues: tuple[ValidationIssue, ...])
```

Subclass of `AgentPluginError` for fatal document validation. `issues` must contain at least one value. The exception string renders the first issue.

See [Errors and issues](/reference/errors) for handling patterns.

## `BuildBackend`

Import the low-level adapter from the build package:

```python
from agent_plugins.build import BuildBackend

backend = BuildBackend("example_backend.build")
```

`BuildBackend` is a frozen value with one public field, `module: str`. It exposes `build_wheel`, `build_sdist`, `build_editable`, and the corresponding three `get_requires_for_build_*` hooks.

```python
backend.build_wheel(
    wheel_directory: str,
    config_settings: dict[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str

backend.build_sdist(
    sdist_directory: str,
    config_settings: dict[str, object] | None = None,
) -> str

backend.build_editable(
    wheel_directory: str,
    config_settings: dict[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str

backend.get_requires_for_build_wheel(
    config_settings: dict[str, object] | None = None,
) -> list[str]

backend.get_requires_for_build_sdist(
    config_settings: dict[str, object] | None = None,
) -> list[str]

backend.get_requires_for_build_editable(
    config_settings: dict[str, object] | None = None,
) -> list[str]
```

Each build hook computes a plan from `Path.cwd()`, calls the delegated module, augments the returned artifact, and returns the delegated filename. The delegate must expose all six hooks.

`wheel_directory` and `sdist_directory` identify the output directory supplied by the build frontend. `config_settings` and `metadata_directory` pass through to the delegate unchanged. Each `get_requires_for_build_*` method copies the delegate's sequence into a new list.

The three artifact hooks can raise `AgentPluginError` while planning or rewriting. Delegate imports, missing delegate hooks, and delegate failures keep their original Python exceptions. A delegate creates the artifact before augmentation, so an augmentation failure can leave the unmodified delegate artifact at its output path.
