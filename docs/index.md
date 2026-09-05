---
layout: home
title: agent-plugins
description: Ship agent instructions and integrations with Python packages.

hero:
  text: Ship Agent Plugins with Python packages.
  tagline: Carry agent instructions and integrations through Python packaging, then discover their installed paths through a small Python API or command-line interface.
  image:
    light: /brand/agent-plugins-lockup-vertical-light.svg
    dark: /brand/agent-plugins-lockup-vertical-dark.svg
    alt: agent-plugins logo
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: Learn the model
      link: /guide/what-is-an-agent-plugin
    - theme: alt
      text: API reference
      link: /reference/python-api

features:
  - title: Package one versioned unit
    details: Carry reusable agent instructions and tool-server configuration in installable packages and source archives.
    link: /guide/getting-started
    linkText: Package a plugin
  - title: Keep the portable layout
    details: Preserve the Agent Plugins directory format inside standard Python packaging artifacts.
    link: /guide/plugin-directory
    linkText: Organize the directory
  - title: Inspect installed contents
    details: Locate plugin roots, traverse instruction files, and read normalized configuration from Python.
    link: /guide/inspect-installed
    linkText: Inspect an installation
---

## One lifecycle from source to installed access

<ol class="lifecycle">
  <li><strong>Author</strong><span>Create the plugin directory.</span></li>
  <li><strong>Plan</strong><span>Select the files for packaging.</span></li>
  <li><strong>Build</strong><span>Stage or package plugin files for the build type.</span></li>
  <li><strong>Install</strong><span>Place package contents in the environment.</span></li>
  <li><strong>Discover</strong><span>Resolve the installed plugin root.</span></li>
  <li><strong>Inspect</strong><span>Read skills, manifest data, and tool-server entries.</span></li>
</ol>

<div class="home-install">

## Package your first plugin

The quickstart creates a complete Python project and Agent Skill, previews the selected files, builds a wheel, installs it, and prints the installed plugin root.

[Build and locate an Agent Plugin →](/guide/getting-started)

</div>
