---
title: Verify a package
description: Check file selection, document access, wheel contents, source rebuilds, and editable discovery before publishing.
---

# Verify an Agent Plugin package

Verify each boundary that a package consumer depends on. A successful build plan proves file selection, while installed inspection proves the final artifact and document access.

## 1. Inspect file selection

```console
uv run --with agent-plugins agent-plugins plan packages/python --json
```

Check the authored plugin root and every target path. The plan should contain `plugin.json`, the intended Agent Skills, optional `mcp.json`, and selected client extension files.

## 2. Validate authored documents

Construct a direct `Plugin` handle and access the fields your consumers use:

```python
import agent_plugins as ap

plugin = ap.Plugin.from_project("packages/python")
print(plugin.manifest.name)
print(plugin.manifest.issues)

for skill in plugin.skills:
    print(skill.frontmatter)

if plugin.mcp is not None:
    print(plugin.mcp.servers)
    print(plugin.mcp.issues)
```

This validates the supported Agent Plugins JSON fields and the `SKILL.md` text structure. Use an [Agent Skills](https://agentskills.io/specification) validator to check YAML fields and other Agent Skills rules.

## 3. Create the artifacts

With a build-backend adapter, build the wheel and source distribution:

```console
uv build packages/python --out-dir dist
```

The output should contain one wheel and one `.tar.gz` source distribution.

When another build tool owns the wheel, attach the Agent Plugin after that build. Use a separate output directory when you want to compare the source and attached artifacts:

```console
mkdir -p dist/attached
agent-plugins attach-wheel dist/my_project-0.1.0-py3-none-any.whl \
  --project packages/python \
  --output-dir dist/attached \
  --json
```

Inspect `files`, `replaced_existing_plugin`, and `removed_signatures` in the result. Install `dist/attached/my_project-0.1.0-py3-none-any.whl` in the remaining checks.

## 4. Rebuild from the source distribution

For the build-backend path, build a wheel from the source distribution into a separate directory:

```console
uv build \
  --wheel dist/my_project-0.1.0.tar.gz \
  --out-dir dist/from-sdist
```

The rebuilt wheel should expose the same Agent Plugin target paths as the direct wheel.

## 5. Inspect a clean installation

Set the wheel path for the artifact workflow:

```console
wheel=dist/my_project-0.1.0-py3-none-any.whl
```

For an external build with the separate attachment directory, use:

```console
wheel=dist/attached/my_project-0.1.0-py3-none-any.whl
```

Install the selected wheel in an isolated temporary environment and inspect it:

```console
uv run --no-project --isolated --no-cache \
  --with agent-plugins \
  --with "$wheel" \
  agent-plugins locate my-project

uv run --no-project --isolated --no-cache \
  --with agent-plugins \
  --with "$wheel" \
  agent-plugins list --json
```

For the build-backend path, repeat the commands with `dist/from-sdist/my_project-0.1.0-py3-none-any.whl`. Then access `plugin.manifest.name`, each skill document, and `plugin.mcp.servers` from Python. File location and document validation are separate checks.

## 6. Inspect an editable installation

```console
uv run --no-project --isolated --no-cache \
  --with agent-plugins \
  --with-editable packages/python \
  agent-plugins locate my-project
```

Confirm that the root points to the authored directory. In a persistent editable environment, add a file, reinstall the editable distribution, and confirm that a new handle includes the new path.

Package-specific projects can automate these checks around their own build command. This repository's contributor workflow is documented in [`development_docs/testing-and-release.md`](https://github.com/peter-gy/agent-plugins/blob/main/development_docs/testing-and-release.md).
