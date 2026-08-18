#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

usage() {
	cat <<'EOF'
Usage: ./scripts/release.sh [--dry-run]

Releases the package version committed to main. The command requires a clean,
synchronized main branch and successful CI for its current commit. It creates
and pushes the annotated vX.Y.Z tag that starts trusted publishing.

Add the version change to the release pull request with:

  uv version --bump patch
EOF
}

error() {
	printf 'ERROR: %s\n' "$1" >&2
}

require_command() {
	if ! command -v "$1" >/dev/null 2>&1; then
		error "Missing required command: $1"
		exit 1
	fi
}

dry_run=0

case "${1:-}" in
"") ;;
--dry-run)
	dry_run=1
	;;
-h | --help)
	usage
	exit 0
	;;
*)
	error "Unknown argument: $1"
	usage >&2
	exit 1
	;;
esac

if [[ "$#" -gt 1 ]]; then
	error "Expected at most one argument"
	usage >&2
	exit 1
fi

require_command gh
require_command git
require_command uv

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
	error "Releases must run from main. Current branch: $branch"
	exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
	error "The working tree must be clean"
	git status --short >&2
	exit 1
fi

git fetch origin main --tags

commit="$(git rev-parse HEAD)"
remote_commit="$(git rev-parse origin/main)"
if [[ "$commit" != "$remote_commit" ]]; then
	error "Local main must match origin/main"
	printf 'Run git pull --ff-only origin main, then retry.\n' >&2
	exit 1
fi

version="$(uv version --short)"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	error "Package version must be a final X.Y.Z version. Current version: $version"
	exit 1
fi

tag="v$version"
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
	error "Release tag already exists: $tag"
	exit 1
fi

ci_run="$(gh run list \
	--workflow ci.yml \
	--branch main \
	--commit "$commit" \
	--event push \
	--limit 1 \
	--json databaseId,status,conclusion,url \
	--jq 'if length == 0 then "" else (.[0] | [.databaseId, .status, .conclusion, .url] | .[]) end')"

if [[ -z "$ci_run" ]]; then
	error "No main CI run found for $commit"
	printf 'Wait for the main CI workflow to start, then retry.\n' >&2
	exit 1
fi

{
	IFS= read -r ci_run_id
	IFS= read -r ci_status
	IFS= read -r ci_conclusion
	IFS= read -r ci_url
} <<<"$ci_run"

ci_conclusion="${ci_conclusion:-pending}"
if [[ "$ci_status" != "completed" || "$ci_conclusion" != "success" ]]; then
	error "Main CI must pass before releasing. Current result: $ci_status/$ci_conclusion"
	printf 'CI run: %s\n' "$ci_url" >&2
	printf 'Run gh run watch %s --exit-status, then retry.\n' "$ci_run_id" >&2
	exit 1
fi

repository_url="$(gh repo view --json url --jq .url)"

printf 'Release: %s\n' "$tag"
printf 'Commit:  %s\n' "$commit"
printf 'CI:      %s\n' "$ci_url"

if [[ "$dry_run" == "1" ]]; then
	printf '\nDry run complete. Run ./scripts/release.sh to create and push %s.\n' "$tag"
	exit 0
fi

git tag -a "$tag" -m "release: $version"
if ! git push origin "$tag"; then
	git tag -d "$tag" >/dev/null
	error "Failed to push $tag. The local tag was deleted so the command can be retried."
	exit 1
fi

printf '\nRelease %s started.\n' "$tag"
printf 'Publish workflow: %s/actions/workflows/publish.yml\n' "$repository_url"
