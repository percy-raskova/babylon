"""Retired Python game-managed PostgreSQL runtime namespace.

Gate 3 moved authoritative schema ownership, ticking, and restart to the
``babylon-runtime`` Rust composition root.  This package intentionally exports
nothing: retaining a Python facade here would recreate the prohibited dual
authority boundary.
"""

from __future__ import annotations

__all__: list[str] = []
