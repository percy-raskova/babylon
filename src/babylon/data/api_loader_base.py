"""Base helpers for API-backed data loaders."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from babylon.data.loader_base import DataLoader, LoaderConfig


class ApiLoaderBase(DataLoader):
    """DataLoader base class with API client lifecycle helpers."""

    def __init__(self, config: LoaderConfig | None = None) -> None:
        super().__init__(config)
        self._client: Any | None = None

    def _close_client(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    @contextmanager
    def _client_scope(self, client: Any) -> Iterator[Any]:
        self._close_client()
        self._client = client
        try:
            yield client
        finally:
            self._close_client()
