"""The declared source of truth for producer outputs and their readers.

Each row is one **output** a production producer stamps — a graph attribute, a
``GraphInputs`` field, a module constant — together with the production files
that read it. A row with no consumers must carry a ``dormant_reason``: dormancy
is legitimate (scaffolding awaiting its consumer) but only when *declared*, so
that an output nobody reads can never again sit undetected.

Hand-written by contract: this is a dev-time claim about the code, not
player-moddable runtime config, so it carries no regeneration machinery. The
static sensors in :mod:`babylon.sentinels.liveness.checks` prove each claim.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class LivenessRow(BaseModel):
    """One declared producer output and the production files that read it.

    Frozen and ``extra="forbid"`` so a malformed row fails loudly at import
    (Constitution III.11) rather than quietly at check time.

    :ivar name: stable identity for the output (e.g. ``"price_divergence"``).
    :ivar producer_file: repo-relative ``.py`` path that stamps the output.
    :ivar producer_symbol: the producing ``System``/function/class; the
        correct-but-inert sensor groups rows by this name.
    :ivar output_symbol: the name a consumer must mention to be counted as a
        reader — a graph-attribute string, a field name, or a constant name.
    :ivar consumer_files: repo-relative ``.py`` paths that read the output in
        PRODUCTION (tests and sentinels do not count; a test-only reader is
        exactly the false liveness this gate exists to expose).
    :ivar dormant_reason: why this output legitimately has no reader yet;
        required when ``consumer_files`` is empty.
    :ivar material_relation: the material relation the output carries
        (Aleksandrov Test) — why anything downstream should want it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    producer_file: str
    producer_symbol: str
    output_symbol: str
    consumer_files: tuple[str, ...] = ()
    dormant_reason: str = ""
    material_relation: str

    @model_validator(mode="after")
    def _validate_shape(self) -> LivenessRow:
        """Reject blank identities, non-``.py`` paths, and undeclared dormancy.

        :returns: ``self`` when valid.
        :raises ValueError: If ``name``/``output_symbol``/``producer_symbol`` is
            blank, any declared path is not a ``.py`` file, or the row has
            neither a consumer nor a ``dormant_reason``.
        """
        for label, value in (
            ("name", self.name),
            ("producer_symbol", self.producer_symbol),
            ("output_symbol", self.output_symbol),
            ("material_relation", self.material_relation),
        ):
            if not value.strip():
                raise ValueError(f"LivenessRow.{label} must be non-empty")
        if not self.producer_file.endswith(".py"):
            raise ValueError(
                f"{self.name!r}: producer_file must be a .py path, got {self.producer_file!r}"
            )
        for consumer in self.consumer_files:
            if not consumer.endswith(".py"):
                raise ValueError(
                    f"{self.name!r}: consumer_files entries must be .py paths, got {consumer!r}"
                )
        if not self.consumer_files and not self.dormant_reason.strip():
            raise ValueError(
                f"{self.name!r}: an output with no consumer_files must declare a "
                "dormant_reason — undeclared dormancy is the error class this "
                "registry exists to forbid"
            )
        return self


#: Repo-relative roots, factored out for readability.
_ENGINE_SYSTEMS = "src/babylon/engine/systems"
_DIALECTICS = "src/babylon/domain/dialectics/instances"
_TICK = "src/babylon/domain/economics/tick"
_ECON_DIST = "src/babylon/domain/economics/distribution"
_ECON_CREDIT = "src/babylon/domain/economics/credit"

