"""The opposition registry: contradictions as measured adjunction defects.

This is the successor to BOTH of Babylon's previous contradiction
representations — the saturating edge-``tension`` scalar (which pinned
at 1.0 and carried no information) and the dormant dialectics layer's
``weight`` float. An :class:`OppositionSpec` names the two poles and
their unity; a :class:`GapMeasure` reports, from live inputs, how far
the opposition currently is from closure (``gap`` — Laclau: the measured
failure of an identity to fully constitute itself) and which pole
dominates (``balance``). The registry derives the rate of development
and Mao's **principal contradiction**: the contradiction whose
development leads all others, operationalized as
``score = gap * (1 + rate_weight * |rate|)``.

Contract with the engine (Phase C): registry states map onto the
existing :class:`babylon.models.entities.contradiction.Contradiction`
fields as intensity ← gap, aspect_balance ← rate,
principal_aspect ← leading_pole. Balance is the signed dominance of
pole B over pole A; at exactly zero the leading pole is INERT — it
holds its previous value, because a principal aspect persists until it
is actually overturned.

See Also:
    :class:`babylon.dialectics.core.cylinder.AdjointCylinder`: supplies
    balance readings for interval-shaped oppositions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from babylon.models import Intensity

Balance = Annotated[
    float,
    Field(ge=-1.0, le=1.0, description="Signed dominance of pole B over pole A"),
]

_DEFAULT_RATE_WEIGHT = 10.0
"""Weight of |rate| in principal-contradiction scoring.

Phase C wires this from GameDefines (Constitution III.1); the default
makes a gap developing at 0.1/tick outrank a static gap twice its size.
"""

__all__ = [
    "BoundOpposition",
    "GapMeasure",
    "GapReading",
    "OppositionRegistry",
    "OppositionSpec",
    "OppositionState",
]


class GapReading(BaseModel):
    """One opposition's instantaneous measurement.

    Example:
        >>> GapReading(gap=0.4, balance=-0.2).gap
        0.4
    """

    gap: Intensity = Field(..., description="Distance from closure: 0 resolved, 1 maximal")
    balance: Balance = Field(..., description="Signed dominance of pole B over pole A")

    model_config = ConfigDict(frozen=True, extra="forbid")


class GapMeasure[I](Protocol):
    """Measures an opposition against live inputs of type ``I``."""

    def __call__(self, inputs: I) -> GapReading:
        """Return the current :class:`GapReading` for these inputs."""
        ...


class OppositionSpec(BaseModel):
    """The static identity of an opposition: poles, unity, placement."""

    key: str = Field(..., min_length=1, description="Registry-unique identifier")
    pole_a: str = Field(..., min_length=1, description="One aspect of the opposition")
    pole_b: str = Field(..., min_length=1, description="The other aspect")
    unity: str = Field(
        default="",
        description="What holds the poles together (mutual presupposition)",
    )
    level_name: str = Field(
        default="",
        description="Level-lattice placement (Phase E); empty = unplaced",
    )
    antagonistic: bool = Field(
        default=False,
        description="Laclau: cannot close within its current level",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


@dataclass(frozen=True)
class BoundOpposition[I]:
    """An :class:`OppositionSpec` bound to its :class:`GapMeasure`."""

    spec: OppositionSpec
    measure: GapMeasure[I]


class OppositionState(BaseModel):
    """One opposition's per-tick dynamic state."""

    key: str = Field(..., min_length=1)
    tick: int = Field(..., ge=0)
    gap: Intensity = Field(..., description="Current distance from closure")
    balance: Balance = Field(..., description="Signed dominance of pole B over pole A")
    rate: float = Field(..., description="gap - previous gap (0.0 on first step)")
    leading_pole: Literal["a", "b"] = Field(..., description="The principal aspect")
    is_principal: bool = Field(
        default=False,
        description="Whether this is the principal contradiction this tick",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class OppositionRegistry[I]:
    """Steps a family of oppositions and ranks the principal contradiction.

    Args:
        bindings: The oppositions to track; keys must be unique.
        rate_weight: Weight of |rate| in principal scoring (>= 0).

    Raises:
        ValueError: On duplicate keys or negative ``rate_weight``.
    """

    def __init__(
        self,
        bindings: Sequence[BoundOpposition[I]],
        rate_weight: float = _DEFAULT_RATE_WEIGHT,
    ) -> None:
        if rate_weight < 0.0:
            raise ValueError(f"rate_weight must be non-negative, got {rate_weight}")
        keys = [binding.spec.key for binding in bindings]
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        if duplicates:
            raise ValueError(f"Duplicate opposition keys: {duplicates}")
        self._bindings: tuple[BoundOpposition[I], ...] = tuple(
            sorted(bindings, key=lambda binding: binding.spec.key)
        )
        self._rate_weight = rate_weight

    @property
    def keys(self) -> tuple[str, ...]:
        """Registered opposition keys, lexicographically ordered."""
        return tuple(binding.spec.key for binding in self._bindings)

    def spec_for(self, key: str) -> OppositionSpec:
        """Look up a spec by key.

        Raises:
            KeyError: If the key is not registered.
        """
        for binding in self._bindings:
            if binding.spec.key == key:
                return binding.spec
        raise KeyError(key)

    def step(
        self,
        inputs: I,
        tick: int,
        previous: Mapping[str, OppositionState] | None = None,
    ) -> tuple[OppositionState, ...]:
        """Measure every opposition and mark the principal contradiction.

        Args:
            inputs: Live inputs handed to every bound measure.
            tick: The current tick, stamped onto each state.
            previous: Last tick's states by key, for rate and pole inertia.

        Returns:
            One state per binding, lexicographic by key, with exactly one
            ``is_principal=True`` (none if the registry is empty). Ties
            in score break toward the lexicographically first key.
        """
        drafts: list[OppositionState] = []
        for binding in self._bindings:
            reading = binding.measure(inputs)
            prior = previous.get(binding.spec.key) if previous else None
            rate = reading.gap - prior.gap if prior is not None else 0.0
            drafts.append(
                OppositionState(
                    key=binding.spec.key,
                    tick=tick,
                    gap=reading.gap,
                    balance=reading.balance,
                    rate=rate,
                    leading_pole=self._lead(reading.balance, prior),
                )
            )
        if not drafts:
            return ()
        principal_key = self._principal_key(drafts)
        return tuple(
            draft.model_copy(update={"is_principal": draft.key == principal_key})
            for draft in drafts
        )

    def _score(self, state: OppositionState) -> float:
        """Mao's principal-contradiction ranking: sharp AND fast-developing."""
        return state.gap * (1.0 + self._rate_weight * abs(state.rate))

    def _principal_key(self, drafts: Sequence[OppositionState]) -> str:
        """Highest score wins; ties break to the lexicographically first key."""
        best = drafts[0]
        best_score = self._score(best)
        for candidate in drafts[1:]:
            score = self._score(candidate)
            if score > best_score:
                best, best_score = candidate, score
        return best.key

    @staticmethod
    def _lead(balance: float, prior: OppositionState | None) -> Literal["a", "b"]:
        """Sign of balance selects the pole; zero holds the previous pole."""
        if balance < 0.0:
            return "a"
        if balance > 0.0:
            return "b"
        return prior.leading_pole if prior is not None else "a"
