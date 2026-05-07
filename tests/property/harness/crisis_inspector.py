"""Crisis-state classifier for the spec-054 alpha-smoothing invariant (US4).

Per ``research.md §5``: the steady-state predicate is

    phase is None  OR  phase == CrisisPhase.NORMAL

NOT just ``phase is None``. ``CrisisPhase`` (in
``babylon/economics/tick/types.py``) has 5 values
(``NORMAL``, ``ONSET``, ``EARLY``, ``DEEP``, ``RECOVERY``) and ``NORMAL`` is
the canonical steady-state marker. ``RECOVERY`` is treated as crisis because
re-equilibration legitimately resets coefficients.

The inspector handles two access patterns observed in the codebase:

- ``state.crisis_phase`` directly (e.g., transition_engine call sites)
- ``state.crisis_state.phase`` (e.g., ``CountyEconomicState``)

Missing attributes default to steady state per the spec-054 edge case.
"""

from __future__ import annotations

from typing import Any

from babylon.economics.tick.types import CrisisPhase


class CrisisStateInspector:
    """Classify a state object as steady-state or crisis-phase.

    Stateless helper — instantiation is essentially free.
    """

    def is_steady_state(self, state: Any) -> bool:
        """Return ``True`` iff the state's crisis phase indicates steady state.

        Args:
            state: Any object that may carry ``crisis_phase`` directly or
                ``crisis_state.phase`` (or neither — missing attributes
                default to steady).

        Returns:
            ``True`` iff phase is ``None`` or ``CrisisPhase.NORMAL``.
        """
        phase = self._extract_phase(state)
        return phase is None or phase == CrisisPhase.NORMAL

    @staticmethod
    def _extract_phase(state: Any) -> CrisisPhase | None:
        """Read crisis phase from either of the two known access patterns."""
        direct = getattr(state, "crisis_phase", None)
        if isinstance(direct, CrisisPhase):
            return direct
        if isinstance(direct, str):
            try:
                return CrisisPhase(direct)
            except ValueError:
                return None
        nested = getattr(state, "crisis_state", None)
        if nested is not None:
            inner = getattr(nested, "phase", None)
            if isinstance(inner, CrisisPhase):
                return inner
            if isinstance(inner, str):
                try:
                    return CrisisPhase(inner)
                except ValueError:
                    return None
        return None


__all__ = ["CrisisStateInspector"]
