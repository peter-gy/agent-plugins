#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

shopt -s nullglob
wheels=(
	"$root"/dist/agent_plugins-*.whl
	"$root"/dist/from-sdist/agent_plugins-*.whl
)

if [[ "${#wheels[@]}" -ne 2 ]]; then
	printf 'ERROR: Expected the release wheel and one wheel rebuilt from the source distribution\n' >&2
	exit 1
fi

export AGENT_PLUGINS_SOURCE_ROOT="$root"
expected_version="$(uv version --short)"
export AGENT_PLUGINS_EXPECTED_VERSION="$expected_version"
export UV_NO_CONFIG=1

verify_install() {
	uv run --no-project --isolated --no-cache "$@" python - <<'PY'
import json
import os
from importlib.metadata import distribution
from pathlib import Path
import subprocess

import agent_plugins as ap

source_root = Path(os.environ["AGENT_PLUGINS_SOURCE_ROOT"])
expected_version = os.environ["AGENT_PLUGINS_EXPECTED_VERSION"]
dist = distribution("agent-plugins")
assert dist.version == expected_version

plugin = ap.locate("agent-plugins")
assert plugin.manifest.name == "agent-plugins"
assert plugin.manifest.issues == ()
assert len(plugin.skills) == 1

skill = plugin.skills[0]
assert skill.path.name == "agent-plugins"
assert skill.frontmatter.startswith("name: agent-plugins\n")
assert skill.body.lstrip().startswith("# Agent Plugins\n")

expected_files = {
    "plugin.json",
    "skills/agent-plugins/SKILL.md",
    "skills/agent-plugins/agents/openai.yaml",
}
installed_files = {
    path.relative_to(plugin.path).as_posix() for path in plugin.files
}
assert installed_files == expected_files

for relative in expected_files:
    assert (plugin.path / relative).read_bytes() == (source_root / relative).read_bytes()

located = subprocess.run(
    ["agent-plugins", "locate", "agent-plugins"],
    check=True,
    capture_output=True,
    text=True,
)
assert Path(located.stdout.strip()).resolve() == plugin.path

listed = subprocess.run(
    ["agent-plugins", "list", "--json"],
    check=True,
    capture_output=True,
    text=True,
)
records = json.loads(listed.stdout)
record = next(item for item in records if item["distribution"] == "agent-plugins")
assert Path(record["root"]).resolve() == plugin.path
assert record["skills"] == [str(skill / "SKILL.md")]
PY
}

for wheel in "${wheels[@]}"; do
	verify_install --with "$wheel"
done

verify_install --with-editable "$root"
