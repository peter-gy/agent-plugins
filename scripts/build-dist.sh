#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dist_dir="$root/dist"
cd "$root"

rm -rf "$dist_dir"
uv build --out-dir "$dist_dir"

shopt -s nullglob
artifacts=("$dist_dir"/agent_plugins-*.whl "$dist_dir"/agent_plugins-*.tar.gz)
sdists=("$dist_dir"/agent_plugins-*.tar.gz)

if [[ "${#artifacts[@]}" -ne 2 || "${#sdists[@]}" -ne 1 ]]; then
	printf 'ERROR: Expected one wheel and one source distribution in %s\n' "$dist_dir" >&2
	exit 1
fi

uvx --from twine==7.0.0 twine check "${artifacts[@]}"

mkdir -p "$dist_dir/from-sdist"
uv build --wheel "${sdists[0]}" --out-dir "$dist_dir/from-sdist"
"$root/scripts/verify-dist.sh"
