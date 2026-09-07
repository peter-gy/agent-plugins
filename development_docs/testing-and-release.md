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
6. Uses the installed Python API and CLI to attach a synthetic external wheel, installs it, and verifies discovery.

## Test boundaries

| Boundary | Primary evidence |
| --- | --- |
| Build-plan selection and CLI JSON | `tests/test_plan.py` |
| Public wheel attachment, preservation, validation, signatures, and `RECORD` | `tests/test_wheel.py` |
| CLI attachment output, warnings, and exit statuses | `tests/test_cli.py` |
| Backend parity, sdist rebuilds, editable markers, and sdist modes | `tests/test_build_backends.py` |
| Installed distribution discovery and marker failures | `tests/test_discovery.py` |
| Project-selected plugin inventory, paths, display, named skills | `tests/test_plugin.py` |
| Exact skill source, checked files, caching, paths, display | `tests/test_skill.py` |
| Manifest normalization, immutability, issues, caching | `tests/test_manifest.py` |
| MCP transports, security checks, partial validation, caching | `tests/test_mcp.py` |
| Pure stdio launch resolution and subprocess inputs | `tests/test_mcp_resolution.py` |
| Documented quickstart builds and installs library code with its skill | `tests/test_docs.py` |

CI runs pytest on Linux for Python 3.10 through 3.14 and on Windows and macOS for Python 3.12. The quality job runs formatting, lint, both type checkers, actionlint, ShellCheck, and distribution verification, then uploads the verified wheel and source distribution as the `dist` artifact.

`ci.yml` also exposes a [reusable workflow](https://docs.github.com/en/actions/concepts/workflows-and-actions/reusing-workflow-configurations), allowing publishing to run the same checks on the tagged source. The publish job downloads the artifact from that run after every Python matrix job and the quality job succeed.

The documentation workflow installs `docs/pnpm-lock.yaml`, runs the TypeScript check and VitePress build for pull requests, and deploys the built site from `main`. Build verification enumerates the Markdown sources and checks their HTML output, downloadable Markdown, canonical URLs, and coverage in the generated text indexes. Configure the repository's Pages source as GitHub Actions before the first deployment.

For a deployment, `actions/configure-pages` supplies the repository or custom-domain base path and complete site URL. The workflow passes those values as `BASE_PATH` and `SITE_URL`. VitePress uses `BASE_PATH` for assets and navigation, while canonical, sitemap, and social metadata use `SITE_URL`. Local development omits both variables, serves from `/`, and keeps the published site URL as the metadata fallback.

## Prepare a release

Create a release pull request that updates the project version and lockfile:

```console
uv version --bump patch
```

After the release commit reaches `main` and its push CI succeeds:

```console
git pull --ff-only origin main
./scripts/release.sh --dry-run
./scripts/release.sh
```

The dry run is a networked release preflight. It requires GitHub authentication, fetches `main` and tags, verifies a clean synchronized `main`, checks the final version and absent tag, verifies the exact commit's successful push CI run, resolves the repository URL, and stops before creating the tag.

The release run creates and pushes an annotated version tag. Publishing follows this dependency order:

```text
tag preflight → shared CI checks and artifact build → PyPI publish
             → public installation verification → GitHub release
```

Use the release script for tag creation. It checks the existing successful `main` CI run before tagging. The publish workflow verifies the annotated tag, package version, and membership in `origin/main`, then independently runs the shared CI checks before publishing the resulting artifacts.

PyPI trusted publishing is configured against `.github/workflows/publish.yml` and the repository `pypi` environment.

## Release recovery

The release script refuses a dirty tree, a non-`main` branch, a local branch that differs from `origin/main`, a non-final package version, a missing successful CI run, or an existing local or fetched tag.

If tag push fails after local tag creation, inspect remote state before retrying. If publishing fails after a tag reaches GitHub, keep the tag fixed and repair the workflow or trusted-publisher configuration against that commit.
