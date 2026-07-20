"""SubstrateSystem: county-grain raw-material stock dynamics (#39 T6).

Rewrite of the MVP pass-through stub (Spec 062 US7): the old ``step()``
iterated ``NodeType.HEX`` nodes, but no production code path ever stamps a
``hex`` node onto the engine graph (confirmed dead code --
``sentinels/vocabulary/registry.py``'s ``UNSTAMPED_QUERY_ALLOWLIST`` "hex"
entry), so it was a no-op every tick. This system now runs real depletion
dynamics on county-grain ``Territory`` nodes and is the FIRST engine
consumer of :class:`~babylon.domain.dialectics.instances.scale.ScaleAdjunction`.

**Scope: raw_material_stock ONLY.** No ``energy_stock`` or
``biocapacity_stock`` dynamics exist here -- no reference-data source backs
either (USGS Mineral Commodity Summaries excludes fuels by design, and no
biocapacity/land-use table exists in the reference DB; both remain the
documented placeholders on ``TerritoryDefines.initial_energy_per_hex`` /
``initial_biocapacity_per_hex``, awaiting a future data-acquisition spec).

**Seeding is NOT this system's job.** ``Territory.raw_material_stock`` AND
``Territory.raw_material_capacity`` (the regeneration ceiling, #39 T6 M1)
are seeded once, at USScenario build time, from the SAME committed
``us_county_territories.json`` artifact value, ``raw_material_value_millions``
(``tools/generate_us_county_territories.py``, state
``fact_state_minerals.value_millions`` allocated to counties by
``dim_county_geometry.area_sq_km`` share -- Program 22 Wave 1). No System
anywhere does a per-tick reference-DB read; this one doesn't either --
``step()`` does ONLY per-tick math on the already-present graph attributes.
A territory with ``raw_material_stock is None`` (unseeded: no
``fact_state_minerals`` row for its state, no geometry row, or an abstract
non-county territory) is skipped forever -- never a fabricated default.

**Does NOT touch ``Territory.biocapacity``/``MetabolismSystem``.** Those are
the ALREADY-LIVE metabolic-rift loop (``engine/systems/metabolism.py``,
@13.0) -- a distinct ecological-limits index, not this dollar-denominated
mineral-value stock. ``raw_material_stock`` dynamics are a genuinely
PARALLEL application of the same ``ΔB = R - E·η`` formula
(:func:`~babylon.formulas.metabolic_rift.calculate_biocapacity_delta`), with
its OWN :class:`~babylon.config.defines.substrate.SubstrateDefines`
coefficients -- this module never imports or mutates ``metabolism.py``.

**One-tick lag (intended, by pipeline position):** this system reads each
territory's ``extraction_intensity`` as it stands at the START of this
tick -- i.e. whatever :class:`~babylon.engine.systems.production.
ProductionSystem` (@3.0) wrote during the PREVIOUS tick, since Substrate
(@2.5) always runs before Production within a single tick.

**Lattice binding:** on the first tick with ≥1 eligible territory (never,
for the 5 canonical qa:regression scenarios -- none of them carry
``county_fips``, so this system no-ops there BY CONSTRUCTION, not a
defensive guard), the system calls
:func:`~babylon.domain.dialectics.instances.levels.spatial_lattice_rungs_for_counties`
(T3) over the eligible county set and caches the returned
:class:`~babylon.domain.dialectics.instances.levels.SpatialLatticeRungs` for
the life of the instance (built once, not per tick). **This assumes a FIXED
county universe for the lifetime of a scenario run** (true for USScenario,
built once at scenario-build time) -- a county that became eligible only
mid-run would silently never enter the cached rungs' aggregates, since the
cache is never invalidated or rebuilt (#39 T6 LOW-3). Every tick thereafter
this system publishes EXTENSIVE (summed, never ``aggregate_intensive`` -- a
stock is summed, not averaged) aggregates of the post-depletion
``raw_material_stock`` into ``context.persistent_data``, mirroring
:class:`~babylon.engine.systems.sovereignty.SovereigntySystem`'s mechanism:

- ``"substrate.cz"``, ``"substrate.msa"``, ``"substrate.state"``,
  ``"substrate.nation"`` -- ``dict[str, float]`` parent id -> summed stock.
- ``"substrate.cz_excluded"`` -- the sorted list of eligible counties with
  no commuting-zone mapping (D-T6-5's honesty companion; see below).

**The CZ rung is deliberately scoped, not shared with state/nation** (#39
T6 M1). T3's ``spatial_lattice_rungs_for_counties`` builds ``state``/
``nation`` TOTAL over every eligible county, while ``cz`` is restricted to
the counties :func:`~babylon.domain.dialectics.instances.levels.cz_adjunction`
actually covers -- the 19 post-1990 AK/CT geography changes it cannot
resolve (its own docstring names them) are EXCLUDED from ``cz`` and
returned on ``SpatialLatticeRungs.cz_excluded``, derived by testing
membership in the real crosswalk (never a hardcoded 19-county list). This
System logs that exclusion once at lattice-build time (D-T6-5: "scope,
don't catch"). The MSA rung is partial by design (uncovered counties
silently absent, no exclusion needed).

**``cz_adjunction``/``msa_adjunction`` are constructor-injectable** (default:
the real functions), forwarded straight through to
``spatial_lattice_rungs_for_counties`` so this System never duplicates T3's
cz/msa construction logic. ``msa_adjunction()`` opens a reference-DB session
(``levels.py``) -- this is the one place SubstrateSystem's lattice build
touches the DB, ONCE per instance lifetime (not per tick, not per county;
never at all for the 5 canonical scenarios). Unit tests inject a synthetic
adjunction-returning callable so the aggregation logic is exercised without
a DB dependency, keeping them in the fast tier.

**The regeneration ceiling is a persisted graph field, not System memory**
(#39 T6 LOW-1). ``Territory.raw_material_capacity`` is stamped once, at
scenario-build time, from the SAME artifact value as ``raw_material_stock``
(``tools/generate_us_county_territories.py`` /
``engine/scenarios/_legacy.py``), and is never mutated by this System (only
``raw_material_stock`` depletes/regenerates). Reading the ceiling straight
off the graph every tick -- rather than caching "the first stock value this
instance ever observed" in a System-local dict -- makes the ceiling
replay-safe: it survives a mid-game checkpoint restore (``to_graph``/
``from_graph``) unchanged, so a modded ``regeneration_rate > 0`` regenerates
toward the SAME ceiling whether the run replays from tick 0 or resumes from
a checkpoint. The former in-memory-cache design was honest but NOT
replay-safe under modding -- a restore mid-run would have re-captured the
ceiling from the already-depleted stock, diverging from a continuous run.

See Also:
    ``docs/superpowers/plans/2026-07-19-hex-scale-county-keying.md`` (#39 T6).
    :mod:`babylon.domain.dialectics.instances.scale`: ``ScaleAdjunction``.
    :mod:`babylon.formulas.metabolic_rift`: the shared formula family.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar, Final

from babylon.domain.dialectics.instances.levels import (
    SpatialLatticeRungs,
    cz_adjunction,
    msa_adjunction,
    spatial_lattice_rungs_for_counties,
)
from babylon.domain.dialectics.instances.scale import ScaleAdjunction
from babylon.domain.economics.tick.graph_bridge import resolve_county_identity
from babylon.formulas.metabolic_rift import calculate_biocapacity_delta
from babylon.kernel.system_base import SystemBase
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import NodeType

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType
    from babylon.models.graph import GraphNode

logger = logging.getLogger(__name__)

#: ``context.persistent_data`` keys this system publishes (SovereigntySystem's
#: dotted-namespace convention). Public for downstream consumers (#39 T7).
SUBSTRATE_CZ_KEY: Final[str] = "substrate.cz"
SUBSTRATE_MSA_KEY: Final[str] = "substrate.msa"
SUBSTRATE_STATE_KEY: Final[str] = "substrate.state"
SUBSTRATE_NATION_KEY: Final[str] = "substrate.nation"
SUBSTRATE_CZ_EXCLUDED_KEY: Final[str] = "substrate.cz_excluded"


class SubstrateSystem(SystemBase):
    """Pipeline slot 2.5: raw-material stock depletion + scale-lattice binding.

    Reads: each eligible ``Territory`` node's ``raw_material_stock``
    (pre-tick), ``raw_material_capacity`` (the regeneration ceiling, seeded
    once at scenario-build time -- #39 T6 M1), and ``extraction_intensity``
    (last tick's ProductionSystem output).

    Writes: the post-depletion ``raw_material_stock`` back onto each
    eligible node, clamped to ``[0, raw_material_capacity]``; four extensive
    aggregates into ``context.persistent_data`` (see module docstring).
    """

    partition: ClassVar[TickPartition] = TickPartition.MATERIAL_BASE
    position: ClassVar[float] = 2.5

    name: ClassVar[str] = "substrate"

    def __init__(
        self,
        *,
        cz_adjunction_fn: Callable[[], ScaleAdjunction] = cz_adjunction,
        msa_adjunction_fn: Callable[[], ScaleAdjunction] = msa_adjunction,
    ) -> None:
        """Construct with injectable lattice-source callables.

        Args:
            cz_adjunction_fn: Returns the full county -> CZ adjunction
                (default: the real, reference-DB-free
                :func:`~babylon.domain.dialectics.instances.levels.cz_adjunction`,
                which reads a committed CSV).
            msa_adjunction_fn: Returns the full county -> MSA adjunction
                (default: the real
                :func:`~babylon.domain.dialectics.instances.levels.msa_adjunction`,
                which opens a reference-DB session). Tests inject a
                synthetic callable to avoid the DB dependency.
        """
        self._cz_adjunction_fn = cz_adjunction_fn
        self._msa_adjunction_fn = msa_adjunction_fn
        #: Cached SpatialLatticeRungs (T3), built once on the first eligible
        #: tick and never rebuilt -- see the module docstring's "Lattice
        #: binding" section for the fixed-county-universe assumption this
        #: relies on.
        self._rungs: SpatialLatticeRungs | None = None

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Deplete each eligible territory's raw_material_stock, then publish
        scale-lattice aggregates.

        No-ops (writes nothing, publishes nothing) when zero territories are
        eligible -- the case for all 5 canonical qa:regression scenarios
        (they carry no ``county_fips``) and for any scenario whose
        territories are all unseeded (``raw_material_stock is None``).
        """
        protocol = self._wrap_graph(graph)

        eligible: list[GraphNode] = sorted(
            (
                node
                for node in protocol.query_nodes(node_type=NodeType.TERRITORY)
                if resolve_county_identity(node) is not None
                and node.attributes.get("raw_material_stock") is not None
            ),
            key=lambda node: node.id,
        )
        if not eligible:
            return

        defines = services.defines.substrate
        stock_by_county: dict[str, float] = {}
        for node in eligible:
            county_fips = resolve_county_identity(node)
            if county_fips is None:  # pragma: no cover -- filtered above
                continue
            current_stock = float(self._read(node, "raw_material_stock", required=True))
            ceiling = self._read_ceiling(node)
            extraction_intensity = float(node.attributes.get("extraction_intensity", 0.0))
            delta = calculate_biocapacity_delta(
                regeneration_rate=defines.regeneration_rate,
                max_biocapacity=ceiling,
                extraction_intensity=extraction_intensity * defines.depletion_scale,
                current_biocapacity=current_stock,
                entropy_factor=defines.entropy_factor,
            )
            new_stock = self._write_clamped(
                protocol,
                node.id,
                "raw_material_stock",
                current_stock + delta,
                lo=0.0,
                hi=ceiling,
            )
            stock_by_county[county_fips] = new_stock

        rungs = self._rungs
        if rungs is None:
            rungs = self._build_rungs(sorted(stock_by_county))
            self._rungs = rungs

        persistent = context.persistent_data
        persistent[SUBSTRATE_CZ_KEY] = rungs.cz.aggregate(stock_by_county)
        persistent[SUBSTRATE_MSA_KEY] = rungs.msa.aggregate(stock_by_county)
        persistent[SUBSTRATE_STATE_KEY] = rungs.state.aggregate(stock_by_county)
        persistent[SUBSTRATE_NATION_KEY] = rungs.nation.aggregate(stock_by_county)
        persistent[SUBSTRATE_CZ_EXCLUDED_KEY] = list(rungs.cz_excluded)

        with contextlib.suppress(AttributeError):
            context.persistent_data = persistent

    @staticmethod
    def _read_ceiling(node: GraphNode) -> float:
        """Read the persisted regeneration ceiling (#39 T6 M1 / LOW-1).

        ``raw_material_capacity`` is stamped once, at scenario-build time,
        alongside ``raw_material_stock`` (the SAME artifact value -- see the
        module docstring) and never mutated by this System, so reading it
        fresh every tick is replay-safe: it survives a mid-game checkpoint
        restore unchanged, unlike a System-local "first observed stock"
        cache would.

        Raises:
            KeyError: If the node has no ``raw_material_capacity`` attribute
                at all -- it must be stamped at the same site as
                ``raw_material_stock``, so its total absence is a seeding
                bug, not an honest data gap.
            ValueError: If the attribute is present but ``None`` -- the same
                seeding-bug shape (stock and capacity are stamped together;
                one present and the other ``None`` cannot be an honest
                artifact gap, since a gap zeroes BOTH to ``None``).
        """
        capacity = SubstrateSystem._read(node, "raw_material_capacity", required=True)
        if capacity is None:
            raise ValueError(
                f"Territory {node.id!r} carries raw_material_stock but its "
                "raw_material_capacity (the regeneration ceiling) is None -- "
                "both fields are stamped together, from the same artifact "
                "value, at scenario build time (#39 T6 M1); this indicates "
                "a seeding bug, not an honest data gap."
            )
        return float(capacity)

    def _build_rungs(self, all_counties: list[str]) -> SpatialLatticeRungs:
        """Build the four scale-lattice rungs (called once, not per tick).

        Delegates to :func:`~babylon.domain.dialectics.instances.levels.
        spatial_lattice_rungs_for_counties` (T3), forwarding this System's
        injected ``cz``/``msa`` adjunction sources so the fast-tier unit
        tests never touch the reference DB (#39 T6 M1 -- this System no
        longer duplicates T3's cz/msa/state/nation construction).

        Args:
            all_counties: Sorted, deduplicated county FIPS present among
                this tick's eligible territories -- the T6-scoped county
                universe (never the nationwide universe; a smaller test
                scenario gets a smaller, internally-consistent lattice).
                **Assumed fixed for the life of this System instance** (#39
                T6 LOW-3) -- see the module docstring's "Lattice binding"
                section.

        Returns:
            The T3 rungs bundle (``chain``, ``cz``, ``msa``, ``state``,
            ``nation``, ``cz_excluded``), for the caller to cache.
        """
        rungs = spatial_lattice_rungs_for_counties(
            all_counties,
            cz_adjunction_fn=self._cz_adjunction_fn,
            msa_adjunction_fn=self._msa_adjunction_fn,
        )
        if rungs.cz_excluded:
            logger.warning(
                "SubstrateSystem: %d eligible counties excluded from the CZ "
                "substrate aggregate (no commuting-zone mapping): %s",
                len(rungs.cz_excluded),
                rungs.cz_excluded,
            )
        return rungs


__all__ = [
    "SUBSTRATE_CZ_EXCLUDED_KEY",
    "SUBSTRATE_CZ_KEY",
    "SUBSTRATE_MSA_KEY",
    "SUBSTRATE_NATION_KEY",
    "SUBSTRATE_STATE_KEY",
    "SubstrateSystem",
]
