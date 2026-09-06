---
title: Agent Skills
description: Package Agent Skill directories and inspect their files and source text.
---

# Package Agent Skills

An [Agent Skill](https://agentskills.io/specification) is a directory of instructions and related resources rooted at `SKILL.md`. Place each skill directly under `skills/` in the plugin directory.

```text
skills/
└── review-records/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── references/
    │   └── fields.md
    └── scripts/
        └── validate.py
```

The build plan selects the complete `skills/` tree. The runtime creates a `Skill` handle for each exact `skills/<name>/SKILL.md` path in the selected file inventory.

## Write the instructions document

`SKILL.md` begins with frontmatter delimited by exact `---` lines:

```md
---
name: review-records
description: Review project records against the published field contract.
---

# Review records

Read `references/fields.md`, then run `scripts/validate.py`.
```

The Python API checks UTF-8 text and the two delimiters. It returns the frontmatter and Markdown body as raw source text. It does not parse the frontmatter as YAML or check the Agent Skills field rules.

## Inspect packaged skills

```python
import agent_plugins as ap

plugin = ap.locate("my-project")
skill = plugin.skill("review-records")

print(skill.path)
print(skill.source)
print(skill.file("references/fields.md"))
```

`skill.files` contains absolute paths from the selected inventory below that skill root. `skill.tree()` renders the same selection as a bounded ASCII tree.

`plugin.skill(name)` selects an immediate skill by its structural directory name and reports sorted available names when the requested skill is absent.

`skill.file(relative_path)` requires an exact selected file and rechecks containment. Use it for instructions, references, scripts, agents, and assets that came from an Agent Plugin inventory.

The `/` operator remains an ordinary unchecked `pathlib.Path` join for compatibility.

## Content cache

The first access to `skill.source`, `skill.frontmatter`, or `skill.body` reads and splits `SKILL.md`. All three strings, or the first `ValidationError`, remain cached on that `Skill` handle. Create a new handle to reread the file.

`skill.source` preserves the complete document, including delimiters, original line endings, and final newline state. Delimiter lines are excluded from `frontmatter` and `body`. An empty body is accepted.