#: The declared producer outputs of the money/value estate.
LIVENESS_ROWS: tuple[LivenessRow, ...] = (
    LivenessRow(
        name="price_divergence",
        producer_file=f"{_ENGINE_SYSTEMS}/market_scissors.py",
        producer_symbol="MarketScissorsSystem",
        output_symbol="price_divergence",
        consumer_files=("web/game/engine_bridge.py", "web/game/map_contract.py"),
        material_relation=(
            "Per-territory divergence of market price from labour value — the "
            "scissors as the player sees it on the map lens."
        ),
    ),
    LivenessRow(
        name="market_balance",
        producer_file=f"{_ENGINE_SYSTEMS}/contradiction.py",
        producer_symbol="ContradictionSystem",
        output_symbol="market_balance",
        consumer_files=(f"{_DIALECTICS}/catalog.py",),
        material_relation=(
            "The pre-derived scissors Balance the price_value opposition measures "
            "as an adjunction defect (ADR077/ADR078)."
        ),
    ),
    LivenessRow(
        name="pole_readings",
        producer_file=f"{_ENGINE_SYSTEMS}/contradiction.py",
        producer_symbol="ContradictionSystem",
        output_symbol="pole_readings",
        consumer_files=(),
        dormant_reason=(
            "Written to the graph every tick and read only by the partition "
            "sentinel's harness (a dev-time probe, not production). Declared "
            "dormant pending the emergent-class-partition Phase 2 consumer "
            "(Program 19 / ADR070); until then it is a live producer with zero "
            "production readers, recorded rather than hidden."
        ),
        material_relation=(
            "Per-entity position on each opposition axis — the raw material of an "
            "emergent class partition."
        ),
    ),
    LivenessRow(
        name="national_financial",
        producer_file=f"{_TICK}/graph_bridge.py",
        producer_symbol="write_national_financial_state_to_graph",
        output_symbol="NATIONAL_FINANCIAL_ATTR",
        consumer_files=(
            f"{_ENGINE_SYSTEMS}/market_scissors.py",
            f"{_ENGINE_SYSTEMS}/contradiction.py",
        ),
        material_relation=(
            "The national ledger of claims on surplus — interest state and "
            "fictitious capital stock — published to the graph so a CONSEQUENCE "
            "phase System reads it in the same tick it is computed (U3)."
        ),
    ),
    LivenessRow(
        name="ground_rent_path_a",
        producer_file=f"{_ECON_DIST}/calculator.py",
        producer_symbol="DefaultDistributionCalculator",
        output_symbol="ground_rent",
        consumer_files=(f"{_TICK}/graph_bridge.py",),
        material_relation=(
            "Real FRED B230RC0Q173SBEA rental income — the landowner's claim on "
            "county surplus. Repointed into tick_ground_rent by U1.5; before that "
            "it computed correctly every year and reached no territory node."
        ),
    ),
    LivenessRow(
        name="fictitious_capital_stock",
        producer_file=f"{_ECON_CREDIT}/fictitious_capital.py",
        producer_symbol="DefaultFictitiousCapitalCalculator",
        output_symbol="fictitious_capital",
        consumer_files=(f"{_ENGINE_SYSTEMS}/market_scissors.py",),
        material_relation=(
            "Government + corporate + household claims on future surplus. Published "
            "by U3 and read by the U6 monetary anchor; before that it died as a "
            "transient local inside _assess_county_financial_crisis after producing "
            "one financialization ratio (float | None since aedce819)."
        ),
    ),
    LivenessRow(
        name="debt_spiral_threshold",
        producer_file=f"{_ECON_DIST}/types.py",
        # Post-U2.3 reality: the module-level ``Final[float]
        # DEBT_SPIRAL_THRESHOLD`` no longer exists. U2.3 deletes it, moves the
        # value into ``GameDefines.capital_vol3.debt_spiral_threshold``, and
        # leaves a defines-backed accessor FUNCTION of the same lowercase name in
        # ``distribution/types.py``. Naming the deleted ALL-CAPS symbol here
        # would be a false claim inside a registry whose entire purpose is
        # accurate claims about the code — and one nothing would red on, because
        # neither liveness check validates ``producer_symbol`` against
        # ``producer_file``. Recorded for the sentinel roadmap: the liveness
        # registry can currently name a producer symbol that does not exist,
        # which is the same class of unverified claim these sensors exist to
        # catch.
        producer_symbol="debt_spiral_threshold",
        output_symbol="debt_spiral_threshold",
        consumer_files=(f"{_ENGINE_SYSTEMS}/contradiction.py",),
        material_relation=(
            "The accumulated-debt-to-annual-surplus ratio at which the spiral is "
            "structurally self-reinforcing — the unity point of the debt_spiral "
            "opposition (wired by U5.10; a dead constant for its whole prior "
            "life, and a defines-backed accessor since U2.3)."
        ),
    ),
    LivenessRow(
        name="serviceability_anchor",
        producer_file="src/babylon/domain/economics/monetary/anchor.py",
        producer_symbol="serviceability_anchor",
        output_symbol="serviceability_anchor",
        consumer_files=(f"{_ENGINE_SYSTEMS}/market_scissors.py",),
        material_relation=(
            "The real interest burden i/s — the share of produced surplus already "
            "claimed before the functioning capitalist sees any — which sets the "
            "ceiling on fictitious_log before the correction snap (design §3.3/§3.5.1)."
        ),
    ),
)
