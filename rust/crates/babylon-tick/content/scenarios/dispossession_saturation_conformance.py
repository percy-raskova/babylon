"""Conformance vectors for `dispossession/territory-transfer`'s clamps, from
the frozen engine — the ADVERSARIAL-REVIEW follow-up scenario (F1/F3 of the
2026-08-11 review round on PR #498).

This script is the PROVENANCE of every number pinned in
``rust/crates/babylon-tick/tests/dispossession_saturation_conformance.rs``.

Every coefficient this scenario needs to push past its declared domain —
``transfer_scale`` past ``1.0``, ``deadweight_loss_fraction`` past ``1.0``,
the five intensity weights past a sum of ``1.0`` — is a
``DispossessionDefines`` field the real engine's own configuration surface
(``GameDefines``/``ServiceContainer``) constructs as a Pydantic-validated
object, and Pydantic refuses out-of-domain values AT CONSTRUCTION, not just
at YAML-parse time (confirmed directly: ``DispossessionDefines(transfer_
scale=12.0)`` raises ``ValidationError`` immediately). The individual
weights ARE reachable at their legal per-field maximum (``1.0`` each,
summing to ``5.0`` — no cross-field validator forbids that), but
``transfer_scale``/``deadweight_loss_fraction`` need
``DispossessionDefines.model_construct(...)`` — a real Pydantic v2 API that
builds an instance WITHOUT running field validation — followed by
``object.__setattr__`` onto the (frozen) ``GameDefines`` object, so the
REAL ``DispossessionEventSystem.step()`` runs unmodified. This is exactly
the gap this scenario exists to close: BSL's ``:const`` mechanism provides
the SAME bypass (a bare, unsuffixed ``defconst`` literal carries no domain
check at all — ``bsl-language.rst``'s ``E-LEX-024`` only bounds SCALED/
suffixed literals), so what this script reaches via ``model_construct`` is
what a BSL content author reaches by omitting a literal's suffix.

Run it from the repository root, single process::

    PYTHONPATH="$PWD/src" uv run python \\
        rust/crates/babylon-tick/content/scenarios/dispossession_saturation_conformance.py
"""

from __future__ import annotations

from babylon.config.defines import DispossessionDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.dispossession_events import DispossessionEventSystem
from babylon.models.enums import NodeType
from babylon.topology.graph import BabylonGraph

#: Every weight at its legal per-field maximum (`Field(ge=0.0, le=1.0)`,
#: individually valid; no cross-field validator caps the SUM). Raw sum:
#: 5 * 1.0 = 5.0. `deadweight_loss_fraction`/`transfer_scale` are past their
#: own individual domain and need the `model_construct` bypass (see header).
BYPASS_DEFINES = DispossessionDefines.model_construct(
    weight_foreclosure=1.0,
    weight_eviction=1.0,
    weight_displacement=1.0,
    weight_tax_sale=1.0,
    weight_eminent_domain=1.0,
    deadweight_loss_fraction=3.0,
    transfer_scale=12.0,
)


def main() -> None:
    """Run one tick of the frozen DispossessionEventSystem, defines bypassed."""
    services = ServiceContainer.create()
    try:
        object.__setattr__(services.defines, "dispossession", BYPASS_DEFINES)

        graph = BabylonGraph()
        graph.add_node(
            "maxed-county",
            NodeType.TERRITORY,
            foreclosure_rate=1.0,
            eviction_rate=1.0,
            displacement_rate=1.0,
            concentrated_ownership=1.0,
            absentee_landlord_share=1.0,
            wealth=1_000_000.0,
        )
        DispossessionEventSystem().step(graph, services, TickContext(tick=1))
        events = services.event_bus.get_history()

        node = graph.get_node("maxed-county")
        if node is None:
            raise SystemExit("maxed-county vanished during the tick")
        a = node.attributes
        print("post-tick state:")
        print(
            f"  maxed-county       wealth={a['wealth']!r} "
            f"dispossession_intensity={a.get('dispossession_intensity')!r}"
        )
        print()

        print("events:")
        for event in events:
            print(f"  {event.type} {event.payload!r}")
        if not events:
            print("  (none)")
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
