# Artifact lifecycle

The build-backend adapter computes the Agent Plugin build plan before asking its delegate to create an artifact. It then rewrites the returned wheel or source distribution.

## Build plan

`build_plan(project)` resolves the Python project directory and loads `[tool.agent-plugins]` from `pyproject.toml`.

The configured `root` resolves from that directory. When `project/.agent-plugin/plugin.json` exists, the staged directory takes precedence. This is how a wheel rebuilt from a source distribution selects the payload captured in that source distribution.

The plan adds required `plugin.json`, an optional recursive `skills/` tree, optional root-level `mcp.json`, and every `include` match. Target keys deduplicate mappings and sort by raw POSIX path.

Selection rejects directory symlinks, paths that resolve outside the plugin root, absolute include patterns, parent traversal, and backslashes. File symlinks remain acceptable when their targets resolve inside the root.

## Backend delegation

`BuildBackend(module)` imports the delegate by module name for each hook call. The delegate contract contains six methods:

- `build_wheel`
- `build_sdist`
- `build_editable`
- `get_requires_for_build_wheel`
- `get_requires_for_build_sdist`
- `get_requires_for_build_editable`

The bundled adapters bind this wrapper to `uv_build` and `hatchling.build`.

The wrapper passes `config_settings` and `metadata_directory` through unchanged. It returns the filename produced by the delegate after augmenting the artifact.

## Regular wheel rewrite

The wheel must contain exactly one top-level `.dist-info/WHEEL` member. Its stem determines the plugin directory name:

```text
<distribution>-<version>.agent-plugin/
```

The rewrite removes any existing owned plugin directory, `agent_plugins.json`, `RECORD`, and `RECORD` signature files. It copies other members, writes the selected plugin payload, writes a compact marker, then creates a new `RECORD`.

Added members use the ZIP epoch timestamp, deflate compression, and source permission bits. `RECORD` hashes use SHA-256 with URL-safe base64 and no padding. The `RECORD` row itself has empty hash and size fields.

The rewrite uses a temporary file in the output directory and replaces the delegated wheel after success. A rewrite failure can leave the unaugmented delegated artifact at its original output path.

## Source distribution rewrite

The source artifact must be a `.tar.gz` archive with one safe top-level directory. Absolute paths, parent traversal, or multiple roots are rejected.

The rewrite replaces any existing `<archive-root>/.agent-plugin/` subtree and adds the planned payload there. New members preserve source modes and modification times while normalizing user and group identifiers to zero. The gzip header timestamp is zero.

The staged payload ensures that a later wheel rebuild carries the same selected plugin bytes. Complete wheel byte reproducibility remains owned by the delegated backend and source metadata.

## Editable wheel rewrite

An editable wheel receives `agent_plugins.json` but no copied plugin directory. The marker stores the absolute authored plugin root and the filenames selected by the install-time plan.

Existing selected files remain live through their source paths. Filename additions, deletions, and moves require reinstalling the editable distribution so the marker can be rebuilt.

## Marker format

`agent_plugins.json` is compact UTF-8 JSON with a trailing newline:

```json
{"root":"demo-1.0.0.agent-plugin","files":["plugin.json","skills/demo/SKILL.md"]}
```

Regular wheels use a distribution-relative `root`. Editable wheels use an absolute `root`. Missing `files` identifies an outdated marker and produces a reinstall diagnostic during discovery.

## Self-hosting

This repository uses `backend-path = ["src"]` and `agent_plugins.build.uv_build`. The local source therefore provides its own adapter during the build. Consumer projects install `agent-plugins` through `[build-system].requires`.
