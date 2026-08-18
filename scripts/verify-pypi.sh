#!/usr/bin/env bash
set -euo pipefail

version="${RELEASE_VERSION:-}"
if [[ -z "$version" ]]; then
	ref_name="${GITHUB_REF_NAME:-}"
	version="${ref_name#v}"
fi

if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	printf 'ERROR: Release version must use final-version form X.Y.Z: %s\n' "$version" >&2
	exit 1
fi

export UV_NO_CONFIG=1

verify_release() {
	RELEASE_VERSION="$version" uv run \
		--no-cache \
		--no-project \
		--isolated \
		--default-index https://pypi.org/simple \
		--with "agent-plugins==$version" \
		python - <<'PY'
import os
from importlib.metadata import distribution
from pathlib import Path
import subprocess

import agent_plugins as ap

dist = distribution("agent-plugins")
assert dist.version == os.environ["RELEASE_VERSION"]

plugin = ap.locate("agent-plugins")
assert plugin.manifest.name == "agent-plugins"
assert plugin.manifest.issues == ()
assert len(plugin.skills) == 1

skill = plugin.skills[0]
assert skill.path.name == "agent-plugins"
assert (skill / "SKILL.md").is_file()
assert (skill / "agents/openai.yaml").is_file()
assert skill.frontmatter.startswith("name: agent-plugins\n")

located = subprocess.run(
    ["agent-plugins", "locate", "agent-plugins"],
    check=True,
    capture_output=True,
    text=True,
)
assert Path(located.stdout.strip()).resolve() == plugin.path
PY
}

for ((attempt = 1; attempt <= 18; attempt++)); do
	if verify_release; then
		exit 0
	fi

	printf 'PyPI verification attempt %s of 18 did not verify %s\n' "$attempt" "$version"
	if [[ "$attempt" -lt 18 ]]; then
		sleep 10
	fi
done

printf 'ERROR: PyPI did not verify agent-plugins %s within three minutes\n' "$version" >&2
exit 1
