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

for skill in plugin.skills:
    print(skill.path)
    print(skill / "SKILL.md")
    print(skill.frontmatter)
    print(skill.body)
```

`skill.files` contains absolute paths from the selected inventory below that skill root. `skill.tree()` renders the same selection as a bounded ASCII tree.

The `/` operator follows ordinary `pathlib.Path` joining semantics. Pass paths you trust. It is a convenience for reaching known instructions, references, scripts, agents, or assets.

## Content cache

The first access to `skill.frontmatter` or `skill.body` reads and splits `SKILL.md`. Both strings, or the first `ValidationError`, remain cached on that `Skill` handle. Create a new handle to reread the file.

The cache preserves original line endings and source text. Delimiter lines are excluded from both returned strings. An empty body is accepted.
