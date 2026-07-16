"""The declared registry of sanctioned synthetic/fallback data sources.

Babylon's production code paths carry a small, deliberate set of
synthetic/fallback data sources: a mock API bridge for dev/test without
Postgres, hardcoded graceful-degradation defaults for unwired economics
calculators, and hand-authored (not empirically-sourced) scenario fixtures.
Each is legitimate *only* because it is guarded — gated behind ``DEBUG``,
counted by a fallback tally, or self-evidently a deterministic fixture never
mistaken for reference data. An UNGUARDED synthetic value reaching a
production run — rendered as if real, with nothing watching — is exactly the
"ghost data" failure mode Constitution III.11 (Loud Failure) and VIII.12 (no
disarmed guardrail) forbid.

Each row below is one :class:`SyntheticSource`: the symbol that fabricates or
defaults data, the file it lives in, the symbol that *guards* it (a DEBUG
check, a tally counter, an ABC + auto-registry), and the material invariant
the guard enforces. This literal is intentionally hand-written — a dev-time
contract, not player-moddable runtime config — so it carries no regeneration
machinery. The static coherence sensor in
:mod:`babylon.sentinels.synthetic.checks` proves each named source *and* its
guard still exist; the row grows the registry so a renamed/deleted guard reds
the fast-gate instead of silently disarming, and a newly-discovered synthetic
source must be declared here (with a real guard) to pass review — the
registry is meant to stay CLOSED, not merely additive.

The full narrative for each row — why it is sanctioned, what was verified,
what was found NOT to hold — lives in
:doc:`/reference/declared-synthetic-data` (Diataxis reference doc); this
module is the machine-checked source of truth the doc and the sensor both
read.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

#: The four guard mechanisms a sanctioned synthetic source may carry:
#:
#: - ``"debug_gate"`` — refuses to serve outside ``django.conf.settings.DEBUG``.
#: - ``"fallback_instrumentation"`` — every substitution is counted in a tally
#:   the run manifest surfaces (never silent).
#: - ``"documented_default_with_override"`` — a hardcoded default with an
#:   explicit wired-source override path and an in-code III.11 comment, but
#:   (as of this writing, see the reference doc) NOT counted in a tally.
#: - ``"deterministic_seed"`` — a hand-authored fixture, self-documented as
#:   such (class docstring), entered only via explicit ``scenario=`` selection
#:   and never substituted for reference data.
GuardKind = Literal[
    "debug_gate",
    "fallback_instrumentation",
    "documented_default_with_override",
    "deterministic_seed",
]


class SyntheticSource(BaseModel):
    """One declared, sanctioned synthetic/fallback data source.

    Frozen and ``extra="forbid"`` so a malformed row is a loud failure at
    import time (Constitution III.11) rather than a quiet ``None`` at check
    time.

    :ivar name: stable identity for the source (e.g. ``"stub_engine_bridge"``).
    :ivar source_file: repo-relative ``.py`` path defining ``source_symbol``.
    :ivar source_symbol: the symbol that fabricates or defaults data — a bare
        module-level name (``"StubEngineBridge"``) or one level of dotted
        attribute access into a module-level class/function
        (``"TickDynamicsSystem._compute_national_params"``); the static
        sensor proves it still exists.
    :ivar guard_file: repo-relative ``.py`` path defining ``guard_symbol``.
    :ivar guard_symbol: the symbol that enforces the guard (same dotted-name
        rules as ``source_symbol``); the static sensor proves it still exists
        too, so a deleted/renamed guard reds the gate even if the source
        itself is untouched.
    :ivar guard_kind: which of the four guard mechanisms this row uses.
    :ivar what_it_fakes: one-line description of the faked/defaulted value.
    :ivar invariant: the specific guarantee that keeps this source from
        reaching a production run unrecorded — cite the enforcing code/test.
    :ivar notes: free-text clarification, cross-references, or a documented
        gap (e.g. "not counted in the tally, unlike its siblings").
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    source_file: str
    source_symbol: str
    guard_file: str
    guard_symbol: str
    guard_kind: GuardKind
    what_it_fakes: str
    invariant: str
    notes: str = ""

    @model_validator(mode="after")
    def _validate_shape(self) -> SyntheticSource:
        """Reject empty identity/location fields loudly at import (III.11).

        :returns: ``self`` when valid.
        :raises ValueError: if any identity/location field is blank, or if
            ``source_file``/``guard_file`` is not a ``.py`` path.
        """
        if not self.name.strip():
            raise ValueError("SyntheticSource.name must be non-empty")
        if not self.source_symbol.strip():
            raise ValueError(f"{self.name!r}: source_symbol must be non-empty")
        if not self.source_file.endswith(".py"):
            raise ValueError(
                f"{self.name!r}: source_file must be a .py path, got {self.source_file!r}"
            )
        if not self.guard_symbol.strip():
            raise ValueError(f"{self.name!r}: guard_symbol must be non-empty")
        if not self.guard_file.endswith(".py"):
            raise ValueError(
                f"{self.name!r}: guard_file must be a .py path, got {self.guard_file!r}"
            )
        return self


