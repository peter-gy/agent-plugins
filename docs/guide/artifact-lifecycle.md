---
title: How packaging works
description: Follow Agent Plugin files through build planning, wheels, source distributions, editable installs, and discovery.
---

# How packaging works

The built distribution is one release boundary for library code and agent instructions. The build-backend adapter asks the configured Python backend to create an artifact, then augments that artifact with Agent Plugin metadata and files selected from the same source revision.

Run library tests and evaluate the skills against that artifact before publishing it. Installing or rolling back one distribution version moves the packaged code and Agent Skills together.

A [wheel](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) is the archive installed into a Python environment. A [source distribution](https://packaging.python.org/en/latest/specifications/source-distribution-format/), or sdist, carries source files that a build frontend can turn into a wheel.

## Build planning

Every wheel, source distribution, and editable build starts with `build_plan()` in the Python project directory.

The plan resolves `[tool.agent-plugins].root` and selects:

1. `plugin.json` at the plugin root.
2. Every file under `skills/`, when that directory exists.
3. `mcp.json`, when it exists at the plugin root.
4. Files and directory trees matched by `include` patterns.

Each `FileMapping` contains an absolute source `Path` and a plugin-root-relative `PurePosixPath` target. A POSIX path uses forward slashes so the artifact path stays stable across operating systems. Duplicate targets collapse into one mapping. Targets are sorted by their POSIX string.

Build planning validates the selection boundary. Document content is read through the inspection API after installation, or through another validator before release.

## Regular wheels

A regular wheel contains the selected files in a sibling directory named from the wheel's distribution metadata:

```text
site-packages/
├── my_project/
├── my_project-0.1.0.dist-info/
│   ├── agent_plugins.json
│   └── ...
└── my_project-0.1.0.agent-plugin/
    ├── plugin.json
    └── skills/
```

The adapter updates the wheel [`RECORD`](https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file), the metadata table that lists installed paths, hashes, and byte sizes. Added files preserve executable mode bits.

The built distribution receives no runtime dependency on `agent-plugins` unless you declare one in `[project].dependencies`.

## Source distributions

A source distribution, or sdist, carries the selected files under a reserved `.agent-plugin/` staging directory.

When a build frontend reconstructs a wheel from the sdist, `build_plan()` selects this staged copy. The rebuilt wheel therefore carries the same Agent Plugin payload as the source checkout used for the original sdist.

## Editable installs

An editable wheel stores an absolute path to the authored plugin root in `agent_plugins.json`. It records the selected relative filenames and does not copy the plugin directory into the wheel.

Edits to an already selected file appear on the next document read through a fresh handle. Adding or removing files changes the build plan, so reinstall the editable distribution to refresh the `agent_plugins.json` file inventory. See [Editable installs](/guide/editable-installs) for the complete lifecycle.

## Installed discovery

`locate(distribution_name)` uses Python distribution metadata to find the `agent_plugins.json` marker. It contains:

- `root`: a relative installed directory for regular wheels, or an absolute authored root for editable wheels.
- `files`: the exact plugin-root-relative paths selected when the artifact was built.

Discovery resolves and validates every selected path before constructing a `Plugin` handle. It rejects missing files, directories listed as files, path traversal, backslashes, and paths that resolve outside the plugin root.

The resulting file inventory stays fixed for that handle. Parsed manifest, MCP, and skill contents have a second cache boundary described in [Validation and caching](/guide/validation).
