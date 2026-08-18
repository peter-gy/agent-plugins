"""Command-line interface for installed and authored Agent Plugins."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ._build.plan import BuildPlan, build_plan
from ._discovery import installed, locate
from ._errors import AgentPluginError


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Agent Plugins command-line interface."""
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "list":
            _list_plugins(as_json=arguments.json)
        elif arguments.command == "locate":
            print(locate(arguments.distribution).path)
        else:
            _print_plan(build_plan(arguments.project), as_json=arguments.json)
    except AgentPluginError as error:
        print(f"agent-plugins: error: {error}", file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-plugins",
        description="Locate installed Agent Plugins and inspect package build plans.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser(
        "list", help="List installed plugins and their skill instruction files."
    )
    list_parser.add_argument(
        "--json", action="store_true", help="Write a JSON array to stdout."
    )

    locate_parser = commands.add_parser(
        "locate", help="Print one installed plugin root."
    )
    locate_parser.add_argument(
        "distribution", help="Installed Python distribution name."
    )

    plan_parser = commands.add_parser(
        "plan", help="List files selected by [tool.agent-plugins]."
    )
    plan_parser.add_argument(
        "project",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help=(
            "Project directory containing pyproject.toml. "
            "Defaults to the current directory."
        ),
    )
    plan_parser.add_argument(
        "--json", action="store_true", help="Write a JSON object to stdout."
    )
    return parser


def _list_plugins(*, as_json: bool) -> None:
    plugins = installed()
    if as_json:
        value = [
            {
                "distribution": name,
                "root": str(plugin.path),
                "skills": [str(skill / "SKILL.md") for skill in plugin.skills],
            }
            for name, plugin in plugins.items()
        ]
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return

    for name, plugin in plugins.items():
        print(f"{name}\t{plugin.path}")
        for skill in plugin.skills:
            print(f"\tskill\t{skill / 'SKILL.md'}")


def _print_plan(plan: BuildPlan, *, as_json: bool) -> None:
    if as_json:
        value = {
            "project": str(plan.project),
            "root": str(plan.root),
            "files": [
                {"source": str(mapping.source), "target": mapping.target.as_posix()}
                for mapping in plan.files
            ],
        }
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return

    print(f"root\t{plan.root}")
    for mapping in plan.files:
        print(f"{mapping.target.as_posix()}\t{mapping.source}")