#: The five known, sanctioned synthetic/fallback sources on production code
#: paths (Phase F audit, 2026-07-16). See
#: :doc:`/reference/declared-synthetic-data` for the full narrative.
SYNTHETIC_SOURCES: tuple[SyntheticSource, ...] = (
    SyntheticSource(
        name="stub_engine_bridge",
        source_file="web/game/stub_bridge.py",
        source_symbol="StubEngineBridge",
        guard_file="web/game/api.py",
        guard_symbol="_get_bridge",
        guard_kind="debug_gate",
        what_it_fakes=(
            "The full EngineBridge query/action surface (session, tick, map, doctrine, "
            "organization snapshots) — deterministic, realistic-looking mock data (e.g. the "
            "4-entity Wayne County class roster _make_wayne_county_entities builds) so the "
            "Django app and frontend can run without PostgreSQL or a live engine."
        ),
        invariant=(
            "_get_bridge() raises ImproperlyConfigured — citing 'Seam Sensor 3 provenance / "
            "Constitution III.11' — whenever django.conf.settings.DEBUG is False and no real "
            "bridge was initialized; the stub's fabricated data can never answer a production "
            "(DEBUG=False) request. Enforced dynamically (not by this static sensor) and proved "
            "by tests/unit/web/test_stub_bridge_guard.py."
        ),
        notes=(
            "Bridge parity (same get_* methods/signatures as the real EngineBridge) is a "
            "separate guard: tests/unit/web/test_stub_bridge_parity.py."
        ),
    ),
    SyntheticSource(
        name="economics_employment_default",
        source_file="src/babylon/domain/economics/tick/initializer.py",
        source_symbol="_DEFAULT_EMPLOYMENT",
        guard_file="src/babylon/engine/services.py",
        guard_symbol="ServiceContainer.employment_source",
        guard_kind="documented_default_with_override",
        what_it_fakes=(
            "Per-county employment headcount (100_000.0) used to seed/bootstrap "
            "CountyEconomicState.employment when no real employment_source is wired or the "
            "county/year QCEW row is absent."
        ),
        invariant=(
            "TickDynamicsSystem._compute_county_states prefers "
            "services.employment_source.get_county_total_employment(fips, year) whenever the "
            "source is wired (tick/system/__init__.py:701-704); every call site carries an "
            "inline comment naming the 100k literal as the documented Constitution III.11 "
            "graceful-degradation default. VERIFIED GAP (2026-07-16): unlike the gamma_basket/"
            "gamma_III fallbacks below, this default is NOT one of the counted fields in "
            "EconomicsFallbackTally — it is documented-in-place, not tallied into the run "
            "manifest's economics_fallbacks block."
        ),
        notes=(
            "The same 100_000.0 literal is mirrored at 3 further call sites kept byte-identical "
            "by convention, not shared reference: tick/system/__init__.py:434 "
            "(_bootstrap_county_states), tick/system/__init__.py:700 (_compute_county_states' "
            "own prev-state fallback), and tick/graph_bridge.py:262 (from_graph). Only the "
            "initializer.py constant is a named module-level symbol."
        ),
    ),
    SyntheticSource(
        name="economics_fallback_tally",
        source_file="src/babylon/domain/economics/tick/system/__init__.py",
        source_symbol="TickDynamicsSystem._compute_national_params",
        guard_file="src/babylon/engine/services.py",
        guard_symbol="EconomicsFallbackTally",
        guard_kind="fallback_instrumentation",
        what_it_fakes=(
            "National tick parameters gamma_basket=0.68 and gamma_III=0.33, substituted when "
            "basket_calculator / gamma_calculator is unwired (None) or returns no data. (MELT's "
            "tau has no literal-substitution fallback here: an unavailable MELT result aborts "
            "the whole annual pipeline for the tick via an early return, rather than defaulting.)"
        ),
        invariant=(
            "Every substitution increments a named counter — record_gamma_basket_calculator_"
            "none() / record_gamma_iii_calculator_none() / record_gamma_iii_returned_none() / "
            "record_melt_unavailable() — plus a per-observation wired-vs-None snapshot "
            "(observe_wiring). The headless runner surfaces EconomicsFallbackTally.to_dict() as "
            "the run manifest's economics_fallbacks block (C.8 / spec 2.R), so a fully-unwired "
            "run's defaulted gamma no longer reports as silently as computed data."
        ),
        notes=(
            "A calculator that is None at the TickDynamicsSystem.step() entry point (the "
            "melt_calculator is None guard at tick/system/__init__.py:151) skips the annual "
            "pipeline before _compute_national_params runs at all — that path is a "
            "logger.debug()-only skip, not counted by any EconomicsFallbackTally field."
        ),
    ),
    SyntheticSource(
        name="scenario_two_node",
        source_file="src/babylon/engine/scenarios/two_node.py",
        source_symbol="TwoNodeScenario",
        guard_file="src/babylon/engine/scenarios/base.py",
        guard_symbol="Scenario",
        guard_kind="deterministic_seed",
        what_it_fakes=(
            "A minimal 2-node WorldState (one worker, one owner, one exploitation edge) with "
            "fixed illustrative parameters (worker_wealth=0.5, extraction_efficiency=0.8, ...) "
            "— never read from the reference database."
        ),
        invariant=(
            "Only reachable by explicit scenario='two_node' selection (resolve_scenario(), "
            "web/game/engine_bridge.py) — never a silent substitute for a real county. The "
            "Scenario ABC's __init_subclass__ auto-registry raises ValueError on a name "
            "collision at import time, so two builders can never shadow each other under one "
            "name."
        ),
        notes="Delegates to the legacy free function create_two_node_scenario for byte-equality.",
    ),
    SyntheticSource(
        name="scenario_wayne_county_detroit",
        source_file="src/babylon/engine/scenarios/wayne_county.py",
        source_symbol="WayneCountyScenario",
        guard_file="src/babylon/engine/scenarios/base.py",
        guard_symbol="Scenario",
        guard_kind="deterministic_seed",
        what_it_fakes=(
            "The Wayne County (Detroit) tri-county WorldState: H3 hexes classified by a "
            "hand-authored _classify_wayne_hex bounding-box rule and fixed illustrative "
            "entities/relationships — never read from the reference database."
        ),
        invariant=(
            "Only reachable by explicit scenario selection — 'wayne_county' or the aliases "
            "'wayne'/'detroit' (resolve_scenario(), web/game/engine_bridge.py) — never a silent "
            "substitute for a real county. Same Scenario ABC auto-registry collision guard as "
            "scenario_two_node."
        ),
        notes=(
            "Delegates to the legacy free function create_wayne_county_scenario for "
            "byte-equality. fix/seed-scenario-loud (project/execution/briefs/"
            "fix-seed-scenario-loud.md) made every scenario entry point fail loud on an unknown "
            "name instead of silently reseeding 'us'."
        ),
    ),
)
