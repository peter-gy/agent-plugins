# Verify package artifacts

Treat source and installed inspection as two views of the same selected plugin:

```python
import agent_plugins as ap

source = ap.Plugin.from_project(".")
installed = ap.locate("my-package")

assert source.manifest.name == installed.manifest.name
assert [path.relative_to(source.path) for path in source.files] == [
    path.relative_to(installed.path) for path in installed.files
]
```

Verify every release boundary:

1. Run `agent-plugins plan PROJECT` and inspect every selected path.
2. Build a wheel and source distribution through the configured adapter, or
   attach the plugin to the externally built wheel.
3. Rebuild a wheel from the source distribution.
4. Install the direct and rebuilt wheels in clean environments.
5. Run `agent-plugins read my-package` and `ap.read("my-package")` against both
   installed wheels. Pass an explicit skill name when it differs from the
   distribution name. Compare the Python briefing with CLI `--skill` output.
6. Install the project as editable and confirm `locate()` resolves the authored
   plugin root.
7. Compare source and installed file inventories and bytes.
8. Access `manifest.name`, every `skill.source`, and `mcp.servers` when present
   to execute supported document validation.
9. Confirm each `skill.file("SKILL.md")` and referenced resource is selected.
10. Run an Agent Skills validator against every authored skill directory.

Let `AgentPluginError` fail missing configuration, unusable paths, or discovery.
Let `ValidationError` fail invalid manifest, MCP, or skill documents. Artifact
verification should exercise the CLI through the installed console script as
well as the Python API.

When the package exposes module help, inspect its captured output and follow
the [briefing handoff scenarios](briefings.md#verify-the-handoff). Confirm that
each referenced setup or workflow file is available in the installed inventory.
