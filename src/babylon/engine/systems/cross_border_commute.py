"""Cross-border commute classifier (Spec 063 T080 / T037).

Stateless rule that resolves a LODES destination identifier into one of
three boundary categories:

    1. In-study-area hex (NodeKind.HEX, the H3 cell ID)
    2. Domestic out-of-study-area (NodeKind.EXTERNAL, "rest_of_usa")
    3. Canadian destination (NodeKind.EXTERNAL, "canada")

Implements FR-023..FR-028 per data-model.md §1.4. Per research.md §4, the
canonical LODES dataset does NOT include Canadian destinations; the
Canadian branch fires only for synthetic test rows OR for rows produced by
the Option B :class:`BorderCommuteSynthesisLoader` when BTS + StatCan + WWE
data is wired up.

The ``domestic_states`` constructor parameter is the single source of truth
for what counts as US-domestic (per the F1 remediation in 2026-05-13
:command:`/speckit.analyze`).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from babylon.domain.economics.node_kinds import NodeKind

logger = logging.getLogger(__name__)

# 15-digit Census 2020 block ID format: state(2) + county(3) + tract(6) + block(4).
_BLOCK_CODE_RE = re.compile(r"^\d{15}$")
# 2-digit FIPS state code form.
_FIPS_STATE_RE = re.compile(r"^[0-9]{2}$")


@dataclass(frozen=True)
class CrossBorderClassification:
    """Resolved (kind, node_id) for one LODES destination identifier."""

    dest_kind: NodeKind
    dest_node_id: str


class CrossBorderCommuteClassifier:
    """Stateless classifier mapping LODES destination IDs to boundary categories.

    See data-model.md §1.4 for the 4-rule classification:

      1. If ``dest_id`` is an H3 res-7 cell in ``study_area_hexes`` → HEX.
      2. Else if a 15-digit Census block with state-prefix in
         ``domestic_states`` → EXTERNAL/rest_of_usa.
      3. Else if a 15-digit code with state-prefix NOT in
         ``domestic_states`` → EXTERNAL/canada.
      4. Else (unrecognized format) → EXTERNAL/rest_of_usa, with one audit
         log entry per unique unmapped destination (FR-028).
    """

    def __init__(
        self,
        *,
        study_area_hexes: frozenset[str],
        study_area_states: frozenset[str],
        domestic_states: frozenset[str],
    ) -> None:
        if not study_area_hexes:
            raise ValueError("study_area_hexes MUST be non-empty")
        if not study_area_states:
            raise ValueError("study_area_states MUST be non-empty")
        if not domestic_states:
            raise ValueError("domestic_states MUST be non-empty")
        for code in study_area_states:
            if not _FIPS_STATE_RE.match(code):
                raise ValueError(f"study_area_states entry {code!r} is not a 2-digit FIPS code")
        for code in domestic_states:
            if not _FIPS_STATE_RE.match(code):
                raise ValueError(f"domestic_states entry {code!r} is not a 2-digit FIPS code")
        if not study_area_states <= domestic_states:
            raise ValueError(
                f"domestic_states MUST be a superset of study_area_states; "
                f"missing: {sorted(study_area_states - domestic_states)}"
            )

        self.study_area_hexes = study_area_hexes
        self.study_area_states = study_area_states
        self.domestic_states = domestic_states
        # Track unique unmapped destinations per process to honor FR-028
        # ("one audit log entry per unique unmapped destination per session").
        self._unmapped_seen: set[str] = set()

    def classify(self, dest_id: str) -> CrossBorderClassification:
        """Resolve a LODES destination identifier to (kind, node_id)."""
        # Rule 1 — in-study-area H3 cell
        if dest_id in self.study_area_hexes:
            return CrossBorderClassification(dest_kind=NodeKind.HEX, dest_node_id=dest_id)

        # Rules 2/3 — Census 2020 block codes
        if _BLOCK_CODE_RE.match(dest_id):
            state_prefix = dest_id[:2]
            if state_prefix in self.domestic_states:
                # Rule 2 — domestic out-of-study-area
                return CrossBorderClassification(
                    dest_kind=NodeKind.EXTERNAL, dest_node_id="rest_of_usa"
                )
            # Rule 3 — non-US (canonical mapping: canada per FR-023)
            return CrossBorderClassification(dest_kind=NodeKind.EXTERNAL, dest_node_id="canada")

        # Rule 4 — unrecognized destination format; default to rest_of_usa
        if dest_id not in self._unmapped_seen:
            self._unmapped_seen.add(dest_id)
            logger.warning(
                "CrossBorderCommuteClassifier: unmapped LODES destination %r — "
                "defaulted to rest_of_usa per FR-028",
                dest_id,
            )
        return CrossBorderClassification(dest_kind=NodeKind.EXTERNAL, dest_node_id="rest_of_usa")


__all__ = ["CrossBorderClassification", "CrossBorderCommuteClassifier"]
