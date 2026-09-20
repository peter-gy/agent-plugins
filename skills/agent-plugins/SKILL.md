---
name: agent-plugins
description: Read version-matched agent briefings and resources from installed Python distributions. Use when a package README points to agent-plugins, a Python host exposes packaged guidance, or a task needs plugin discovery, linked resources, or installation diagnostics. For adding Agent Plugin packaging to a project, use package-agent-plugin.
---

# Read installed Agent Plugins

Read the instructions shipped with the Python installation that will execute
the task. A briefing combines distribution identity, environment guidance,
plugin inventory, and complete skill instructions. The host supplies execution
tools, dependency management, and runtime connections.

## Choose the entrypoint

If the package is already installed, read its briefing in that Python
environment:

```python
import agent_plugins as ap

print(ap.read("my-package"))
```

`ap.read()` returns a string and selects the skill whose directory name matches
the distribution argument exactly. Pass `skill="use-my-package"` when the
workflow has another name. An unavailable skill raises `AgentPluginError` and
lists the available names. Use the host's captured `help(module)` output when
a package exposes the same briefing through an agent module.

When starting from a README before setting up an execution environment, run:

```console
uvx --with my-package agent-plugins read my-package
```

The requirement after `--with` selects what uv installs. The final argument
identifies the installed distribution to inspect. Pin the requirement, such as
`'my-package==1.2.3'`, when the task requires a particular release.

The CLI includes every packaged skill by default. Select one with
`--skill NAME`. Follow the workflows applicable to the request. Running
`uvx agent-plugins` with no arguments reads this package's consumer and
packaging skills.

## Use the execution environment

Check the briefing's distribution version and interpreter before using its
examples. `uvx` uses an isolated, disposable tool environment. Its resource
paths can remain readable while cached, but the project or notebook may have
a different installation or filesystem.

Install dependencies through the target project's or host's package manager,
preserving its version policy. Then read that installation's briefing. From a
terminal, bind the CLI to the intended interpreter:

```console
/path/to/environment/bin/python -m agent_plugins read my-package
```

In a remote kernel or service, execute `ap.read()` there. Reuse the briefing
while that environment and installation remain unchanged. If a package's
module help already supplied the applicable skill, continue with its workflow.
Rediscover after switching environments or installations. Restart a process
that still holds imports from a replaced package.

Package availability and runtime readiness are separate. Follow the selected
workflow's connection, activation, and verification steps before treating a
browser, service, device, or other host as ready.

## Read linked resources

Relative links are resolved from the skill directory. When the agent cannot
read that filesystem directly, retrieve the text through Python in its owning
environment:

```python
import agent_plugins as ap

plugin = ap.locate("my-package")
skill = plugin.skill("my-package")
print(skill.tree())
```

Choose a resource named by the skill. For a packaged `references/api.md`:

```python
print(skill.file("references/api.md").read_text(encoding="utf-8"))
```

`skill.file()` checks selected-file membership and containment. Reacquire the
handle in each execution if the host discards local bindings between calls.
Read additional resources at the decision points specified by the workflow.
`skill.source` returns the full instruction file, and `skill.body` omits its
frontmatter when raw text is needed instead of a briefing.

Use published documentation and its `llms.txt` index for broader examples and
reference. Check that an online API matches the active installation. A source
checkout describes that checkout and may differ from an installed release.

## Inspect or recover

| Task | Operation |
| --- | --- |
| Find plugins in this interpreter | `ap.installed()` |
| Inspect one plugin's selected files | `ap.locate("my-package").tree()` |
| Discover its skill names | `[skill.name for skill in plugin.skills]` |
| Inspect plugin metadata | `plugin.manifest` |
| Inspect MCP configuration | `plugin.mcp` |
| List installed plugins from a terminal | `agent-plugins list --json` |
| Print one installed plugin root | `agent-plugins locate my-package` |

Pass the Python distribution name to `read()` and `locate()`. The manifest
plugin name and Python import name can differ from it.

For an absent distribution or unusable plugin, correct the target installation
before retrying. For an unavailable skill, select a listed structural name.
`ValidationError` identifies an invalid plugin document. Preserve that
diagnostic when the packaged files need repair.

Briefings summarize MCP names and transports while leaving configured commands,
arguments, environment values, URLs, and headers out of the output. The host
owns component activation and execution permissions.

Use `agent-plugins --help` or `agent-plugins COMMAND --help` for CLI syntax.
Success writes to stdout. Expected operational failures return status `1`
with a diagnostic on stderr. Argument errors return status `2`.

For project packaging, build planning, or wheel attachment, read the
`package-agent-plugin` skill.

Use the [documentation index](https://peter-gy.github.io/agent-plugins/llms.txt)
for additional API and integration guidance.
