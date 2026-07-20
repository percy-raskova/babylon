"""Declared invariants of the ``defines_passthrough`` sentinel.

**The error class** (task #42 fix wave 1, review MEDIUM-1): a production
call site invokes a formulas-layer function that declares an OPTIONAL
``defines`` parameter (``defines: XDefines | None = None``) but omits it.
The function then silently falls back to its own schema-default
coefficients (``defines = defines or XDefines()``), ignoring whatever the
run's ``services.defines``/``defines.yaml`` actually says -- defeating the
repo's whole moddability promise (``defines.yaml`` — "the canonical,
player-editable single source of truth"). Latent on every canonical run
today (``defines.yaml`` IS generated from the schema, so the two are
numerically identical), but real for any modded override.

**Founding specimens.** The #42-A+B review found the ``defines=`` fix landed
for ``compute_agitation_delta`` (``ideology.py``) was a ONE-INSTANCE patch of
this class-wide bug: two SIBLING calls in the SAME per-node loop --
``route_agitation_to_ternary`` and ``compute_exploitation_visibility`` --
still omitted it. This sentinel's own repo-wide survey (``src/babylon`` only,
tests excluded, per the fix brief) found two MORE, unrelated to the
consciousness-routing area entirely: ``engine/systems/sovereignty.py``'s
``calculate_metabolic_impact(policy)`` call (fixed in the same fix wave --
threading ``services.defines.balkanization`` through, mirroring the
ideology.py fix exactly) and ``models/entities/sovereign.py``'s
``Sovereign.metabolic_impact`` computed_field (exempted below -- a Pydantic
``@computed_field`` has only ``self`` in scope; there is no
``services``/run-defines object reachable from a model property at all, and
the property's own docstring already documents its override path is a
custom ``Sovereign`` + custom defines in higher-level code, never this
property).

**Scope (read before extending — mirrors the dangling sentinel's own scope
discipline):** a general "flag every call missing a keyword" checker would
drown in false positives against arbitrary functions. The deliberate scope
is a **registry of watched functions** (:data:`WATCHED_FUNCTIONS`) — only
formulas-layer functions whose ``defines`` parameter is OPTIONAL (has a
default) are watched; a REQUIRED ``defines`` parameter (no default) cannot
be silently omitted at all (Python raises ``TypeError``), so those functions
(``state_ai.py``'s three, ``balkanization.py``'s private
``_eligible_territories``) are correctly out of scope by construction, not
by oversight — :func:`~babylon.sentinels._ast.optional_defines_param_index`
returns ``None`` for them and the checks module never watches a row whose
function does not resolve to the optional shape.

:data:`DEFINES_PASSTHROUGH_EXEMPTIONS` is the same family-wide
:class:`~babylon.sentinels.exemptions.SentinelExemption` every other
sentinel uses (gate-governance ruling, 2026-07-18) — never a bespoke
exemption class.

Layer 0.5: imports nothing above :mod:`babylon.models`.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

from babylon.sentinels.exemptions import SentinelExemption

__all__ = [
    "DEFINES_PASSTHROUGH_EXEMPTIONS",
    "EXCLUDED_DIRS",
    "PRODUCTION_ROOTS",
    "WATCHED_FUNCTIONS",
    "WatchedFunction",
]

#: Trees scanned for a missing defines= passthrough. Test files are EXCLUDED
#: no matter which root they live under (see
#: :func:`babylon.sentinels.defines_passthrough.checks.is_test_source`), per
#: the fix brief's explicit "src/babylon only, tests excluded" scope.
PRODUCTION_ROOTS: Final[tuple[str, ...]] = ("src/babylon",)

#: Repo-relative directory prefixes excluded even though they sit under a
#: scanned root: ``formulas/`` is the DECLARATION site for every
#: :data:`WATCHED_FUNCTIONS` row, not a production CALL site -- scanning it
#: would only ever find each function's own ``def``, never a call (verified:
#: no formula in this codebase today calls a sibling formula from this
#: watched set).
EXCLUDED_DIRS: Final[tuple[str, ...]] = ("src/babylon/formulas",)


class WatchedFunction(BaseModel):
    """One formulas-layer function whose OPTIONAL ``defines`` parameter must be threaded through.

    :ivar name: Stable identity for this row (conventionally ``func_name``).
    :ivar def_file: Repo-relative ``.py`` path declaring ``func_name``.
    :ivar func_name: The bare function name production code calls.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    def_file: str
    func_name: str

    @model_validator(mode="after")
    def _validate_shape(self) -> WatchedFunction:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: If any identity field is blank, or ``def_file``
            is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("WatchedFunction.name must be non-empty")
        if not self.func_name.strip():
            raise ValueError(f"{self.name!r}: func_name must be non-empty")
        if not self.def_file.endswith(".py"):
            raise ValueError(f"{self.name!r}: def_file must be a .py path, got {self.def_file!r}")
        return self


