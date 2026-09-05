# Development documentation

These notes describe the implementation contracts that maintainers need when changing `agent-plugins`.

Start with [Architecture](architecture.md), then follow the contract affected by the change:

- [Artifact lifecycle](artifacts.md) covers build planning, delegated backends, wheel rewriting, source-distribution staging, and editable markers.
- [Discovery and validation](validation.md) covers installed metadata, selected file inventories, lazy document loading, schema dispatch, and MCP security checks.
- [Testing and release](testing-and-release.md) maps local checks, CI, artifact verification, and the tag-driven publishing flow.

User-facing behavior belongs in `docs/`. Keep module ownership, archive mechanics, marker encoding, and release operations in this directory.
