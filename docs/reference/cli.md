---
title: CLI reference
description: Reference agent-plugins plan, locate, and list commands, output formats, and exit statuses.
---

# CLI reference

The `agent-plugins` command previews package file selection and locates Agent Plugins visible in the current Python environment.

```text
agent-plugins {plan,locate,list} ...
```

`python -m agent_plugins` runs the same entry point.

## `agent-plugins plan`

```text
agent-plugins plan [PROJECT] [--json]
```

`PROJECT` is the Python project directory containing `pyproject.toml`. It defaults to the current directory.

Human output is tab-delimited:

```text
root    /absolute/plugin/root
plugin.json    /absolute/plugin/root/plugin.json
skills/example/SKILL.md    /absolute/plugin/root/skills/example/SKILL.md
```

`--json` writes one object:

```json
{
  "project": "/absolute/python/project",
  "root": "/absolute/plugin/root",
  "files": [
    {
      "source": "/absolute/plugin/root/plugin.json",
      "target": "plugin.json"
    }
  ]
}
```

`project`, `root`, and `source` are absolute native path strings. `target` is a plugin-root-relative POSIX path.

`plan` checks configuration and selected files. It does not parse `plugin.json`, `mcp.json`, or `SKILL.md`.

## `agent-plugins locate`

```text
agent-plugins locate DISTRIBUTION
```

`DISTRIBUTION` is an installed Python distribution name. Success writes the absolute plugin root and a newline to stdout.

## `agent-plugins list`

```text
agent-plugins list [--json]
```

Human output contains one distribution line followed by its skill instruction paths:

```text
my-project    /absolute/my_project-1.0.0.agent-plugin
    skill    /absolute/my_project-1.0.0.agent-plugin/skills/example/SKILL.md
```

The command uses tabs for indentation and columns. An environment with no marked distributions prints no human output.

`--json` writes an array sorted by distribution name without regard to case:

```json
[
  {
    "distribution": "my-project",
    "root": "/absolute/my_project-1.0.0.agent-plugin",
    "skills": [
      "/absolute/my_project-1.0.0.agent-plugin/skills/example/SKILL.md"
    ]
  }
]
```

The `skills` field contains absolute `SKILL.md` paths. An empty result is `[]`.

`list` is fail-fast. One marked distribution with unusable metadata or selected files stops the complete scan.

## Output and exit statuses

| Status | Meaning | Streams |
| ---: | --- | --- |
| `0` | Command completed | Data on stdout |
| `1` | `AgentPluginError` from configuration, packaging metadata, or filesystem state | `agent-plugins: error: ...` on stderr |
| `2` | Argument parsing failure | Usage and diagnostic on stderr |

Unexpected Python exceptions follow normal interpreter traceback behavior.
