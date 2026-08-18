"""Installed Agent Plugin discovery."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

from ._errors import AgentPluginError
from ._files import FileInventory
from ._marker import MARKER_NAME, InvalidMarker, OutdatedMarker, PluginMarker
from ._plugin import Plugin


def locate(distribution_name: str) -> Plugin:
    """Return the Agent Plugin installed by a Python distribution.

    Raises:
        AgentPluginError: The distribution has no usable Agent Plugin marker.
    """
    if not distribution_name:
        raise AgentPluginError("A distribution name is required")

    try:
        distribution = metadata.distribution(distribution_name)
    except metadata.PackageNotFoundError:
        raise AgentPluginError(
            f"Python distribution {distribution_name!r} is not installed"
        ) from None

    return _root(distribution, distribution_name)


def installed() -> dict[str, Plugin]:
    """Return installed Agent Plugins keyed by distribution name."""
    plugins: dict[str, Plugin] = {}
    for distribution in metadata.distributions():
        marker = distribution.read_text(MARKER_NAME)
        if marker is None:
            continue

        name = distribution.metadata["Name"]
        if name is None:
            raise AgentPluginError(
                f"Distribution marker {MARKER_NAME!r} has no project name"
            )
        plugins[name] = _root(distribution, name, marker)

    return dict(sorted(plugins.items(), key=lambda item: item[0].casefold()))


def _root(
    distribution: metadata.Distribution,
    distribution_name: str,
    marker: str | None = None,
) -> Plugin:
    marker_text = marker if marker is not None else distribution.read_text(MARKER_NAME)
    if marker_text is None:
        raise AgentPluginError(
            f"Python distribution {distribution_name!r} has no Agent Plugin"
        )

    try:
        marker_value = PluginMarker.loads(marker_text)
    except OutdatedMarker as error:
        raise AgentPluginError(
            f"Python distribution {distribution_name!r} has outdated Agent Plugin "
            f"metadata. Reinstall the distribution to refresh {MARKER_NAME}"
        ) from error
    except InvalidMarker as error:
        raise AgentPluginError(
            f"Python distribution {distribution_name!r} has an invalid {MARKER_NAME}"
        ) from error

    configured = Path(marker_value.root)
    candidate = (
        configured if configured.is_absolute() else distribution.locate_file(configured)
    )
    inventory = FileInventory.select(
        Path(str(candidate)),
        marker_value.files,
        kind="Agent Plugin",
        required="plugin.json",
    )
    return Plugin._from_inventory(inventory)
