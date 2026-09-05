from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
RELEASE_SPECIFIC_PIN = re.compile(
    r"\b(?:agent-plugins|uv[-_]build|hatchling)==\d+(?:\.\d+){2}\b"
)


def test_documented_dependency_examples_are_release_independent() -> None:
    documents = [
        ROOT / "README.md",
        ROOT / "skills" / "agent-plugins" / "SKILL.md",
        *(ROOT / "docs").rglob("*.md"),
        *(ROOT / "development_docs").rglob("*.md"),
    ]

    pinned: dict[str, list[str]] = {}
    for document in documents:
        matches = sorted(
            set(RELEASE_SPECIFIC_PIN.findall(document.read_text(encoding="utf-8")))
        )
        if matches:
            pinned[document.relative_to(ROOT).as_posix()] = matches

    assert pinned == {}
