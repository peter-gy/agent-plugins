# Discovery and validation

Project and installed discovery create a bounded filesystem inventory first. Document parsing happens when a caller requests content.

## Project selection

`Plugin.from_project(project)` calls `build_plan(project)`, then constructs a `FileInventory` from its root and target paths. This makes source inspection use the same selection as wheel creation. Direct `Plugin(path)` construction continues to inventory the complete directory tree.

## Installed discovery

`locate(distribution_name)` asks `importlib.metadata` for one Python distribution and reads its `agent_plugins.json` file. A relative marker root resolves through `Distribution.locate_file()`. An absolute root supports editable installs.

`installed()` selects the first visible installation of each normalized distribution name, then skips unmarked entries and sorts the result by distribution name without regard to case. This preserves `importlib.metadata` precedence even when an unmarked installation shadows a marked one. It is fail-fast. An invalid selected marked distribution aborts the complete scan.

The distribution name remains independent from the manifest plugin name.

## File inventory

`FileInventory` keeps one resolved root and sorted tuple of validated relative paths.

Direct `Plugin(path)` and `Skill(path)` construction discovers every current regular file. Project and installed discovery select build-plan or marker-listed paths.

Relative names reject absolute paths, `.`, parent traversal, and backslashes. Every selected path must exist, be a regular file, and resolve inside the inventory root. Runtime ordering uses case-folded POSIX path followed by original POSIX path.

`Plugin.skills` recognizes exact three-part paths of the form `skills/<name>/SKILL.md`. `Plugin.mcp` exists when the selected inventory contains exact root-level `mcp.json`.

`Plugin.skill(name)` selects a cached immediate skill by its structural directory name. `Skill.file(path)` requires exact inventory membership and rechecks the regular-file and containment boundary at access time.

## Lazy document cache

`LazyResult` evaluates a loader once under a lock. It caches either the returned value or the raised exception, then releases its loader reference.

A `BaseException` interruption before a value or ordinary exception is cached releases the lock and retains the loader for a retry.

The two state boundaries are:

1. `Plugin` and `Skill` construction captures the selected file inventory.
2. First manifest, MCP, or skill content access captures the document value or error.

A new handle refreshes document content. An editable reinstall is also required when the selected filenames change.

Inventory-bound manifest, MCP, and skill loaders recheck the document's containment immediately before the first read. A failed check becomes a cached `ValidationError`. Native paths remain ordinary filesystem paths, and validation is not an atomic filesystem sandbox.

## Manifest validation

`Manifest` dispatches by exact `$schema` identifier. The current loader accepts Agent Plugins 1.0.0.

Unknown top-level fields and a non-object top-level `extensions` value become non-fatal issues. Other structural and typed failures raise `ValidationError` at the first detected issue.

Normalized nested extension objects become read-only mappings and arrays become tuples.

## MCP validation

`MCPConfig` validates its associated manifest before reading `mcp.json`. The schema dispatch table pairs each MCP schema identifier with its required manifest schema identifier and loader.

Top-level MCP failures are fatal. Each server entry is isolated. An invalid entry is skipped and recorded as one issue at `("mcpServers", name)`.

The versioned loader owns:

- Closed field sets for stdio and HTTP server entries.
- Plugin-root containment for `./` commands and working directories.
- `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` working-directory forms.
- Reserved environment keys.
- HTTPS requirements for non-loopback endpoints.
- URL user-information, fragment, escaping, whitespace, and port checks.
- HTTP header name, value, and case-insensitive uniqueness checks.

The loader preserves placeholder strings. `MCPConfig.resolve_stdio()` delegates to `_mcp.py`, which applies one-pass placeholder expansion, resolves selected plugin commands and working directories, and returns immutable subprocess inputs. Runtime resolution is uncached because it depends on the caller's data directory, base environment, and current filesystem.

Process creation, permissions, transport connection, authentication, logging, and the MCP handshake remain client-owned.

## Skill document structure

`SkillDocument` reads UTF-8 text once and splits at exact `---` delimiter lines. It preserves the complete source plus all text between and after those delimiters.

It does not parse YAML or enforce Agent Skills names, descriptions, field types, lengths, or directory-name parity. Keep this limited contract explicit when adding validation or documentation.

## Diagnostics

`ValidationError` extends `AgentPluginError` and contains the document path plus a non-empty issue tuple. Its text renders the first location with a JSONPath-like `$` prefix.

`ValidationIssue` is also used for non-fatal manifest and MCP results. Callers must inspect `.issues` to observe those outcomes.
