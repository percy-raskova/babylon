"""The declared assumptions ledger — load-bearing placeholders made visible.

Babylon's economics layer carries a small set of intentional, documented
simplifications that stand in for data or modeling work the project has not
yet done: a flat employment headcount when no real source is wired, a
national-average FRED series applied uniformly where county-level data would
be more honest, a linear proxy formula standing in for a dataset that does not
exist yet. Each one is *legitimate* only because it is disclosed — Constitution
III.11 (Loud Failure) forbids a placeholder masquerading as measured reality.

Where :mod:`babylon.sentinels.synthetic` answers "which fakes are
code-guarded" and :mod:`babylon.sentinels.coverage` answers "which reference
tables does a calculator depend on", this ledger answers a third, simpler
question a player or reviewer actually asks: **"what is this simulation run
assuming, in plain language, right now?"** ``babylon doctor`` prints it
(:func:`ledger_lines`) so the answer is a command away, not tribal knowledge
scattered across recon docs and code comments.

Each row below is one :class:`Assumption`: a stable id, the material claim it
stands in for, who owns revisiting it, the file where it actually lives in
code, and the condition (never a calendar date — see
:mod:`babylon.sentinels.exemptions`'s ``stale_exemptions`` for why a hard
expiry date is the wrong shape) that would resolve it. This literal is
intentionally hand-written — a dev-time contract, not player-moddable runtime
config. The static coherence check in :mod:`babylon.sentinels.assumptions.checks`
proves each row's ``code_ref`` still exists, so a row cannot silently outlive
the code it describes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class Assumption(BaseModel):
    """One declared, load-bearing assumption baked into a live code path.

    Frozen and ``extra="forbid"`` so a malformed row is a loud failure at
    import time (Constitution III.11) rather than a quiet gap at doctor-print
    time.

    :ivar id: stable identity for the assumption (e.g.
        ``"economics_employment_default"``); referenced from tests and printed
        by ``babylon doctor``.
    :ivar claim: the material simplification this assumption stands in for —
        what a player/reviewer should understand is NOT real measured data.
    :ivar owner: who is responsible for revisiting/resolving this assumption
        (this is a Benevolent-Dictator project; every declared assumption is a
        recorded, revisitable BD-owned decision, not an anonymous shrug).
    :ivar code_ref: repo-relative ``.py`` path where the assumption actually
        lives in code; the static sensor in
        :mod:`babylon.sentinels.assumptions.checks` proves this path still
        exists. Deliberately file-grain, not symbol-grain — the ``claim`` text
        names the specific class/function so the row stays useful to a human
        reader even though only file existence is machine-checked.
    :ivar expiry_condition: what would resolve/retire this assumption — a
        CONDITION to satisfy, never a calendar date. A hard-coded expiry date
        would be exactly the "breaks CI on an arbitrary date" failure mode
        :mod:`babylon.sentinels.exemptions` already warns against; this field
        is documentation a human re-reads, not something anything gates on.
    :ivar notes: free-text clarification, cross-references, or provenance
        (e.g. the recon doc that first flagged the gap).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    claim: str
    owner: str
    code_ref: str
    expiry_condition: str
    notes: str = ""

    @model_validator(mode="after")
    def _validate_shape(self) -> Assumption:
        """Reject a malformed row loudly at import (Constitution III.11).

        :returns: ``self`` when valid.
        :raises ValueError: if ``id``, ``claim``, ``owner``, ``code_ref`` or
            ``expiry_condition`` is blank, or if ``code_ref`` is not a ``.py``
            path.
        """
        for field_name in ("id", "claim", "owner", "code_ref", "expiry_condition"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"Assumption.{field_name} must be non-empty")
        if not self.code_ref.endswith(".py"):
            raise ValueError(f"{self.id!r}: code_ref must be a .py path, got {self.code_ref!r}")
        return self


