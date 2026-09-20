# Build variants

## Hatchling

Wrap an existing Hatchling project with the bundled adapter:

```toml
[build-system]
requires = ["agent-plugins", "hatchling"]
build-backend = "agent_plugins.build.hatchling"

[tool.agent-plugins]
root = "."
```

The adapter preserves the delegate's wheel, source distribution, and editable
behavior while adding the selected Agent Plugin and installation marker.

## Monorepo roots

Resolve `root` relative to the `pyproject.toml` that owns the build. For this
layout, the Python package points back to the repository plugin root:

```text
repository/
|-- plugin.json
|-- skills/
`-- packages/
    `-- python/
        `-- pyproject.toml
```

```toml
[tool.agent-plugins]
root = "../.."
```

## Additional selected files

The build always selects `plugin.json`, the complete `skills/` tree, and
`mcp.json` when present. Select other root-relative files explicitly:

```toml
[tool.agent-plugins]
root = "."
include = ["bin/**", "com.example.client/**"]
```

Every include pattern must remain inside the plugin root and match at least one
filesystem entry. A matched directory contributes its regular files.

## Prebuilt wheels

When another backend owns the wheel, attach the configured Agent Plugin after
that build:

```console
agent-plugins attach-wheel dist/my_package-0.1.0-py3-none-any.whl \
  --project .
```

The command atomically replaces the input wheel after the complete attached
artifact succeeds. Use `--output-dir` to preserve the source wheel. The Python
API exposes the same operation:

```python
import agent_plugins as ap

result = ap.attach_wheel(
    "dist/my_package-0.1.0-py3-none-any.whl",
    project=".",
)
print(result.output)
```

A custom delegate must expose wheel, source distribution, and editable build
hooks together with their corresponding `get_requires_for_build_*` hooks.
