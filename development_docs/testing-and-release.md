# Testing and release

The repository validates source behavior, static typing, packaging artifacts, installed discovery, and the public PyPI release through separate checks.

## Local checks

Install the locked environment and run:

```console
uv sync --locked
uv run ruff format --check src tests
uv run ruff check src tests
uv run ty check
uv run pyrefly check
uv run pytest -q
./scripts/build-dist.sh
pnpm --dir docs install --frozen-lockfile
pnpm --dir docs typecheck
pnpm --dir docs build
```

`scripts/build-dist.sh` removes the repository `dist/` directory, builds the wheel and source distribution, then calls `scripts/verify-dist.sh`.

## Serve documentation locally

[Portless](https://portless.sh/) assigns the VitePress development server an available port and exposes it through a named `.localhost` URL:

```console
pnpm --dir docs dev
```

The main checkout uses `https://docs.agent-plugins.localhost`. A linked Git worktree receives a branch-prefixed subdomain so concurrent documentation servers do not collide.

Portless may request permission to create and trust a local certificate authority and bind its HTTPS proxy on the first run. Run `pnpm --dir docs dev:server` to start VitePress directly with its ordinary local URL.

The distribution verifier:

1. Requires one wheel and one `.tar.gz` source distribution.
2. Rebuilds a wheel from the source distribution.
3. Installs the direct and rebuilt wheels in isolated targets.
4. Verifies plugin file bytes, discovery, manifest access, skill access, CLI `locate`, and CLI `list --json`.
5. Creates an editable installation and checks that discovery resolves the authored root.

## Test boundaries

| Boundary | Primary evidence |
| --- | --- |
| Build-plan selection and CLI JSON | `tests/test_plan.py` |
| Wheel, sdist, rebuilt wheel, editable marker, `RECORD`, file modes | `tests/test_build_backends.py` |
| Installed distribution discovery and marker failures | `tests/test_discovery.py` |
| Plugin inventory, paths, display, skill recognition | `tests/test_plugin.py` |
| Skill source splitting, caching, paths, display | `tests/test_skill.py` |
| Manifest normalization, immutability, issues, caching | `tests/test_manifest.py` |
| MCP transports, security checks, partial validation, caching | `tests/test_mcp.py` |
| User-facing `agent-plugins` version pins | `tests/test_docs.py` |

CI runs pytest on Linux for Python 3.10 through 3.14 and on Windows for Python 3.12. The quality job runs formatting, lint, both type checkers, ShellCheck, and distribution verification.

The documentation workflow installs `docs/pnpm-lock.yaml`, runs the TypeScript check and VitePress build for pull requests, and deploys the built site from `main`. Configure the repository's Pages source as GitHub Actions before the first deployment.

For a deployment, `actions/configure-pages` supplies the repository or custom-domain base path and complete site URL. The workflow passes those values as `BASE_PATH` and `SITE_URL`. VitePress uses `BASE_PATH` for assets and navigation, while canonical, sitemap, and social metadata use `SITE_URL`. Local development omits both variables, serves from `/`, and keeps the published site URL as the metadata fallback.

## Prepare a release

Create a release pull request that updates the project version and lockfile:

```console
uv version --bump patch
```

Update the exact `agent-plugins==X.Y.Z` pins in the README, public docs, and bundled Agent Skill in the same pull request. `tests/test_docs.py` checks every documented package pin against `project.version`.

After the release commit reaches `main` and its push CI succeeds:

```console
git pull --ff-only origin main
./scripts/release.sh --dry-run
./scripts/release.sh
```

The dry run is a networked release preflight. It requires GitHub authentication, fetches `main` and tags, verifies a clean synchronized `main`, checks the final version and absent tag, verifies the exact commit's successful push CI run, resolves the repository URL, and stops before creating the tag.

The release run creates and pushes an annotated version tag. The publish workflow builds and verifies the artifacts, publishes through the PyPI trusted publisher, verifies the public package, and creates a GitHub release.

Use the release script for tag creation. The publish workflow checks that the tagged commit belongs to `origin/main`, while the script supplies the stricter exact-commit CI gate. A manually pushed tag can bypass that stricter preflight.

PyPI trusted publishing is configured against `.github/workflows/publish.yml` and the repository `pypi` environment.

## Release recovery

The release script refuses a dirty tree, a non-`main` branch, a local branch that differs from `origin/main`, a non-final package version, a missing successful CI run, or an existing local or fetched tag.

If tag push fails after local tag creation, inspect remote state before retrying. If publishing fails after a tag reaches GitHub, keep the tag fixed and repair the workflow or trusted-publisher configuration against that commit.
