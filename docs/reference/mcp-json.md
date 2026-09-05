---
title: mcp.json reference
description: Reference MCP configuration fields, transport values, path rules, URL rules, and validation outcomes.
---

# `mcp.json` reference

`mcp.json` is the optional Model Context Protocol configuration at the plugin root. `agent-plugins` recognizes the 1.0.0 schema identifier exactly.

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {}
}
```

## Top-level fields

| Field | Required | Contract |
| --- | --- | --- |
| `$schema` | Yes | `https://agent-plugins.org/schemas/1.0.0/mcp.schema.json` |
| `mcpServers` | Yes | Object keyed by server name |

The top-level schema is closed. An unknown field, invalid JSON shape, missing required field, unsupported schema identifier, or mismatch with the manifest schema raises `ValidationError`.

The associated manifest is validated before the MCP document.

## `stdio`

```json
{
  "type": "stdio",
  "command": "./bin/server",
  "args": ["--root", "${PLUGIN_ROOT}"],
  "env": {
    "CACHE_DIR": "${PLUGIN_DATA}/cache"
  },
  "cwd": "${PLUGIN_ROOT}"
}
```

| Field | Required | Default | Contract |
| --- | --- | --- | --- |
| `type` | Yes |  | Exact string `stdio` |
| `command` | Yes |  | Non-empty bare name or plugin-relative value beginning with `./` |
| `args` | No | `[]` | Array of strings, exposed as a tuple |
| `env` | No | `{}` | Object with string values, exposed as a read-only mapping |
| `cwd` | No | `null` | Accepted working-directory form |

A bare command contains no slash, backslash, or NUL. A `./` command must resolve inside the plugin root. Existence and executability are runtime concerns for the agent client.

`env` cannot define the exact reserved keys `PLUGIN_ROOT` or `PLUGIN_DATA`.

Accepted `cwd` forms are:

- A plugin-relative path beginning with `./`.
- `${PLUGIN_ROOT}` or a path below it.
- `${PLUGIN_DATA}` or a path below it.

Traversal outside either managed root is rejected. An unknown stdio field invalidates the server entry.

The normalized value is `StdioServer(command, args=(), env={}, cwd=None)` with class attribute `type == "stdio"`.

## `streamable-http`

```json
{
  "type": "streamable-http",
  "url": "https://mcp.example.com",
  "headers": {
    "X-Client": "my-project"
  }
}
```

The normalized value is `StreamableHTTPServer(url, headers={})` with class attribute `type == "streamable-http"`.

## `sse`

```json
{
  "type": "sse",
  "url": "https://mcp.example.com/events"
}
```

The normalized value is `SSEServer(url, headers={})` with class attribute `type == "sse"`. This type represents the legacy HTTP plus Server-Sent Events transport.

## HTTP URL rules

Streamable HTTP and SSE entries share these rules:

- URLs are absolute HTTP or HTTPS URLs with a host.
- Plain HTTP is accepted for `localhost` and loopback IP addresses.
- URLs cannot contain user information or fragments.
- Backslashes, spaces, control characters, invalid percent escapes, and invalid ports are rejected.
- `headers` is an optional object with string values.
- Header names use the HTTP token character set and are unique without regard to case.
- Header values accept tab, U+0020 through U+007E, and U+0080 through U+00FF. Other characters are rejected.
- Unknown fields invalidate the server entry.

## Partial server validation

Each server entry validates independently. An invalid entry is omitted from `MCPConfig.servers` and contributes one `ValidationIssue` to `MCPConfig.issues` at `("mcpServers", server_name)`.

```python
mcp = plugin.mcp
if mcp is not None:
    print(mcp.schema)
    print(mcp.servers)
    print(mcp.issues)
```

A document with no valid server entries still loads successfully when its top-level shape is valid.
