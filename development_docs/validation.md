# Discovery and validation

Installed discovery creates a bounded filesystem inventory first. Document parsing happens when a caller requests content.

## Installed discovery

`locate(distribution_name)` asks `importlib.metadata` for one Python distribution and reads its `agent_plugins.json` file. A relative marker root resolves through `Distribution.locate_file()`. An absolute root supports editable installs.

`installed()` scans every visible distribution, skips unmarked entries, and sorts the result by distribution name without regard to case. It is fail-fast. One invalid marked distribution aborts the complete scan.

The distribution name remains independent from the manifest plugin name.

## File inventory

`FileInventory` keeps one resolved root and sorted tuple of validated relative paths.

Direct `Plugin(path)` and `Skill(path)` construction discovers every current regular file. Installed discovery selects only marker-listed paths.

Relative names reject absolute paths, `.`, parent traversal, and backslashes. Every selected path must exist, be a regular file, and resolve inside the inventory root. Runtime ordering uses case-folded POSIX path followed by original POSIX path.

`Plugin.skills` recognizes exact three-part paths of the form `skills/<name>/SKILL.md`. `Plugin.mcp` exists when the selected inventory contains exact root-level `mcp.json`.

## Lazy document cache

`LazyResult` evaluates a loader once under a lock. It caches either the returned value or the raised exception, then releases its loader reference.

The two state boundaries are:

1. `Plugin` and `Skill` construction captures the selected file inventory.
2. First manifest, MCP, or skill content access captures the document value or error.

A new handle refreshes document content. An editable reinstall is also required when the selected filenames change.

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

The loader preserves placeholder strings. It does not expand them, inspect executable availability, open a transport, authenticate, or perform an MCP handshake.

## Skill document structure

`SkillDocument` reads UTF-8 text and splits at exact `---` delimiter lines. It preserves all source text between and after those delimiters.

It does not parse YAML or enforce Agent Skills names, descriptions, field types, lengths, or directory-name parity. Keep this limited contract explicit when adding validation or documentation.

## Diagnostics

`ValidationError` extends `AgentPluginError` and contains the document path plus a non-empty issue tuple. Its text renders the first location with a JSONPath-like `$` prefix.

`ValidationIssue` is also used for non-fatal manifest and MCP results. Callers must inspect `.issues` to observe those outcomes.
