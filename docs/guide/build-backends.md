---
title: Build backends
description: Add Agent Plugin packaging to uv_build, Hatchling, or another compatible Python build backend.
---

# Configure a build-backend adapter

An `agent-plugins` build-backend adapter delegates the Python package build, then augments the returned artifact. A regular wheel receives packaged plugin files and the `agent_plugins.json` marker. A source distribution receives staged plugin files. An editable wheel receives a marker that points at the authored plugin root.

## uv_build

Use the bundled uv_build adapter for projects that already build with [uv_build](https://docs.astral.sh/uv/concepts/build-backend/):

```toml
[build-system]
requires = ["agent-plugins", "uv_build"]
build-backend = "agent_plugins.build.uv_build"

[tool.agent-plugins]
root = "../.."
```

The adapter exposes the wheel, source distribution, and editable hooks from uv_build.

## Hatchling

Use the bundled Hatchling adapter for projects built with [Hatchling](https://hatch.pypa.io/latest/config/build/):

```toml
[build-system]
requires = ["agent-plugins", "hatchling"]
build-backend = "agent_plugins.build.hatchling"

[tool.agent-plugins]
root = "../.."
```

Both adapters apply the same Agent Plugin build plan and artifact layout. Backend-specific Python package settings remain owned by uv_build or Hatchling.

## Build-time and runtime dependencies

Keep `agent-plugins` in `[build-system].requires` when it is needed during builds.

Add it to runtime dependencies when installed Python code calls the inspection API:

```toml
[project]
dependencies = ["agent-plugins"]
```

The adapter does not add this runtime dependency automatically.

## Wrap another backend

`agent_plugins.build.BuildBackend` is the low-level adapter used by the two bundled modules:

```python
from agent_plugins.build import BuildBackend

backend = BuildBackend("example_backend.build")

build_wheel = backend.build_wheel
build_sdist = backend.build_sdist
build_editable = backend.build_editable
get_requires_for_build_wheel = backend.get_requires_for_build_wheel
get_requires_for_build_sdist = backend.get_requires_for_build_sdist
get_requires_for_build_editable = backend.get_requires_for_build_editable
```

The delegated module must expose all six hooks shown in the example. The adapter resolves the build plan from the current working directory before delegating each artifact build.

Use the bundled modules when possible. A custom wrapper takes responsibility for backend hook compatibility and integration testing.
