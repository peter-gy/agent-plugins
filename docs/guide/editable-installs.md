---
title: Editable installs
description: Understand how an editable agent_plugins.json marker tracks an authored plugin directory.
---

# Develop through an editable install

An editable wheel points discovery at the authored plugin root. This keeps selected source files available while you work on them.

Install the Python project in editable mode through a frontend that supports [PEP 660](https://peps.python.org/pep-0660/):

```console
python -m pip install -e packages/python
```

Then locate it by Python distribution name:

```console
agent-plugins locate my-project
```

The printed path is the resolved authored plugin root.

## What updates immediately

The editable form of the `agent_plugins.json` marker stores the authored root and the file paths selected at install time.

- Editing a selected `plugin.json`, `mcp.json`, or `SKILL.md` updates the source file.
- A new `Plugin` handle reads the current file contents when a document property is first accessed.
- `plugin.files` and `plugin.skills` remain limited to names recorded by the `agent_plugins.json` marker.

## When to reinstall

Reinstall the editable distribution after adding, deleting, or moving plugin files:

```console
python -m pip install -e packages/python
```

This regenerates the `agent_plugins.json` marker with a fresh build plan. Reinstall after moving the checkout too, because its `root` contains an absolute authored path.

## Refresh a document handle

Manifest, MCP, and skill documents cache their first loaded value or error. Create a fresh handle after editing document contents:

```python
import agent_plugins as ap

plugin = ap.locate("my-project")
print(plugin.manifest.name)
```

Calling `ap.locate()` again creates a new `Plugin` handle, then the next parsed-field access reads the document again.
