"""Package and inspect Agent Plugins through Python distributions."""

from ._build.plan import BuildPlan, FileMapping, build_plan
from ._build.wheel import WheelAttachment, attach_wheel
from ._discovery import installed, locate
from ._errors import AgentPluginError
from ._plugin import Plugin
from ._schema import (
    Author,
    Manifest,
    MCPConfig,
    MCPServer,
    ResolvedStdioServer,
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
    "ResolvedStdioServer",
    "SSEServer",
    "Skill",
    "StdioServer",
    "StreamableHTTPServer",
    "ValidationError",
    "ValidationIssue",
    "WheelAttachment",
    "attach_wheel",
    "build_plan",
    "installed",
    "locate",
]
