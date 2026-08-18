"""Cache one value or exception per document object."""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import Generic, TypeVar, cast

T = TypeVar("T")
_UNSET = object()


class LazyResult(Generic[T]):
    """Evaluate a loader once and cache either its value or its exception."""

    __slots__ = ("_error", "_loader", "_lock", "_value")

    def __init__(self, loader: Callable[[], T]) -> None:
        self._loader: Callable[[], T] | None = loader
        self._lock = Lock()
        self._value: T | object = _UNSET
        self._error: Exception | object = _UNSET

    def get(self) -> T:
        """Return the cached value or raise the cached exception."""
        if self._value is not _UNSET:
            return cast(T, self._value)
        if self._error is not _UNSET:
            raise cast(Exception, self._error)

        with self._lock:
            if self._value is not _UNSET:
                return cast(T, self._value)
            if self._error is not _UNSET:
                raise cast(Exception, self._error)

            loader = self._loader
            if loader is None:
                raise RuntimeError("Lazy loader is unavailable")
            try:
                self._value = loader()
            except Exception as error:
                self._error = error
                raise
            finally:
                self._loader = None
        return self._value
