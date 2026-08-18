"""Locate and inspect Agent Plugins installed by Python distributions."""

from ._build.plan import BuildPlan, FileMapping, build_plan
from ._discovery import installed, locate
from ._errors import AgentPluginError
from ._plugin import Plugin
from ._schema import (
    Author,
    Manifest,
    MCPConfig,
    MCPServer,
    SSEServer,
    StdioServer,
    StreamableHTTPServer,
    ValidationError,
    ValidationIssue,
)
from ._skill import Skill

__all__ = [
    "AgentPluginError",
    "Author",
    "BuildPlan",
    "FileMapping",
    "MCPConfig",
    "MCPServer",
    "Manifest",
    "Plugin",
    "SSEServer",
    "Skill",
    "StdioServer",
    "StreamableHTTPServer",
    "ValidationError",
    "ValidationIssue",
    "build_plan",
    "installed",
    "locate",
]
