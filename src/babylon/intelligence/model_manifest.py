"""The signed model manifest (D3, ADR096).

The manifest ships in the package (``data/model_manifest.toml``) → inside the
signed Nix closure, so the closure narinfo signature IS the manifest
signature. Weights never enter the store; ``babylon doctor --provision``
(see ``provision.py``) fetches them per this manifest into
``~/.local/share/babylon/models/``.

Entries are owner-provisioned: an entry is fetched only when ``available`` is
true, which the model validator ties to a complete ``url``/``sha256``/``bytes``
triple. Until the owner uploads weights to the babylon-data R2 bucket, every
entry is unavailable and provision is a loud no-op.
"""

from __future__ import annotations

import tomllib
from enum import StrEnum
from importlib import resources
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class ModelKind(StrEnum):
    CHAT = "chat"
    EMBED = "embed"


class ModelEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: ModelKind
    available: bool = False
    url: str | None = None
    sha256: str | None = None
    bytes: int | None = None
    dims: int | None = None

    @model_validator(mode="after")
    def _check_completeness(self) -> ModelEntry:
        # An AVAILABLE entry must carry a complete, verifiable source triple —
        # provision refuses to fetch anything it cannot sha256-verify (III.11).
        if self.available and (self.url is None or self.sha256 is None or self.bytes is None):
            raise ValueError(
                f"model {self.name!r} is available=true but missing url/sha256/bytes; "
                "an available entry must be fully verifiable"
            )
        # Embedding entries must pin their dimension (the vector(N) column, D5).
        if self.kind is ModelKind.EMBED and self.dims is None:
            raise ValueError(f"embed model {self.name!r} must declare dims")
        return self


class ModelManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    models: list[ModelEntry]

    def available_entries(self) -> list[ModelEntry]:
        return [entry for entry in self.models if entry.available]

    def chat_entries(self) -> list[ModelEntry]:
        return [entry for entry in self.models if entry.kind is ModelKind.CHAT]

    def embed_entries(self) -> list[ModelEntry]:
        return [entry for entry in self.models if entry.kind is ModelKind.EMBED]


def parse_manifest(raw: dict[str, Any]) -> ModelManifest:
    """Parse a TOML mapping (``[[model]]`` array) into a validated manifest."""
    return ModelManifest(models=list(raw.get("model", [])))


def load_bundled_manifest() -> ModelManifest:
    """Load the manifest shipped inside the package (the signed closure)."""
    data = resources.files("babylon.intelligence.data").joinpath("model_manifest.toml")
    with resources.as_file(data) as path, path.open("rb") as handle:
        raw = tomllib.load(handle)
    return parse_manifest(raw)
