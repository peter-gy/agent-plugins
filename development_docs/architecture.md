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
             BuildPlan
                  │
       delegated backend artifact
                  │
                  ├── regular wheel → plugin payload + marker ───┐
                  ├── sdist → staged plugin payload               │
                  │                │                               │
                  │                ▼                               │
                  │           rebuilt wheel → payload + marker ───┤
                  └── editable wheel → authored-root marker ──────┤
                                                                   │
                                                                   ▼
                                                        install distribution
                                                                   │
                                                                   ▼
                                                    importlib.metadata lookup
                                                                   │
                                                                   ▼
                                         FileInventory → Plugin → lazy documents
```

## Ownership map

| Owner | Contract |
| --- | --- |
| `_build/plan.py` | Resolve project configuration and produce ordered source-to-target mappings |
| `_build/backend.py` | Delegate PEP 517 and PEP 660 hooks, then augment artifacts |
| `_build/wheel.py` | Add regular or editable marker data, copy plugin files, and rebuild `RECORD` |
| `_build/sdist.py` | Stage the selected payload under `.agent-plugin/` |
| `build/uv_build.py` | Public uv_build adapter module |
| `build/hatchling.py` | Public Hatchling adapter module |
| `_marker.py` | Encode and decode `agent_plugins.json` |
| `_discovery.py` | Resolve markers through `importlib.metadata` |
| `_files.py` | Own resolved roots, validated relative names, and subtree inventories |
| `_plugin.py` | Compose manifest, MCP, and skill handles around one inventory |
| `_skill.py` | Expose skill paths, source sections, and tree rendering |
| `_schema/manifest.py` | Dispatch and cache manifest validation |
| `_schema/mcp.py` | Dispatch and cache MCP validation against a manifest |
| `_schema/skill.py` | Split UTF-8 `SKILL.md` source at exact delimiters |
| `_schema/v1/` | Validate Agent Plugins 1.0.0 documents |
| `_tree.py` | Render bounded deterministic ASCII trees |
| `_cli.py` | Parse commands and render human or JSON output |

## Dependency direction

The public `agent_plugins` package re-exports build-plan, discovery, filesystem, schema-value, and diagnostic types. `agent_plugins.build` separately exports the low-level `BuildBackend`.

Private build code depends on the plan and marker codec. Runtime discovery depends on the marker codec and file inventory. Schema loaders do not depend on build or discovery code.

The CLI parses input, calls public-domain functions, and renders output. Core modules do not depend on terminal state.

## Public object model

`Plugin` and `Skill` are slotted filesystem handles. Their equality and hash use the resolved root and selected relative filenames. Parsed document content does not participate.

`Manifest` and `MCPConfig` are lazy document handles. `Author`, MCP server values, `ValidationIssue`, `BuildPlan`, and `FileMapping` are frozen values.

`Plugin`, `Skill`, `Manifest`, and `MCPConfig` implement `os.PathLike`. `Plugin` and `Skill` also expose text and notebook tree renderings.

## Change rules

- Preserve the boundary between file selection and document validation.
- Preserve the marker as the single handoff from artifact creation to installed discovery.
- Keep schema-version dispatch outside normalized value models.
- Keep agent-client activation, placeholder expansion, permissions, and MCP connection behavior outside this package.
- Update public docs, the bundled Agent Skill, tests, and artifact verification together when a supported contract changes.
