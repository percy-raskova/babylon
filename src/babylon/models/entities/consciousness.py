"""Ternary consciousness model (Feature 034).

Replaces the stipulated scalar CommunityConsciousness with a 2-simplex model
where ``r + l + f = 1.0``. Old fields become computed properties, preserving
full backward compatibility (SC-005).

Theoretical basis: George Jackson's *Blood in My Eye* — revolutionary
consciousness is qualitatively different from the liberal-fascist spectrum.
The height above the base (r) measures distance from assimilation.

See Also:
    :mod:`babylon.models.entities.community`: CommunityConsciousness alias.
    :mod:`babylon.formulas.consciousness`: Computation function.
    ``specs/034-ternary-consciousness/spec.md``: Feature specification.
"""

from __future__ import annotations

import logging
import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.models.enums import CommunityType, ConsciousnessTendency
from babylon.models.types import Probability

logger = logging.getLogger(__name__)

# Tolerance for simplex constraint validation
_SIMPLEX_TOLERANCE = 1e-4


class ProvenanceLevel(StrEnum):
    """Data quality indicator for substrate floor computation.

    Values:
        HIGH: Derived from 2+ independent proxy data sources.
        MEDIUM: Derived from 1 proxy data source.
        LOW: Estimated from related data, not direct proxy.
        SYNTHETIC: Stipulated placeholder with no data path.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SYNTHETIC = "synthetic"


class TernaryConsciousness(BaseModel):
    """A point in the 2-simplex representing community consciousness.

    Three components (r, l, f) sum to 1.0:
    - r: Revolutionary consciousness (distance from assimilation).
    - l: Liberal consciousness (reform within existing order).
    - f: Fascist consciousness (exclusionary reaction).

    Supports two construction paths:
    1. **Native**: ``TernaryConsciousness(r=0.5, l=0.3, f=0.2)``
    2. **Legacy**: ``TernaryConsciousness(collective_identity=0.5,
       dominant_tendency=LIBERAL, ideological_contestation=0.4)``

    Both produce valid simplex points with backward-compatible properties.

    Args:
        r: Revolutionary component [0, 1].
        l: Liberal component [0, 1].
        f: Fascist component [0, 1].
        contestation_stored: Preserved legacy contestation value, or None
            for natively constructed instances (uses Shannon entropy).
    """

    model_config = ConfigDict(frozen=True)

    r: Probability = Field(default=Probability(0.3), description="Revolutionary component")
    l: Probability = Field(default=Probability(0.6), description="Liberal component")  # noqa: E741
    f: Probability = Field(default=Probability(0.1), description="Fascist component")
    contestation_stored: float | None = Field(
        default=None,
        repr=False,
        description="Stored legacy contestation (None = use Shannon entropy)",
    )

    @model_validator(mode="before")
    @classmethod
    def _handle_construction_paths(cls, data: Any) -> Any:
        """Route between native, legacy, and default construction paths.

        Three paths:
        1. Native (r in data): Strip computed field leftovers, pass through.
        2. Legacy (collective_identity in data, r not): Convert to (r, l, f).
        3. Default (empty dict): Set contestation_stored=0.2.
        """
        if not isinstance(data, dict):
            return data

        has_r = "r" in data
        has_ci = "collective_identity" in data

        if has_r:
            # Native path — strip any computed field leftovers from roundtrip
            for key in (
                "collective_identity",
                "dominant_tendency",
                "ideological_contestation",
                "assimilation_ratio",
            ):
                data.pop(key, None)
            return data

        if has_ci:
            # Legacy path — convert old kwargs to ternary
            ci = float(data.pop("collective_identity"))
            tendency_raw = data.pop("dominant_tendency", ConsciousnessTendency.LIBERAL)
            contestation_raw = data.pop("ideological_contestation", 0.2)

            # Parse tendency if string
            if isinstance(tendency_raw, str):
                tendency = ConsciousnessTendency(tendency_raw)
            else:
                tendency = tendency_raw

            contestation = float(contestation_raw)

            r, l_val, f_val = _derive_ternary_from_legacy(ci, tendency)
            data["r"] = r
            data["l"] = l_val
            data["f"] = f_val
            data["contestation_stored"] = contestation
            return data

        # Default path — empty dict or only contestation_stored
        if not any(k in data for k in ("r", "l", "f", "contestation_stored")):
            data["contestation_stored"] = 0.2

        return data

    @model_validator(mode="after")
    def _enforce_simplex(self) -> TernaryConsciousness:
        """Enforce r + l + f = 1.0 within tolerance."""
        total = self.r + self.l + self.f
        if abs(total - 1.0) > _SIMPLEX_TOLERANCE:
            msg = f"Simplex violation: r + l + f = {total} (expected 1.0)"
            raise ValueError(msg)
        return self

    @property
    def collective_identity(self) -> float:
        """Oppositional consciousness [0, 1]. Equals r component.

        Returns:
            The revolutionary component, semantically identical to the
            old CommunityConsciousness.collective_identity.
        """
        return float(self.r)

    @property
    def dominant_tendency(self) -> ConsciousnessTendency:
        """Prevailing ideological direction (argmax of r, l, f).

        Ties are broken in favor of liberal (structural advantage of the
        status quo — you have to actively organize to leave liberalism).

        Returns:
            ConsciousnessTendency corresponding to the largest component.
        """
        components = {
            ConsciousnessTendency.REVOLUTIONARY: float(self.r),
            ConsciousnessTendency.LIBERAL: float(self.l),
            ConsciousnessTendency.FASCIST: float(self.f),
        }
        max_val = max(components.values())
        # Tie-breaking: prefer liberal, then revolutionary, then fascist
        for tendency in (
            ConsciousnessTendency.LIBERAL,
            ConsciousnessTendency.REVOLUTIONARY,
            ConsciousnessTendency.FASCIST,
        ):
            if abs(components[tendency] - max_val) < 1e-6:
                return tendency
        # Should never reach here, but satisfy type checker
        return ConsciousnessTendency.LIBERAL  # pragma: no cover

    @property
    def ideological_contestation(self) -> float:
        """Active debate between tendencies [0, 1].

        If contestation_stored is set (legacy construction), returns that
        value for backward compatibility. Otherwise computes normalized
        Shannon entropy of (r, l, f): H(r,l,f) / log(3).

        Returns:
            Contestation level. 0 = monopoly, 1 = maximum contestation.
        """
        if self.contestation_stored is not None:
            return self.contestation_stored
        return _shannon_entropy_normalized(float(self.r), float(self.l), float(self.f))

    @property
    def assimilation_ratio(self) -> float:
        """Position along the liberal-fascist base: f / (l + f).

        Measures how much of the non-revolutionary consciousness is fascist.
        When l + f is near zero (fully revolutionary), returns 0.5 (neutral).

        Returns:
            Ratio in [0, 1]. 0 = pure liberal, 1 = pure fascist.
        """
        denominator = float(self.l) + float(self.f)
        if denominator < 1e-6:
            return 0.5
        return float(self.f) / denominator


def _derive_ternary_from_legacy(
    ci: float,
    tendency: ConsciousnessTendency,
) -> tuple[float, float, float]:
    """Convert legacy scalar fields to ternary (r, l, f) coordinates.

    Args:
        ci: Old collective_identity value [0, 1].
        tendency: Old dominant_tendency enum.

    Returns:
        Tuple of (r, l, f) summing to 1.0 where argmax matches tendency.
    """
    r = ci
    remaining = 1.0 - r

    if remaining < 1e-6:
        # Fully revolutionary — no room for l or f
        return (r, 0.0, 0.0)

    if tendency == ConsciousnessTendency.LIBERAL:
        # Liberal dominant: l must be >= r for argmax (tie-breaking favors liberal)
        l_val = remaining * 0.75
        f_val = remaining * 0.25
        # When ci is high (>= ~0.43), the 75/25 split gives l < r.
        # Give all remaining to l so tie-breaking can work at ci=0.5.
        if l_val < r:
            l_val = remaining
            f_val = 0.0
    elif tendency == ConsciousnessTendency.FASCIST:
        # Fascist dominant: f must be >= r for argmax
        f_val = remaining * 0.75
        l_val = remaining * 0.25
        if f_val < r:
            f_val = remaining
            l_val = 0.0
    elif tendency == ConsciousnessTendency.REVOLUTIONARY:
        # Revolutionary dominant: r is already largest (ci was given)
        # Split remaining to not challenge r's dominance
        l_val = remaining * 0.6
        f_val = remaining * 0.4
    else:
        # Fallback — should not happen
        l_val = remaining * 0.75
        f_val = remaining * 0.25

    return (r, l_val, f_val)


def _shannon_entropy_normalized(r: float, l: float, f: float) -> float:  # noqa: E741
    """Compute normalized Shannon entropy of a 3-component distribution.

    H(r, l, f) / log(3), yielding [0, 1] where 0 is pure and 1 is uniform.

    Args:
        r: Revolutionary component.
        l: Liberal component.
        f: Fascist component.

    Returns:
        Normalized entropy in [0, 1].
    """
    entropy = 0.0
    for p in (r, l, f):
        if p > 1e-10:
            entropy -= p * math.log(p)
    return entropy / math.log(3)


class SubstrateFloor(BaseModel):
    """Per-community-type minimum revolutionary consciousness with provenance.

    The substrate floor is consciousness that persists even when all
    organizations are destroyed — the grandmother teaching not to talk
    to cops, survival knowledge transmitted through socialization.

    Args:
        community_type: Which community this floor applies to.
        floor_value: Minimum r regardless of org landscape [0, 1].
        confidence: Data quality indicator.
        data_sources: Named data sources used.
        computation_method: How floor was derived from proxies.
    """

    model_config = ConfigDict(frozen=True)

    community_type: CommunityType
    floor_value: Probability = Field(
        default=Probability(0.0),
        description="Minimum r regardless of org landscape",
    )
    confidence: ProvenanceLevel = Field(
        default=ProvenanceLevel.SYNTHETIC,
        description="Data quality indicator",
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="Named data sources used",
    )
    computation_method: str = Field(
        default="",
        description="How floor was derived from proxies",
    )


class OrgContribution(BaseModel):
    """An organization's weighted contribution to community consciousness.

    Used as input to the compute_ternary_consciousness function.

    Args:
        tendency: Which vertex this org pulls toward.
        membership_density: Members in community / community population [0, 1].
        cadre_level: Organizational development level [0, 1].
        cohesion: Internal organizational cohesion [0, 1].
    """

    model_config = ConfigDict(frozen=True)

    tendency: ConsciousnessTendency
    membership_density: Probability = Field(
        description="Members in community / community population",
    )
    cadre_level: Probability = Field(
        description="Organizational development level",
    )
    cohesion: Probability = Field(
        description="Internal organizational cohesion",
    )


__all__ = [
    "OrgContribution",
    "ProvenanceLevel",
    "SubstrateFloor",
    "TernaryConsciousness",
]