#: The declared assumptions ledger (T1.2 keel, unit K5, 2026-07-21). Each row
#: was verified against the code it cites at the time it was written — see
#: each row's ``notes`` for provenance. Seeded from genuinely-documented gaps
#: found in code/recon docs, not invented: the employment default already had
#: a sibling :class:`~babylon.sentinels.synthetic.registry.SyntheticSource`
#: row; the Vol I FRED-proxy gaps are named verbatim in
#: ``ai/_inbox/vol1-value-production-program-prompt.md``.
DECLARED_ASSUMPTIONS: tuple[Assumption, ...] = (
    Assumption(
        id="economics_employment_default",
        claim=(
            "Per-county employment defaults to a flat 100,000 headcount "
            "(_DEFAULT_EMPLOYMENT) whenever no real employment_source is wired or the "
            "county/year QCEW row is absent — every tick's wage/profit/exploitation-rate "
            "denominators are computed against this placeholder, not real BLS/QCEW counts, "
            "in that configuration."
        ),
        owner="Persephone Raskova",
        code_ref="src/babylon/domain/economics/tick/initializer.py",
        expiry_condition=(
            "Resolved when every economics tick entry point (headless runner AND web "
            "bridge) always injects a real employment_source so the 100_000.0 literal is "
            "unreachable in a production run — or, short of that, when the substitution is "
            "added to EconomicsFallbackTally so a defaulted run is at least counted (today "
            "it is documented in-place but NOT tallied)."
        ),
        notes=(
            "Mirrors the sibling SyntheticSource row 'economics_employment_default' "
            "(sentinels/synthetic/registry.py) — same literal; that row's lens is 'what "
            "code guards it', this row's lens is 'what should a player/reviewer know'."
        ),
    ),
    Assumption(
        id="lodes_commuter_flow_absent_degrades_to_residence_only",
        claim=(
            "When no LODESCommuterFlowSource is wired, or a county/year has no LODES row, "
            "DefaultThroughputCalculator.compute_commuter_adjusted_metrics silently reports "
            "has_commuter_data=False and net_commuter_balance=0 — every such county is "
            "treated as a closed labor market (no cross-county commuting), understating true "
            "throughput wherever commuting is significant."
        ),
        owner="Persephone Raskova",
        code_ref="src/babylon/domain/economics/throughput/calculator.py",
        expiry_condition=(
            "Resolved when LODES coverage reaches every in-scope county/year so "
            "has_commuter_data is never False for a county the running scenario claims to "
            "model — see the 'lodes_commuter_flow' DataRequirement row "
            "(sentinels/coverage/registry.py) for the underlying data-availability tracking."
        ),
        notes=(
            "The origin-destination adapter itself (SQLiteLODESCommuterFlowSource, "
            "throughput/adapters_lodes.py) is real and wired; the gap is missing/absent "
            "LODES rows for specific county-years, not a stubbed adapter."
        ),
    ),
    Assumption(
        id="dispossession_unrate_proxy_2021_plus",
        claim=(
            "_FredDispossessionAdapter uses real hardcoded historical foreclosure/"
            "bankruptcy/eviction rates only through 2020; every year from 2021 onward "
            "derives all three rates from a single national FRED UNRATE reading via "
            "hand-picked linear proxies (foreclosure≈UNRATE×0.08, bankruptcy≈UNRATE×0.07, "
            "eviction≈UNRATE×0.60+0.015), not observed dispossession data."
        ),
        owner="Persephone Raskova",
        code_ref="src/babylon/domain/economics/factory.py",
        expiry_condition=(
            "Resolved when a real per-year (ideally per-county) foreclosure/bankruptcy/"
            "eviction dataset for 2021 onward replaces the UNRATE-derived proxy formulas in "
            "_FredDispossessionAdapter."
        ),
        notes=(
            "Named 'the honesty gap' verbatim in "
            "ai/_inbox/vol1-value-production-program-prompt.md (§2c / §4)."
        ),
    ),
    Assumption(
        id="vol1_national_series_applied_uniformly_per_county",
        claim=(
            "create_vol1_services (Vol I's county-tick data-source factory, wired only by "
            "the legacy web engine_bridge, not the canonical headless runner) builds three "
            "FRED adapters — _FredReserveArmyAdapter, _FredProductivityAdapter, "
            "_FredDispossessionAdapter — that each read one NATIONAL-level FRED series "
            "(UNRATE/NROU/OPHNFB/HOANBS) and apply the identical value to every county; no "
            "county-level economic variation is modeled for reserve-army decomposition, "
            "productivity, or dispossession along this path."
        ),
        owner="Persephone Raskova",
        code_ref="src/babylon/domain/economics/factory.py",
        expiry_condition=(
            "Resolved when create_vol1_services's adapters read county-grain (not merely "
            "national) series, or this path is superseded by the Vol I county-tick "
            "pipeline's canonical runner-parity unit."
        ),
        notes=(
            "Recon-flagged verbatim as 'National-level series applied to every county — not "
            "county-grain' (ai/_inbox/vol1-value-production-program-prompt.md:71-72)."
        ),
    ),
)


def ledger_lines(registry: tuple[Assumption, ...] = DECLARED_ASSUMPTIONS) -> list[str]:
    """Render one human-readable line per declared assumption.

    Pure formatting — no filesystem access beyond the already-imported literal
    tuple, so it is testable without a CLI runner (mirrors
    :func:`babylon.render.doctor.run_render_probe`'s "kept out of the Typer
    command" precedent). ``babylon doctor`` prints these lines verbatim.

    :param registry: The rows to render (defaults to the real
        :data:`DECLARED_ASSUMPTIONS`).
    :returns: One line per row, in registry order:
        ``"<id>: <claim> [<code_ref>]"``.
    """
    return [f"{row.id}: {row.claim} [{row.code_ref}]" for row in registry]
