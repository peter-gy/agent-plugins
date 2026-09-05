---
title: Client extension files
description: Select client-owned files and distinguish them from extension data in plugin.json.
---

# Include client extension files

An agent client can define files beyond the portable `plugin.json`, `skills/`, and `mcp.json` locations. Keep those files under a client-owned directory in the plugin root and select them with `include`.

```text
my-project/
├── plugin.json
└── com.example.client/
    ├── hooks/
    │   └── validate.py
    └── settings.json
```

```toml
[tool.agent-plugins]
root = "../.."
include = ["com.example.client/**"]
```

The build plan preserves the paths relative to the plugin root. `plugin.files` exposes their installed absolute paths.

## Extension files and manifest data

Client extension files and `plugin.json.extensions` are separate integration surfaces.

| Surface | Shape | Access |
| --- | --- | --- |
| Client extension files | Files and directories selected by include patterns | `plugin.files` and native paths below `plugin.path` |
| Manifest extension data | Namespaced JSON objects inside `plugin.json` | `plugin.manifest.extensions` |

Use manifest extension data for small declarative settings:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "my-project",
  "extensions": {
    "com.example.client": {
      "entrypoint": "com.example.client/hooks/validate.py"
    }
  }
}
```

The parser preserves each namespace object as immutable nested mappings and tuples. It does not interpret client-specific keys or require a matching extension directory.

Use include patterns for executable code, templates, schemas, and other file-backed resources. The agent client owns their meaning and activation.
