# Artifact lifecycle

Configuration adapters produce a validated `BuildPlan`. `attach_wheel()` consumes a plan and rewrites one regular wheel. `BuildBackend` obtains the same plan before delegation, then calls the regular wheel operation or the internal source-distribution and editable-wheel writers.

## Build plan

`build_plan(project)` resolves the Python project directory and loads `[tool.agent-plugins]` from `pyproject.toml`.

The configured `root` resolves from that directory. When `project/.agent-plugin/plugin.json` exists, the staged directory takes precedence. This is how a wheel rebuilt from a source distribution selects the payload captured in that source distribution.

For an authored root, the plan adds required `plugin.json`, an optional recursive `skills/` tree, optional root-level `mcp.json`, and every `include` match. For a staged root, it inventories the complete captured payload. Authored include patterns have already selected that payload. Target keys deduplicate mappings and sort by raw POSIX path.

Selection rejects directory symlinks, paths that resolve outside the plugin root, absolute include patterns, parent traversal, and backslashes. File symlinks remain acceptable when their targets resolve inside the root.

Supplied plans are checked before wheel rewriting. Targets must be unique portable file paths, must include `plugin.json`, and must have readable regular sources. NUL characters and file-directory target collisions are rejected.

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

`attach_wheel()` resolves one existing `.whl` file. When `plan` is absent, it calls `build_plan(project or Path.cwd())`. Passing both values fails before artifact access. A supplied plan bypasses project configuration.

The wheel must contain exactly one top-level `.dist-info/WHEEL` member plus sibling `METADATA` and `RECORD` members. Duplicate names, absolute names, parent traversal, and backslashes are rejected. The `.dist-info` stem determines the plugin directory name:

```text
<distribution>-<version>.agent-plugin/
```

`wheel.py` owns the operation and publication. `wheel_archive.py` inspects the ZIP layout, replaces the owned plugin directory, `agent_plugins.json`, `RECORD`, and `RECORD` signature files, and copies every other member with its bytes and relevant `ZipInfo` metadata. It preserves the archive comment, writes the selected plugin payload in plan order, writes a compact marker, then creates a new `RECORD`.

Added members use the ZIP epoch timestamp, deflate compression, and source permission bits. `RECORD` contains one row per non-directory member. Its hashes use SHA-256 with URL-safe base64 and no padding. The `RECORD` row itself has empty hash and size fields.

`RECORD.jws` and `RECORD.p7s` are invalid after mutation. The rewrite omits them and returns their archive paths through `WheelAttachment.removed_signatures`.

The rewrite uses a temporary file in the destination directory and applies the source artifact mode before publication. In-place attachment replaces the source after the complete rewrite succeeds. `output_dir` preserves the source, keeps its filename, and uses a no-clobber publish operation. Planning, validation, source reads, ZIP writing, and publication failures leave the source bytes unchanged. Temporary artifacts are cleaned after success and failure.

Ownership uses installation paths as well as top-level archive paths. Payloads and markers under wheel `.data/purelib/` and `.data/platlib/` locations are replaced when they install into the owned plugin or marker path. Conflicting relocated distribution metadata is rejected before publication.

An existing marker or matching plugin payload sets `replaced_existing_plugin`. The rewrite removes that owned state before writing the current plan. Repeating the same attachment is byte-deterministic.

## Source distribution rewrite

The source artifact must be a `.tar.gz` archive with one safe top-level directory. Absolute paths, parent traversal, or multiple roots are rejected.

The rewrite compares canonical member paths to replace the complete `<archive-root>/.agent-plugin/` subtree, then adds the planned payload there. New members preserve source modes and modification times while normalizing user and group identifiers to zero. The gzip header timestamp is zero. Temporary replacement also preserves the source distribution's outer file mode.

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
