"""Shared PEP 517 and PEP 660 backend hooks."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from .plan import build_plan
from .sdist import write_sdist_plugin
from .wheel import write_wheel_plugin

ConfigSettings = dict[str, object] | None


class _BuildBackend(Protocol):
    def build_wheel(
        self,
        wheel_directory: str,
        config_settings: ConfigSettings = None,
        metadata_directory: str | None = None,
    ) -> str: ...

    def build_sdist(
        self,
        sdist_directory: str,
        config_settings: ConfigSettings = None,
    ) -> str: ...

    def build_editable(
        self,
        wheel_directory: str,
        config_settings: ConfigSettings = None,
        metadata_directory: str | None = None,
    ) -> str: ...

    def get_requires_for_build_wheel(
        self, config_settings: ConfigSettings = None
    ) -> Sequence[str]: ...

    def get_requires_for_build_sdist(
        self, config_settings: ConfigSettings = None
    ) -> Sequence[str]: ...

    def get_requires_for_build_editable(
        self, config_settings: ConfigSettings = None
    ) -> Sequence[str]: ...


@dataclass(frozen=True, slots=True)
class BuildBackend:
    """Add Agent Plugin artifacts around an existing build backend."""

    module: str

    def build_wheel(
        self,
        wheel_directory: str,
        config_settings: ConfigSettings = None,
        metadata_directory: str | None = None,
    ) -> str:
        """Build a wheel and add its plugin files."""
        plan = build_plan(Path.cwd())
        filename = self._delegate.build_wheel(
            wheel_directory, config_settings, metadata_directory
        )
        write_wheel_plugin(Path(wheel_directory) / filename, plan)
        return filename

    def build_sdist(
        self,
        sdist_directory: str,
        config_settings: ConfigSettings = None,
    ) -> str:
        """Build an sdist and stage its plugin files."""
        plan = build_plan(Path.cwd())
        filename = self._delegate.build_sdist(sdist_directory, config_settings)
        write_sdist_plugin(Path(sdist_directory) / filename, plan)
        return filename

    def build_editable(
        self,
        wheel_directory: str,
        config_settings: ConfigSettings = None,
        metadata_directory: str | None = None,
    ) -> str:
        """Build an editable wheel that points at the source plugin root."""
        plan = build_plan(Path.cwd())
        filename = self._delegate.build_editable(
            wheel_directory, config_settings, metadata_directory
        )
        write_wheel_plugin(Path(wheel_directory) / filename, plan, editable=True)
        return filename

    def get_requires_for_build_wheel(
        self, config_settings: ConfigSettings = None
    ) -> list[str]:
        """Return additional wheel build requirements from the wrapped backend."""
        return list(self._delegate.get_requires_for_build_wheel(config_settings))

    def get_requires_for_build_sdist(
        self, config_settings: ConfigSettings = None
    ) -> list[str]:
        """Return additional sdist build requirements from the wrapped backend."""
        return list(self._delegate.get_requires_for_build_sdist(config_settings))

    def get_requires_for_build_editable(
        self, config_settings: ConfigSettings = None
    ) -> list[str]:
        """Return additional editable build requirements from the wrapped backend."""
        return list(self._delegate.get_requires_for_build_editable(config_settings))

    @property
    def _delegate(self) -> _BuildBackend:
        return cast(_BuildBackend, importlib.import_module(self.module))
