# Design package briefings

An independently loaded skill must give a fresh agent enough information to
choose a workflow, execute its first action, verify the result, and find the
next relevant resource. CLI and Python help should present the same authored
core, with environment context supplied by `agent-plugins`.

## Assign each surface an owner

| Surface | Content |
| --- | --- |
| Package README | Bootstrap command and the already-installed Python route |
| Generated briefing | Distribution version, interpreter, resource location, documentation links, and selected skill source |
| Core skill | Applicability, package concepts, prerequisites, workflow, and verification |
| Skill references | Conditional setup, specialized workflows, and detailed recovery |
| API docstrings | Signatures, inputs, returns, side effects, and operation semantics |
| Project instructions | Repository or authored-project conventions |
| Published docs | Broader guides, examples, and reference pages |

Package-specific host requirements and optional extras belong with the
workflow that needs them. The execution host or project manager owns dependency
installation and version policy. An importable agent module already has its
base package installed, so its help should route to additional setup only when
the selected operation requires it.

Distinguish instructions being available, a package being installed in the
execution environment, and the required runtime being connected and ready.
Describe the check that establishes each relevant transition.

## Shape the core skill

Use this outline when the package has several workflows. Collapse sections
when a smaller skill can convey the same contract:

```text
Frontmatter: name and concrete activation conditions
Purpose: outcome, essential objects, and their ownership
Choose: task-to-workflow routes and their prerequisites
Start: smallest complete example, including imports and bindings
Verify: observable success and the main misleading success signal
Continue: conditional references, recovery, and published documentation
```

Prefer a compact core, often around 100–200 lines. Length follows the complete
workflow rather than a quota. Move substantial conditional material into
focused `references/` files and link it at the decision point where it is
needed. Keep essential correctness constraints beside the example they govern.

Write the core for direct loading as well as generated briefings. A first
example must not depend on a variable created by module help, a prior task, or
another execution call. Repeat short imports where they make an example
independent. For hosts that discard scratch bindings, explain how to reacquire
handles and which identities or results must survive between calls.

Do not require the agent to read the skill it is already following. Reuse
loaded instructions for the same environment and installation. Route back to
discovery when the environment or installation changes or an API mismatch
requires checking the source of the instructions.

Use relative links beneath the skill root and resolve packaged resources with
`Skill.file()`. Absolute paths in a briefing describe its owning installation.
They can be inaccessible from another host or disappear with a disposable
environment. Provide a Python resource-access route for remote execution.

Keep additional task skills independently selectable when their activation
conditions differ. A general package capability should route to a specialized
workflow only when the user's request calls for it.

## Python module help

The packaging skill's minimal `agent.py` example sets `__doc__` from
`ap.read("my-package")`. It reads the installed core when that module is
imported. Keep it out of the package's ordinary import path. Restart the host
after replacing an already imported installation.

`ap.read()` returns one Markdown string. Omitted `skill` uses the distribution
argument exactly. An explicit `skill` selects a structural directory name.
The CLI uses the same renderer but includes all skills unless `--skill` is
provided. Both entrypoints preserve the selected instruction source.

If callers need resource handles, expose small accessors over the public API:

```python
import agent_plugins as _ap


def agent_plugin() -> _ap.Plugin:
    return _ap.locate("my-package")


def agent_skill() -> _ap.Skill:
    return agent_plugin().skill("my-package")
```

Callers can then read a linked file inside the execution host with
`agent_skill().file("references/setup.md").read_text(encoding="utf-8")`, when
that resource is packaged. Add accessors when consumers need them, and retain
host adapters that implement package-specific operations.

Inspect actual `help(module)` output. Python can append documentation for
exported functions and classes, even when the module docstring is short.
Keep initial help focused and route detailed introspection to the relevant
objects or submodules. Check that help reads instructions without connecting
services, mounting components, or performing the example's operations.

## Publish documentation links

Declare documentation URLs in Python package metadata:

```toml
[project.urls]
Documentation = "https://example.org/my-package/"
"Documentation Index" = "https://example.org/my-package/llms.txt"
```

`agent-plugins` includes these two labels in generated briefings. The
`Documentation Index` label is a package-authoring convention. Use the actual
index URL when one is published, and verify its linked destinations as part of
the documentation build. A new manifest property is unnecessary.

Keep a short documentation link in the core skill too, so it works when loaded
independently of Python metadata. Load specific linked pages as needed. Check
online APIs against the installed version. A development checkout describes
that checkout and may differ from a released installation.

## Verify the handoff

Exercise the entrypoints an agent will actually use:

1. From a README, run the isolated CLI bootstrap and follow one linked resource.
   Confirm the output distinguishes that installation from the execution host.
2. In a project with an existing installation, read through its interpreter and
   verify the reported version and resource origin.
3. Through the intended Python host, read module help and retrieve a reference
   using Python when direct filesystem access is unavailable.
4. Load `SKILL.md` directly and follow its first example using fresh bindings.
5. Continue a related task in the same environment and verify that the routing
   advances to relevant work instead of requiring repeated discovery.

Test required runtime readiness and the example's expected result separately
from successful imports and resource reads. Keep failures actionable: an absent
package requires installation, an unknown skill requires selecting an available
name, and an unavailable runtime requires its host's connection workflow.
