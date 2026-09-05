from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).parent.parent
PIN = re.compile(r"agent-plugins==([0-9]+\.[0-9]+\.[0-9]+)")


def test_documented_package_pins_match_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    documents = [
        ROOT / "README.md",
        ROOT / "skills" / "agent-plugins" / "SKILL.md",
        *(ROOT / "docs").rglob("*.md"),
    ]

    documented = {
        match.group(1)
        for document in documents
        for match in PIN.finditer(document.read_text(encoding="utf-8"))
    }

    assert documented == {version}
