# Architecture

`agent-plugins` has two public jobs:

1. Add an Agent Plugin directory to Python packaging artifacts.
2. Locate and inspect Agent Plugins installed by Python distributions.

The build and runtime halves meet at one installed metadata file, `agent_plugins.json`.

## System flow

```text
pyproject.toml + authored plugin directory
                       │
                       ▼
                  build_plan()
                       │
                       ▼
                  BuildPlan ──────────────→ FileInventory → Plugin.from_project()
                       │
                       ├──────────────────→ delegated backend artifact
                       │                    ┌──────────┼──────────┐
                       │                    ▼          ▼          ▼
                       │               regular wheel  sdist  editable wheel
other source → supplied BuildPlan           │          │          │
                       │                    │     rebuilt wheel  │
                       └─→ attach_wheel ─────┴──────────┴──────────┘
                                                │
                                                ▼
                                     plugin payload or source marker
                                                │
                                                ▼
                                      install distribution
                                                │
                                                ▼
                                   importlib.metadata lookup
                                                │
                                                ▼
                                FileInventory → locate() → Plugin
```

## Ownership map

| Owner | Contract |
| --- | --- |
| `_build/plan.py` | Select authored files, replay staged payloads, and validate source-to-target mappings |
| `_build/backend.py` | Delegate PEP 517 and PEP 660 hooks, then augment artifacts |
| `_build/wheel.py` | Own attachment, temporary artifact lifetime, publication, and `WheelAttachment` results |
| `_build/wheel_archive.py` | Validate ZIP members, replace plugin payloads and markers, and rebuild `RECORD` |
| `_build/sdist.py` | Stage the selected payload under `.agent-plugin/` |
| `build/uv_build.py` | Public uv_build adapter module |
| `build/hatchling.py` | Public Hatchling adapter module |
| `_marker.py` | Encode and decode `agent_plugins.json` |
| `_discovery.py` | Resolve markers through `importlib.metadata` |
| `_files.py` | Own resolved roots, validated relative names, subtree inventories, and selected-file lookup |
| `_plugin.py` | Construct project-selected handles and compose named manifest, MCP, and skill access around one inventory |
| `_skill.py` | Expose exact skill source, checked selected files, native joins, and tree rendering |
| `_schema/manifest.py` | Dispatch and cache manifest validation |
| `_schema/mcp.py` | Dispatch and cache MCP validation and expose the `MCPConfig` facade |
| `_mcp.py` | Resolve validated stdio declarations against current files, data directories, and environment values |
| `_schema/models.py` | Hold immutable normalized document and stdio launch values |
| `_schema/skill.py` | Split UTF-8 `SKILL.md` source at exact delimiters |
| `_schema/v1/` | Validate Agent Plugins 1.0.0 documents |
| `_tree.py` | Render bounded deterministic ASCII trees |
| `_cli.py` | Parse commands and render human or JSON output |

## Dependency direction

The public `agent_plugins` package re-exports build planning, wheel attachment, discovery, filesystem, schema-value, and diagnostic types. `agent_plugins.build` separately exports the low-level `BuildBackend`.

Artifact operations depend on plan validation and archive writers. Archive writers depend on plan values and the marker codec. Runtime discovery depends on the marker codec and file inventory. Project inspection composes build planning with the same inventory model.

Versioned schema loaders produce normalized values. Stdio resolution consumes those values and the selected inventory, independently of JSON parsing. `MCPConfig` composes cached document access with uncached launch preparation. Schema loaders and launch preparation do not depend on build or discovery code.

The CLI parses input, calls public-domain functions, and renders output. Core modules do not depend on terminal state.

## Public object model

`Plugin` and `Skill` are slotted filesystem handles. Their equality and hash use the resolved root and selected relative filenames. Parsed document content does not participate.

`Manifest` and `MCPConfig` are lazy document handles. `Author`, MCP server values, `ResolvedStdioServer`, `ValidationIssue`, `BuildPlan`, `FileMapping`, and `WheelAttachment` are frozen values.

`Plugin`, `Skill`, `Manifest`, and `MCPConfig` implement `os.PathLike`. `Plugin` and `Skill` also expose text and notebook tree renderings.

## Change rules

- Preserve the boundary between file selection and document validation.
- Preserve the marker as the single handoff from artifact creation to installed discovery.
- Keep schema-version dispatch outside normalized value models.
- Keep stdio resolution transport-neutral. Process creation, permissions, logging, and MCP connection behavior remain outside this package.
- Update public docs, the bundled Agent Skill, tests, and artifact verification together when a supported contract changes.
