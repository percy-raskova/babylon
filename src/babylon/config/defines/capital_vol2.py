"""Volume II circulation/reproduction-schema coefficients (spec 023-capital-volume-ii).

Thresholds for the reproduction-schema balance checks that feed
:func:`~babylon.domain.economics.circulation.crisis.assess_circulation_crisis` —
extracted to player-editable ``defines.yaml`` per the Paradox Pattern rather
than hardcoded at the Volume II tick call site
(``domain/economics/tick/system/__init__.py::_compute_county_circulation_state``,
U3 wiring, 2026-07-21 vol2-circulation-engine program).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CapitalVolumeIIDefines(BaseModel):
    """Volume II (circulation / reproduction schema) coefficients."""

    model_config = ConfigDict(frozen=True)

    reproduction_tolerance: float = Field(
        default=0.01,
        gt=0.0,
        description=(
            "Maximum absolute I(v+s) - IIc gap (labor-hours) still "
            "considered BALANCED simple reproduction. Passed as the "
            "tolerance argument to check_simple_reproduction() from "
            "_compute_reproduction_state (Volume II tick wiring, U3). "
            "Matches the calculator's own pre-existing tested default "
            "(Feature 023 T047, tests/unit/economics/circulation/"
            "test_reproduction.py)."
        ),
    )
    dept_i_share_required: float = Field(
        default=0.6667,
        gt=0.0,
        lt=1.0,
        description=(
            "Theoretically required Department I (means of production) "
            "share of combined Dept I + Dept II output for balanced "
            "reproduction. Passed to compute_disproportionality() from "
            "_compute_reproduction_state (Volume II tick wiring, U3). "
            "Derived from Marx's own simple-reproduction numerical "
            "illustration (Capital Vol. II, Ch. 20 SS II): "
            "I = 4000c+1000v+1000s = 6000, II = 2000c+500v+500s = 3000, "
            "dept I share = 6000/9000 = 0.6667."
        ),
    )


__all__ = ["CapitalVolumeIIDefines"]
