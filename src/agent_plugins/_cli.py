"""Command-line interface for installed and authored Agent Plugins."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ._build.plan import BuildPlan, build_plan
from ._build.wheel import WheelAttachment, attach_wheel
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
        elif arguments.command == "plan":
            _print_plan(build_plan(arguments.project), as_json=arguments.json)
        else:
            result = attach_wheel(
                arguments.wheel,
                project=arguments.project,
                output_dir=arguments.output_dir,
            )
            _print_attachment(result, as_json=arguments.json)
            for signature in result.removed_signatures:
                print(
                    "agent-plugins: warning: removed invalidated wheel signature: "
                    f"{signature.as_posix()}",
                    file=sys.stderr,
                )
    except AgentPluginError as error:
        print(f"agent-plugins: error: {error}", file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-plugins",
        description="Package and inspect Agent Plugins in Python distributions.",
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

    attach_parser = commands.add_parser(
        "attach-wheel",
        help="Attach the configured Agent Plugin to one wheel.",
        description=(
            "Attach the configured Agent Plugin to one wheel. "
            "By default, atomically rewrite WHEEL in place."
        ),
    )
    attach_parser.add_argument("wheel", type=Path, help="Existing .whl file.")
    attach_parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help=(
            "Project directory containing pyproject.toml. "
            "Defaults to the current directory."
        ),
    )
    attach_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Preserve the input and write the same wheel filename in this directory.",
    )
    attach_parser.add_argument(
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


def _print_attachment(result: WheelAttachment, *, as_json: bool) -> None:
    if as_json:
        value = {
            "source": str(result.source),
            "output": str(result.output),
            "dist_info": result.dist_info.as_posix(),
            "plugin_root": result.plugin_root.as_posix(),
            "files": [path.as_posix() for path in result.files],
            "replaced_existing_plugin": result.replaced_existing_plugin,
            "removed_signatures": [
                path.as_posix() for path in result.removed_signatures
            ],
        }
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    print(result.output)
