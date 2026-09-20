"""Render an installed Agent Plugin as a Markdown briefing."""

from __future__ import annotations

import re
from importlib.metadata import Distribution

from ._discovery import _locate
from ._plugin import Plugin
from ._schema.errors import ValidationIssue, format_location
from ._schema.models import Author
from ._skill import Skill


def render_read(distribution_name: str, *, skill_name: str | None = None) -> str:
    """Return a getting-started briefing for one installed Agent Plugin."""
    distribution, plugin = _locate(distribution_name)
    skills = plugin.skills if skill_name is None else (plugin.skill(skill_name),)
    return _markdown(distribution, plugin, skills)


def _markdown(
    distribution: Distribution,
    plugin: Plugin,
    skills: tuple[Skill, ...],
) -> str:
    manifest = plugin.manifest
    distribution_name = distribution.metadata["Name"] or manifest.name
    lines = [
        f"# Agent Plugin: {_code(manifest.name)}",
        "",
        f"Python distribution: {_code(f'{distribution_name}=={distribution.version}')}",
        f"Installed root: {_code(str(plugin.path))}",
    ]
    summary = distribution.metadata["Summary"]
    if summary:
        lines.append(f"Distribution summary: {_one_line(summary)}")
    if manifest.version:
        lines.append(f"Plugin version: {_code(manifest.version)}")
    if manifest.description:
        lines.append(f"Plugin description: {_one_line(manifest.description)}")
    if manifest.author:
        author = _author(manifest.author)
        if author:
            lines.append(f"Author: {_one_line(author)}")
    if manifest.homepage:
        lines.append(f"Homepage: {_one_line(manifest.homepage)}")
    if manifest.repository:
        lines.append(f"Repository: {_one_line(manifest.repository)}")
    if manifest.license:
        lines.append(f"License: {_one_line(manifest.license)}")
    if manifest.keywords:
        lines.append(
            "Keywords: " + ", ".join(_code(value) for value in manifest.keywords)
        )

    lines.extend(
        (
            "",
            (
                "Complete installed Agent Skill instructions follow. Resolve relative "
                "resource paths from each instruction file's directory."
            ),
            "",
            "## Plugin inventory",
            "",
            _fenced_block(plugin.tree(), language="text"),
            "",
            (
                "The inventory is bounded. Inspect the installed root shown above when "
                "a skill routes to a deeper resource."
            ),
        )
    )

    if manifest.extensions:
        lines.extend(("", "## Client extensions", ""))
        lines.extend(f"- {_code(name)}" for name in manifest.extensions)

    if manifest.issues:
        lines.extend(("", "## Manifest issues", ""))
        lines.extend(_issue_line(issue) for issue in manifest.issues)

    mcp = plugin.mcp
    if mcp is not None:
        lines.extend(
            (
                "",
                "## MCP servers",
                "",
                f"Configuration: {_code(str(mcp.path))}",
            )
        )
        if mcp.servers:
            lines.append("")
            lines.extend(
                f"- {_code(name)} ({_code(server.type)})"
                for name, server in mcp.servers.items()
            )
        if mcp.issues:
            lines.extend(("", "Configuration issues:", ""))
            lines.extend(_issue_line(issue) for issue in mcp.issues)

    if skills:
        for skill in skills:
            lines.extend(
                (
                    "",
                    f"## Agent Skill: {_code(skill.name)}",
                    "",
                    f"Instruction file: {_code(str(skill.file('SKILL.md')))}",
                    "",
                    skill.source,
                )
            )
    else:
        lines.extend(
            (
                "",
                "## Agent Skills",
                "",
                "This plugin packages no Agent Skills. Use its inventory and "
                "component metadata.",
            )
        )

    output = "\n".join(lines)
    return output if output.endswith("\n") else output + "\n"


def _author(author: Author) -> str:
    values = [value for value in (author.name, author.email, author.url) if value]
    return ", ".join(values)


def _issue_line(issue: ValidationIssue) -> str:
    return f"- {_code(format_location(issue.location))}: {_one_line(issue.message)}"


def _one_line(value: str) -> str:
    return " ".join(value.split())


def _code(value: str) -> str:
    delimiter = "`" * (_longest_backtick_run(value) + 1)
    padding = " " if value.startswith(("`", " ")) or value.endswith(("`", " ")) else ""
    return f"{delimiter}{padding}{value}{padding}{delimiter}"


def _fenced_block(value: str, *, language: str) -> str:
    delimiter = "`" * max(3, _longest_backtick_run(value) + 1)
    return f"{delimiter}{language}\n{value}\n{delimiter}"


def _longest_backtick_run(value: str) -> int:
    return max((len(match.group()) for match in re.finditer(r"`+", value)), default=0)
