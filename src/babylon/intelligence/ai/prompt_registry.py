"""Versioned narrator prompt artifacts.

Prompts are data, not code (Constitution III.12 — durable spec artifacts). The
registry version is derived from content bytes, so an edited prompt can never
ship with a stale version pin (closes the manual PROMPT_VERSION drift gap).
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Final

_DEFAULT_DIR: Final[Path] = (
    Path(__file__).resolve().parents[2] / "data" / "game" / "prompts" / "narrator"
)


class PromptRegistry:
    """Load-once registry of narrator prompt artifacts.

    :param root: directory containing ``*.txt`` prompt artifacts.
    :raises FileNotFoundError: if the directory is missing (loud, III.11).
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root: Final[Path] = root or _DEFAULT_DIR
        if not self._root.is_dir():
            raise FileNotFoundError(f"Prompt artifact dir missing: {self._root}")
        self._prompts: Final[dict[str, str]] = {
            p.stem: p.read_text(encoding="utf-8") for p in sorted(self._root.glob("*.txt"))
        }
        if not self._prompts:
            raise FileNotFoundError(f"No prompt artifacts in {self._root}")

    def get(self, name: str) -> str:
        """Return prompt text by artifact stem; KeyError on unknown name."""
        return self._prompts[name]

    def version(self) -> str:
        """Content-derived version: sha256 over (name, bytes) pairs, sorted."""
        h = hashlib.sha256()
        for name in sorted(self._prompts):
            h.update(name.encode("utf-8"))
            h.update(b"\x00")
            h.update(self._prompts[name].encode("utf-8"))
        return f"sha256:{h.hexdigest()[:12]}"


@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistry:
    """Process-wide registry over the default artifact directory."""
    return PromptRegistry()
