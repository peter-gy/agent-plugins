---
title: Python API reference
description: Reference the complete public API for build planning, wheel attachment, discovery, filesystem handles, documents, values, and diagnostics.
---

# Python API reference

Import the top-level API as `agent_plugins`:

```python
import agent_plugins as ap
```

Load the package-selected Agent Plugin and read one named skill:

```python
plugin = ap.Plugin.from_project(".")
skill = plugin.skill("agent-plugins")
print(skill.source)
```

The distribution supports Python 3.10 through 3.14 and ships a `py.typed` marker.

## Build planning

### `build_plan(project=".")`

```python
def build_plan(project: str | Path = ".") -> BuildPlan: ...
```

Reads `[tool.agent-plugins]` from `project/pyproject.toml`, resolves the authored plugin root, and returns the complete ordered file plan.

`project` can be a string or `Path`. It must identify the Python project directory.

Raises `AgentPluginError` for missing configuration, configuration I/O failures, invalid TOML syntax or encoding, invalid settings, an unusable plugin root, unsafe patterns, directory symlinks, missing required files, or selected files that resolve outside the plugin root.

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

## Wheel attachment

### `attach_wheel(wheel, *, project=None, plan=None, output_dir=None)`

```python
def attach_wheel(
    wheel: str | Path,
    *,
    project: str | Path | None = None,
    plan: BuildPlan | None = None,
    output_dir: str | Path | None = None,
) -> WheelAttachment: ...
```

Attaches the selected Agent Plugin to one existing `.whl` file and returns the completed artifact details.

- `wheel` identifies an existing wheel file.
- `project` identifies the Python project containing `[tool.agent-plugins]`. It defaults to the current directory when `plan` is omitted.
- `plan` supplies a validated `BuildPlan` from the caller's configuration source. Attachment reads no project configuration when this value is present.
- `output_dir` identifies an existing directory for the attached artifact. The output keeps the input wheel filename.

Passing both `project` and `plan` raises `AgentPluginError` before artifact access. With no `output_dir`, attachment writes a temporary wheel beside the input and atomically replaces the input after the complete rewrite succeeds. With `output_dir`, it preserves the input and refuses to overwrite an existing destination.

The rewrite validates the wheel structure and member paths, replaces the owned plugin payload and marker, removes invalidated `RECORD.jws` and `RECORD.p7s` signatures, and rebuilds `RECORD`. It preserves the outer file mode, archive comment, and non-owned ZIP members. Running the same plan again replaces the owned payload deterministically.

Planning, validation, plugin-file reads, ZIP writes, and replacement failures leave the input bytes unchanged. Expected project, plan, wheel, ZIP, and filesystem failures raise `AgentPluginError` with the affected path or archive member and a recovery action.

```python
import agent_plugins as ap

result = ap.attach_wheel(
    "dist/example-1.0.0-py3-none-any.whl",
    project="packages/python",
)
print(result.output)
```

### `WheelAttachment`

```python
@dataclass(frozen=True, slots=True)
class WheelAttachment:
    source: Path
    output: Path
    dist_info: PurePosixPath
    plugin_root: PurePosixPath
    files: tuple[PurePosixPath, ...]
    replaced_existing_plugin: bool
    removed_signatures: tuple[PurePosixPath, ...]
```

| Field | Behavior |
| --- | --- |
| `source` | Resolved input wheel path |
| `output` | Resolved attached wheel path |
| `dist_info` | Top-level wheel metadata directory |
| `plugin_root` | Installed `.agent-plugin` directory |
| `files` | Plugin-root-relative targets in `BuildPlan` order |
| `replaced_existing_plugin` | `True` when the input contained its marker or plugin payload |
| `removed_signatures` | Removed `RECORD.jws` and `RECORD.p7s` archive paths |

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

### `Plugin.from_project(project=".")`

```python
@classmethod
def from_project(
    cls,
    project: str | os.PathLike[str] = ".",
) -> Plugin: ...
```

Calls `build_plan(project)` and returns a `Plugin` containing exactly the selected target paths. It honors the staged `.agent-plugin/` root during a source-distribution rebuild.