#: The 7 functions across ``consciousness_routing.py``/``balkanization.py``
#: whose ``defines`` parameter is OPTIONAL (``defines: XDefines | None =
#: None``) -- the risky shape this sentinel exists for. Verified (task #42
#: fix wave 1 survey) against the other 4 formulas-layer functions that also
#: declare a ``defines`` parameter (``state_ai.py``'s
#: ``calculate_faction_shift``/``is_fascist_convergence``/
#: ``check_fascist_reversion``, ``balkanization.py``'s private
#: ``_eligible_territories``) -- all four declare it REQUIRED (no default)
#: and are correctly excluded from this registry.
WATCHED_FUNCTIONS: Final[tuple[WatchedFunction, ...]] = (
    WatchedFunction(
        name="compute_agitation_delta",
        def_file="src/babylon/formulas/consciousness_routing.py",
        func_name="compute_agitation_delta",
    ),
    WatchedFunction(
        name="compute_exploitation_visibility",
        def_file="src/babylon/formulas/consciousness_routing.py",
        func_name="compute_exploitation_visibility",
    ),
    WatchedFunction(
        name="route_agitation_to_ternary",
        def_file="src/babylon/formulas/consciousness_routing.py",
        func_name="route_agitation_to_ternary",
    ),
    WatchedFunction(
        name="calculate_metabolic_impact",
        def_file="src/babylon/formulas/balkanization.py",
        func_name="calculate_metabolic_impact",
    ),
    WatchedFunction(
        name="derive_default_multipliers_from_stance",
        def_file="src/babylon/formulas/balkanization.py",
        func_name="derive_default_multipliers_from_stance",
    ),
    WatchedFunction(
        name="detect_red_settler_trap",
        def_file="src/babylon/formulas/balkanization.py",
        func_name="detect_red_settler_trap",
    ),
    WatchedFunction(
        name="contiguous_influence_majority_subregion",
        def_file="src/babylon/formulas/balkanization.py",
        func_name="contiguous_influence_majority_subregion",
    ),
)

#: ``Sovereign.metabolic_impact`` (``models/entities/sovereign.py``) -- the
#: one genuinely ARCHITECTURAL exemption found by this sentinel's repo-wide
#: survey: a Pydantic ``@computed_field`` property has only ``self`` in
#: scope, so there is no ``services``/run-defines object reachable from it
#: at all (unlike every :data:`WATCHED_FUNCTIONS` call site, which lives in
#: an engine System's ``step()`` with ``services`` as a parameter). The
#: property's own docstring already records this as deliberate: "Uses
#: BalkanizationDefines canonical defaults; override path is to construct a
#: custom Sovereign + custom defines in higher-level code, not via this
#: property." Not a fixable omission -- a structural boundary.
DEFINES_PASSTHROUGH_EXEMPTIONS: Final[tuple[SentinelExemption, ...]] = (
    SentinelExemption(
        key=(
            "defines_passthrough",
            "src/babylon/models/entities/sovereign.py",
            "calculate_metabolic_impact",
        ),
        reason=(
            "Sovereign.metabolic_impact is a Pydantic computed_field -- only "
            "`self` is in scope; there is no services/run-defines object "
            "reachable from a model property at all. The property's own "
            "docstring already documents the override path is a custom "
            "Sovereign + custom defines in higher-level code, never this "
            "property. Architectural, not a fixable omission."
        ),
        owner="Persephone Raskova",
        date="2026-07-20",
        tracking_task="N/A (architectural: model layer has no services access)",
    ),
)
