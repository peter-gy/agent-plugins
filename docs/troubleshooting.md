---
title: Troubleshooting
description: Recover from build-plan, wheel-attachment, installed discovery, document, and editable-install failures.
---

# Troubleshooting

Start from the first error line. The CLI writes handled failures as `agent-plugins: error: ...` on stderr and exits with status 1.

## Build-plan failures

| Message contains | Cause | Recovery |
| --- | --- | --- |
| `Project has no pyproject.toml` | The `plan` argument is not a Python project directory | Pass the directory that contains `pyproject.toml` |
| `Missing [tool.agent-plugins]` | The configuration table is absent or has the wrong shape | Add `[tool.agent-plugins]` |
| `root must be a non-empty path` | `root` is absent, empty, or not a string | Set `root` to the authored plugin directory |
| `Agent Plugin root cannot be resolved` | The configured path does not exist | Resolve `root` from the Python project directory |
| `Expected a file: .../plugin.json` | The required manifest is absent or not a regular file | Create root-level `plugin.json` |
| `Include pattern matched no files` | An `include` glob found no filesystem entry | Correct the pattern or create the intended files |
| `Include pattern must stay within the plugin root` | The pattern is absolute, contains `..`, or uses backslashes | Use a forward-slash, root-relative pattern |
| `Directory symlinks cannot be packaged` | A recursively selected directory is a symlink | Select a real directory inside the plugin root |
| `Plugin file escapes its root` | A selected file or symlink resolves outside the plugin root | Move the file into the root or remove it from selection |

Run `agent-plugins plan PROJECT --json` after each correction.

## Wheel attachment failures

`attach-wheel` names the incompatible file, archive member, or destination and the recovery action. Rebuild a corrupt wheel. Correct duplicate, absolute, parent-traversing, or backslash-containing archive members at their source build step.

When `--output-dir` reports an existing destination, remove that artifact or select another existing directory. Attachment publishes the destination after the complete rewrite succeeds, so retrying the command is safe.

## Installed discovery failures

Installed discovery reads the `agent_plugins.json` marker from Python distribution metadata. The marker records the plugin root and selected filenames.

### Distribution is not installed

`locate()` accepts a Python distribution name. Check the installed metadata name:

```console
python -m pip show my-project
```

Install the distribution in the same environment that runs `agent-plugins`.

### Distribution has no Agent Plugin

The installed distribution lacks `agent_plugins.json`. Rebuild it with an `agent_plugins.build` backend adapter or run `attach-wheel` on the trusted wheel. Reinstall the attached artifact, then run `locate` again.

### Outdated Agent Plugin metadata

The marker predates the exact file inventory. Reinstall a wheel created by the current adapter or `attach-wheel` command.

### Invalid marker or selected files

Reinstall from a trusted wheel. If the problem remains, inspect the built wheel for `agent_plugins.json`, the sibling `.agent-plugin` directory, and every marker-listed path.

`agent-plugins list` is fail-fast. A broken marked distribution can stop the complete scan. Locate known distributions individually while diagnosing the environment.

## Document validation failures

`ValidationError` names the file, location, and first fatal issue.

```text
/path/plugin.json: $.name: Invalid plugin name
```

Use the exact supported `$schema` identifier and check the affected field in [`plugin.json`](/reference/plugin-json) or [`mcp.json`](/reference/mcp-json).

Manifest and MCP objects cache their first error. Create a new `Plugin`, `Manifest`, or `MCPConfig` handle after editing the file.

## Skill lookup and resource failures

`plugin.skill(name)` accepts one immediate skill directory name. Use a name listed in the error's sorted available skills.

`skill.file(path)` accepts a portable path from the selected skill inventory. Use forward slashes and a path shown by `skill.files` or `skill.tree()`. Recreate the `Plugin` or `Skill` handle after changing selected filenames.

## Missing MCP server entries

An invalid individual entry is skipped and recorded in `mcp.issues`:

```python
for issue in plugin.mcp.issues:
    print(issue.location, issue.message)
```

Check the server type, closed field set, stdio command and working-directory rules, URL security rules, and headers.

`resolve_stdio()` requires an existing plugin data directory, regular plugin-relative command, and existing contained working directory. When the configuration came from a `Plugin`, the command and plugin-root working directory must also belong to its selected inventory. Create the data directory through the client application's storage policy. Package a `./` command through the build plan and create any configured working directory in the applicable plugin or data root.

After resolution, process creation can still fail because of permissions, executable format, platform search, or process policy. HTTP endpoints can fail to connect or complete the MCP handshake. Those checks belong to the consuming agent client.

## Invalid `SKILL.md`

`skill.source`, `skill.frontmatter`, and `skill.body` require UTF-8 text, an opening `---` on the first line, and a later closing `---` line.

Create a new `Skill` handle after fixing the file because the first error is cached.

Use an Agent Skills validator for YAML fields and specification rules beyond the delimiter structure.

## Editable install misses a new file

The editable form of the `agent_plugins.json` marker records filenames at install time. Reinstall after adding, deleting, or moving plugin files:

```console
python -m pip install -e packages/python
```

Create a fresh `Plugin` handle after reinstalling.

## Tree rendering rejects a limit

`Plugin.tree()` and `Skill.tree()` accept non-negative integers or `None`. Pass `None` to remove a bound:

```python
plugin.tree(max_depth=None, max_files=None)
```