Use this constructor when Python package selection defines the source boundary. Use `Plugin(path)` to inventory every current regular file below a plugin directory.

Build-plan and selected-inventory failures raise `AgentPluginError`.

### Properties

| Property | Type | Behavior |
| --- | --- | --- |
| `path` | `Path` | Resolved absolute plugin root |
| `files` | `tuple[Path, ...]` | Absolute paths in this handle's selected inventory |
| `manifest` | `Manifest` | Stable lazy handle for `plugin.json` |
| `skills` | `tuple[Skill, ...]` | Immediate selected Agent Skill directories |
| `mcp` | `MCPConfig \| None` | Stable lazy handle when root-level `mcp.json` is selected |

### `plugin.skill(name)`

```python
plugin.skill(name: str) -> Skill
```

Returns the cached immediate `Skill` whose structural directory name matches `name` exactly. `name` must be one non-empty directory component. Absolute values, separators, `.`, `..`, and Windows drive-qualified values raise `AgentPluginError`.

An unavailable name raises `AgentPluginError` with the requested name and sorted available names.

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
| `source` | `str` | Complete exact `SKILL.md` text |

The first access to `source`, `frontmatter`, or `body` reads UTF-8 text, checks delimiter structure, and caches all three strings or the first `ValidationError`. `source` preserves delimiters, line endings, spacing, and final newline state. YAML fields are not parsed.

### `skill.file(relative_path)`

```python
skill.file(relative_path: str | os.PathLike[str]) -> Path
```

Returns one selected regular file below the skill root. The portable relative path must match the selected inventory exactly. Absolute paths, empty paths, `.`, parent traversal, backslashes, directories, unselected files, and paths that resolve outside the root raise `AgentPluginError`.

The method rechecks the current file and containment before returning its absolute inventory path. A file created after the `Skill` handle was constructed remains unselected.

```python
skill / "references" / "api.md"
```

The `/` operator delegates to ordinary unchecked `pathlib.Path` joining. Use `skill.file()` when selection and containment are required.

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

### `mcp.resolve_stdio(name, *, data_dir, base_env=None)`

```python
mcp.resolve_stdio(
    name: str,
    *,
    data_dir: str | os.PathLike[str],
    base_env: Mapping[str, str] | None = None,
) -> ResolvedStdioServer
```

Selects one validated stdio server and returns immutable subprocess inputs. A bare command remains one token. A `./` command becomes a contained absolute path to a regular plugin file. When the `MCPConfig` came from a `Plugin`, the command must also belong to that plugin's selected inventory.

The resolver expands `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` once in arguments, configured environment values, and `cwd`. It copies `base_env`, overlays configured values, then sets the two reserved variables. Environment-name matching follows platform rules.

`data_dir` must already exist as a directory. The caller chooses and retains that location. The caller also owns process creation, permissions, logging, MCP transport, and lifecycle.

An unknown server, non-stdio transport, missing data directory, unavailable plugin-relative command, or invalid working directory raises `AgentPluginError`. Manifest and MCP document failures retain their cached `ValidationError` behavior.

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

### `ResolvedStdioServer`

```python
@dataclass(frozen=True, slots=True)
class ResolvedStdioServer:
    command: str
    args: tuple[str, ...]
    env: Mapping[str, str]
    cwd: Path
```

Contains shell-free subprocess inputs resolved from one stdio declaration. Construction copies `args` to a tuple and `env` to a read-only mapping.

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

Each build hook computes a plan from `Path.cwd()`, calls the delegated module, augments the returned artifact, and returns the delegated filename. `build_wheel()` uses the same regular-wheel operation as `attach_wheel()`. Editable marker attachment remains internal to the adapter. The delegate must expose all six hooks.

`wheel_directory` and `sdist_directory` identify the output directory supplied by the build frontend. `config_settings` and `metadata_directory` pass through to the delegate unchanged. Each `get_requires_for_build_*` method copies the delegate's sequence into a new list.

The three artifact hooks can raise `AgentPluginError` while planning or rewriting. Delegate imports, missing delegate hooks, and delegate failures keep their original Python exceptions. A rewrite failure preserves the artifact bytes returned by the delegate.
