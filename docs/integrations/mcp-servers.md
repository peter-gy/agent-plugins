---
title: MCP servers
description: Package and inspect stdio, Streamable HTTP, and legacy SSE server configuration.
---

# Configure MCP servers

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification) lets an agent client connect to local processes or HTTP endpoints that provide tools and context. Put the server entries in `mcp.json` at the plugin root.

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "records": {
      "type": "stdio",
      "command": "./bin/records-server",
      "args": ["--plugin-root", "${PLUGIN_ROOT}"],
      "env": {
        "CACHE_DIR": "${PLUGIN_DATA}/cache"
      },
      "cwd": "${PLUGIN_ROOT}"
    },
    "catalog": {
      "type": "streamable-http",
      "url": "https://mcp.example.com"
    }
  }
}
```

The build includes root-level `mcp.json` automatically. Add the local executable through `[tool.agent-plugins].include`.

## Choose a transport

| Type | Configuration | Intended endpoint |
| --- | --- | --- |
| `stdio` | `command`, optional `args`, `env`, and `cwd` | A local process started by the agent client |
| `streamable-http` | `url` and optional `headers` | A Streamable HTTP endpoint |
| `sse` | `url` and optional `headers` | A legacy HTTP plus Server-Sent Events endpoint |

`agent-plugins` validates the configuration and resolves stdio declarations into subprocess inputs. The agent client supplies permissions, starts local processes, opens transports, and manages writable plugin data.

## Reference packaged paths

Agent clients provide two reserved runtime locations:

- `${PLUGIN_ROOT}` identifies the active installed plugin root.
- `${PLUGIN_DATA}` identifies a client-managed writable data directory.

The parser preserves placeholder strings. It accepts `cwd` values equal to either placeholder, below either placeholder, or beginning with `./` for a plugin-relative directory. `resolve_stdio()` expands the placeholders once and rejects paths that escape the plugin root or plugin data directory.

A stdio command can be a bare executable name such as `python` or a plugin-relative value beginning with `./`. Other command paths are rejected. `resolve_stdio()` preserves a bare command as one token and resolves a plugin-relative command to a regular file inside the plugin root. Configuration obtained through `plugin.mcp` also requires that file in the plugin's selected inventory.

`env` cannot define the reserved names `PLUGIN_ROOT` or `PLUGIN_DATA`.

## Resolve a stdio launch

Create the plugin data directory according to the client application's storage policy, then resolve one validated server:

```python
from pathlib import Path
import os
import subprocess

import agent_plugins as ap

plugin = ap.locate("my-project")
data_dir = Path(".agent-data/my-project").resolve()
data_dir.mkdir(parents=True, exist_ok=True)

mcp = plugin.mcp
if mcp is None:
    raise RuntimeError("The plugin has no MCP configuration")

launch = mcp.resolve_stdio(
    "records",
    data_dir=data_dir,
    base_env={"PATH": os.environ.get("PATH", "")},
)

process = subprocess.Popen(
    [launch.command, *launch.args],
    cwd=launch.cwd,
    env=dict(launch.env),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=None,
)
```

`ResolvedStdioServer` contains a command token, argument tuple, read-only environment mapping, and absolute working directory. Placeholder expansion applies to arguments, configured environment values, and `cwd`. It leaves the command and non-reserved environment keys unchanged. Platform-equivalent reserved keys are replaced by canonical `PLUGIN_ROOT` and `PLUGIN_DATA` entries.

The caller creates and retains `PLUGIN_DATA`, chooses the base environment, starts the process, and owns permissions, logging, shutdown, and the MCP handshake. `resolve_stdio()` performs no process or network work.

## Connect to HTTP safely

Remote MCP URLs must use HTTPS. Plain HTTP is accepted for `localhost` and loopback IP addresses.

URLs with user information, fragments, spaces, control characters, backslashes, invalid percent escapes, or invalid ports are rejected. Header names use the HTTP token character set, and names must be unique without regard to case. Header values accept tab, printable ASCII, and characters through U+00FF. Newlines, DEL, other disallowed control characters, and non-Latin-1 Unicode are rejected.

Keep credentials in the agent client's secret mechanism. `mcp.json` is packaged content and can be read by anyone with access to the distribution.

## Inspect valid entries and issues

```python
import agent_plugins as ap

plugin = ap.locate("my-project")

if plugin.mcp is not None:
    for name, server in plugin.mcp.servers.items():
        print(name, server.type, server)

    for issue in plugin.mcp.issues:
        print(issue.location, issue.message)
```

A fatal top-level or schema error raises `ValidationError`. An invalid individual server entry is skipped and recorded in `mcp.issues`, so valid sibling entries remain available.

See the complete [`mcp.json` reference](/reference/mcp-json) for field defaults and validation rules.
