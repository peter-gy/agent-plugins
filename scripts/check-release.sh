#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

error() {
	printf 'ERROR: %s\n' "$1" >&2
}

require_env() {
	if [[ -z "${!1:-}" ]]; then
		error "Missing required environment variable: $1"
		exit 1
	fi
}

require_env GITHUB_REF_NAME
require_env GITHUB_REF
require_env GITHUB_SHA

if [[ ! "$GITHUB_REF_NAME" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	error "Release tag must use final-version form vX.Y.Z: $GITHUB_REF_NAME"
	exit 1
fi

if [[ "$GITHUB_REF" != "refs/tags/$GITHUB_REF_NAME" ]]; then
	error "Release ref must identify tag $GITHUB_REF_NAME: $GITHUB_REF"
	exit 1
fi

package_version="$(uv version --short)"
if [[ "v$package_version" != "$GITHUB_REF_NAME" ]]; then
	error "Package version $package_version does not match tag $GITHUB_REF_NAME"
	exit 1
fi

if [[ "$(git cat-file -t "$GITHUB_REF")" != tag ]]; then
	error "Release tag $GITHUB_REF_NAME must be annotated"
	exit 1
fi

if ! git merge-base --is-ancestor "$GITHUB_SHA" origin/main; then
	error "Release commit $GITHUB_SHA must be reachable from origin/main"
	exit 1
fi
