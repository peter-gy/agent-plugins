---
title: Attach a prebuilt wheel
description: Add the configured Agent Plugin to a wheel produced by another build tool.
---

# Attach a prebuilt wheel

Run `attach-wheel` after another build tool creates a wheel:

```console
agent-plugins attach-wheel dist/example-1.0.0-py3-none-any.whl --project .
```

The command reads `[tool.agent-plugins]`, rewrites the wheel in place, and prints its absolute path. The Python API performs the same operation:

```python
import agent_plugins as ap

result = ap.attach_wheel(
    "dist/example-1.0.0-py3-none-any.whl",
    project=".",
)
print(result.output)
```

Use a [build-backend adapter](/guide/build-backends) when `agent-plugins` owns the Python build path. Use `attach_wheel()` or `attach-wheel` when another tool already produced the wheel.

## Choose the build plan

When `project` is omitted, `attach_wheel()` reads `[tool.agent-plugins]` from the current directory. Pass another Python project directory when its `pyproject.toml` owns the configuration:

```python
result = ap.attach_wheel(
    "dist/example-1.0.0-py3-none-any.whl",
    project="packages/python",
)
```

A caller with another configuration source can supply a validated `BuildPlan`. A project integration can also reuse a plan it computed earlier:

```python
plan = ap.build_plan("packages/python")
result = ap.attach_wheel(
    "dist/example-1.0.0-py3-none-any.whl",
    plan=plan,
)
```

Passing both `project` and `plan` raises `AgentPluginError` before the wheel changes.

## Preserve the source wheel

Pass `output_dir` to keep the input wheel and write the attached artifact under the same filename:

```python
from pathlib import Path

Path("dist/attached").mkdir(parents=True, exist_ok=True)
result = ap.attach_wheel(
    "dist/example-1.0.0-py3-none-any.whl",
    plan=plan,
    output_dir="dist/attached",
)
```

```console
mkdir -p dist/attached
agent-plugins attach-wheel dist/example-1.0.0-py3-none-any.whl \
  --project . \
  --output-dir dist/attached
```

The output directory must exist. Attachment refuses to replace an existing destination. Keeping the original filename preserves its agreement with the wheel metadata and compatibility tags.

Without `output_dir`, attachment writes a temporary wheel beside the input and replaces the input after the complete rewrite succeeds. Planning, validation, source-file reads, ZIP writes, and replacement failures leave the input bytes unchanged.

## Inspect the result

`WheelAttachment` reports the resolved source and output paths, the wheel metadata directory, the installed plugin root, the ordered plugin-relative files, whether an owned plugin was replaced, and any invalidated signature files that were removed.

```python
print(result.files)
print(result.replaced_existing_plugin)
print(result.removed_signatures)
```

Use `--json` for the same fields as one stable object. The command writes signature-removal warnings to stderr so stdout remains valid JSON.

Attachment replaces the wheel's existing `agent_plugins.json` marker and matching `.agent-plugin` payload. Running the operation again with the same plan produces the same attached wheel bytes. The rewrite preserves the outer file mode, ZIP archive comment, and non-owned members. It rebuilds `RECORD` with current SHA-256 hashes and sizes.

`RECORD.jws` and `RECORD.p7s` signatures no longer match after a wheel changes. Attachment removes them, records their paths in `removed_signatures`, and warns when the CLI encounters them.

Missing files, invalid project configuration, malformed wheels, unsafe archive paths, unreadable plugin sources, and destination failures raise `AgentPluginError`. Correct the reported path or rebuild the input wheel, then rerun the same command.

## Run after an external build

Keep wheel selection in the build or continuous integration job. For example, a [Maturin](https://www.maturin.rs/) workflow can attach the configured plugin after producing its platform wheel:

```console
uv run --with "agent-plugins==<released-version>" \
  agent-plugins attach-wheel dist/example.whl --project .
```

Install and inspect the attached artifact before publishing it. See [Verify an Agent Plugin package](/guide/verify-package) for the artifact checks.
