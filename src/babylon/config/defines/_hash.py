"""The single canonical defines-hash (Program 27 spec §7, III.12(a)).

Byte layout: ``model_dump(mode="json")`` → ``json.dumps(payload,
sort_keys=True, separators=(",", ":"), ensure_ascii=True)`` → UTF-8 →
SHA-256 full 64-hex. No ``default=`` fallback: a non-JSON-native value in
the schema raises ``TypeError`` loudly (III.11) instead of hashing an
implementation-defined ``str()``.
"""

from __future__ import annotations

import hashlib
import json

from babylon.config.defines._assembler import GameDefines


def canonical_defines_hash(defines: GameDefines) -> str:
    """Compute the one canonical fingerprint of a ``GameDefines`` snapshot.

    :param defines: the coefficients to fingerprint.
    :returns: a 64-character lowercase hex SHA-256 digest.
    """
    payload = defines.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
