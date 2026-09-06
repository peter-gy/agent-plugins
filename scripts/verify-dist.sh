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
import sys

import agent_plugins as ap

source_root = Path(os.environ["AGENT_PLUGINS_SOURCE_ROOT"])
expected_version = os.environ["AGENT_PLUGINS_EXPECTED_VERSION"]
dist = distribution("agent-plugins")
assert dist.version == expected_version

plugin = ap.locate("agent-plugins")
source_plugin = ap.Plugin.from_project(source_root)
assert plugin.manifest.name == "agent-plugins"
assert source_plugin.manifest.name == plugin.manifest.name

assert tuple(path.relative_to(source_plugin.path) for path in source_plugin.files) == tuple(
    path.relative_to(plugin.path) for path in plugin.files
)

skill = plugin.skills[0]
source_skill = source_plugin.skill("agent-plugins")
assert plugin.skill("agent-plugins") is skill
assert source_skill.source == skill.source

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
    [sys.executable, "-m", "agent_plugins", "locate", "agent-plugins"],
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

attachment_dir="$(mktemp -d "$root/dist/.attachment-smoke.XXXXXX")"
cleanup_attachment() {
	rm -rf "$attachment_dir"
}
trap cleanup_attachment EXIT
attached_dir="$attachment_dir/attached"
plain_wheel="$attachment_dir/attachment_smoke-1.0.0-py3-none-any.whl"
attached_wheel="$attached_dir/attachment_smoke-1.0.0-py3-none-any.whl"
mkdir -p "$attached_dir"

uv run --no-project --isolated --no-cache --with "${wheels[0]}" python - \
	"$plain_wheel" "$attached_dir" "$attachment_dir" <<'PY'
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import agent_plugins as ap

wheel = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
workspace = Path(sys.argv[3])
project = workspace / "project"
dist_info = "attachment_smoke-1.0.0.dist-info"
plugin_schema = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
mcp_schema = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

core = project / "skills" / "core"
critique = project / "skills" / "critique"
(core / "references").mkdir(parents=True)
critique.mkdir(parents=True)
(project / "bin").mkdir()
(project / "pyproject.toml").write_text(
    '[tool.agent-plugins]\nroot = "."\ninclude = ["bin/**"]\n',
    encoding="utf-8",
)
(project / "plugin.json").write_text(
    json.dumps({"$schema": plugin_schema, "name": "fixture-plugin"}),
    encoding="utf-8",
)
(project / "mcp.json").write_text(
    json.dumps(
        {
            "$schema": mcp_schema,
            "mcpServers": {
                "fixture": {
                    "type": "stdio",
                    "command": "./bin/server",
                    "args": ["mcp", "--data", "${PLUGIN_DATA}"],
                }
            },
        }
    ),
    encoding="utf-8",
)
(project / "bin" / "server").write_text("server\n", encoding="utf-8")
(core / "SKILL.md").write_text(
    "---\nname: core\ndescription: Core workflow\n---\n# Core\n",
    encoding="utf-8",
)
(core / "references" / "querying.md").write_text(
    "# Querying\n", encoding="utf-8"
)
(critique / "SKILL.md").write_text(
    "---\nname: critique\ndescription: Critique workflow\n---\n# Critique\n",
    encoding="utf-8",
)

source_plugin = ap.Plugin.from_project(project)
assert source_plugin.skill("core").source.startswith("---\n")
assert source_plugin.skill("core").file(
    "references/querying.md"
).read_text(encoding="utf-8") == "# Querying\n"
source_data = workspace / "source-data"
source_data.mkdir()
source_mcp = source_plugin.mcp
assert source_mcp is not None
source_launch = source_mcp.resolve_stdio("fixture", data_dir=source_data)
assert source_launch.args == ("mcp", "--data", str(source_data.resolve()))

with zipfile.ZipFile(wheel, "w") as archive:
    archive.writestr("attachment_smoke.py", "VALUE = 1\n")
    archive.writestr(f"{dist_info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
    archive.writestr(f"{dist_info}/METADATA", "Metadata-Version: 2.4\nName: attachment-smoke\nVersion: 1.0.0\n")
    archive.writestr(f"{dist_info}/RECORD", "")

source_bytes = wheel.read_bytes()
attachment = ap.attach_wheel(wheel, project=project, output_dir=output_dir)
assert isinstance(attachment, ap.WheelAttachment)
assert attachment.source == wheel.resolve()
assert attachment.output == (output_dir / wheel.name).resolve()
assert wheel.read_bytes() == source_bytes
attached_bytes = attachment.output.read_bytes()

completed = subprocess.run(
    [
        "agent-plugins",
        "attach-wheel",
        str(attachment.output),
        "--project",
        str(project),
        "--json",
    ],
    check=True,
    capture_output=True,
    text=True,
)
result = json.loads(completed.stdout)
assert Path(result["source"]) == attachment.output
assert Path(result["output"]) == (output_dir / wheel.name).resolve()
assert result["files"] == [
    "bin/server",
    "mcp.json",
    "plugin.json",
    "skills/core/SKILL.md",
    "skills/core/references/querying.md",
    "skills/critique/SKILL.md",
]
assert result["replaced_existing_plugin"] is True
assert attachment.output.read_bytes() == attached_bytes
assert completed.stderr == ""
PY

uv run --no-project --isolated --no-cache \
	--with "${wheels[0]}" \
	--with "$attached_wheel" \
	python - "$attachment_dir" <<'PY'
from pathlib import Path
import sys

import agent_plugins as ap

plugin = ap.locate("attachment-smoke")
assert plugin.manifest.name == "fixture-plugin"
assert {
    path.relative_to(plugin.path).as_posix() for path in plugin.files
} == {
    "bin/server",
    "mcp.json",
    "plugin.json",
    "skills/core/SKILL.md",
    "skills/core/references/querying.md",
    "skills/critique/SKILL.md",
}
core = plugin.skill("core")
assert core.source.startswith("---\n")
assert core.file("references/querying.md").read_text(
    encoding="utf-8"
) == "# Querying\n"
data_dir = Path(sys.argv[1]) / "installed-data"
data_dir.mkdir()
mcp = plugin.mcp
assert mcp is not None
launch = mcp.resolve_stdio("fixture", data_dir=data_dir)
assert launch.command == str((plugin.path / "bin" / "server").resolve())
assert launch.args == ("mcp", "--data", str(data_dir.resolve()))
assert launch.env["PLUGIN_ROOT"] == str(plugin.path)
assert launch.env["PLUGIN_DATA"] == str(data_dir.resolve())
PY

verify_install --with-editable "$root"
