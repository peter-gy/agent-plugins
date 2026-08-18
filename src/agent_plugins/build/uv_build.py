"""Agent Plugin adapter for uv_build."""

from .._build.backend import BuildBackend

_backend = BuildBackend("uv_build")

build_editable = _backend.build_editable
build_sdist = _backend.build_sdist
build_wheel = _backend.build_wheel
get_requires_for_build_editable = _backend.get_requires_for_build_editable
get_requires_for_build_sdist = _backend.get_requires_for_build_sdist
get_requires_for_build_wheel = _backend.get_requires_for_build_wheel

__all__ = [
    "build_editable",
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_editable",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
]
