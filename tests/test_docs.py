from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def test_quickstart_installs_library_and_skill_from_documented_files(
    tmp_path: Path,
) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required for wheel installation")
    guide = (ROOT / "docs/guide/getting-started.md").read_text(encoding="utf-8")
    for name, content in re.findall(
        r"^```\w+ \[([^\]]+)\]\n(.*?)^```$", guide, re.MULTILINE | re.DOTALL
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    project = tmp_path / "packages/python"
    dist = tmp_path / "dist"
    environment = {**os.environ, "UV_CACHE_DIR": str(tmp_path / "uv-cache")}
    subprocess.run(
        [
            uv,
            "build",
            "--wheel",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--out-dir",
            str(dist),
            str(project),
        ],
        env=environment,
        check=True,
        timeout=60,
        capture_output=True,
        text=True,
    )
    wheel = dist / "my_project-0.1.0-py3-none-any.whl"
    installed = tmp_path / "installed"
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--python",
            sys.executable,
            "--target",
            str(installed),
            "--no-deps",
            str(wheel),
        ],
        env=environment,
        check=True,
        timeout=60,
        capture_output=True,
        text=True,
    )
    example = re.findall(r"^```python\n(.*?)^```$", guide, re.MULTILINE | re.DOTALL)[0]
    completed = subprocess.run(
        [sys.executable, "-c", example],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(installed)},
        check=True,
        timeout=60,
        capture_output=True,
        text=True,
    )

    instructions = (tmp_path / "skills/use-my-project/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert completed.stdout == f"{instructions}\nHello, Ada!\n"
