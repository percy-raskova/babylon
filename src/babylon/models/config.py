"""Run-scoped configuration for the Babylon engine.

``SimulationConfig`` carries per-run settings that are *not* game-balance
coefficients. Historically it also declared every formula coefficient, but
those fields were dead: the engine reads all tunable coefficients from
:class:`~babylon.config.defines.GameDefines` (via ``services.defines.*``), the
canonical single source of truth. The ~36 shadow coefficient fields were
removed in the ``src/`` simplification sweep (2026-07) — they had zero logic
readers, and their values had drifted out of sync with the live GameDefines
values (e.g. ``comprador_cut`` read 0.15 here vs the live 0.90 in
``GameDefines.economy``), making them an active source of confusion.

Only the deterministic RNG seed remains: the web bridge threads it from the
``GameSession`` and serializes it into the persisted ``config_json`` blob, so
it is a genuine run-scoped setting rather than a coefficient shadow.

See Also:
    :class:`~babylon.config.defines.GameDefines`: canonical coefficient source
        and the moddable single source of truth (``src/babylon/data/defines.yaml``).
"""

from pydantic import BaseModel, ConfigDict, Field


class SimulationConfig(BaseModel):
    """Immutable per-run settings for the simulation engine.

    Game-balance coefficients live in
    :class:`~babylon.config.defines.GameDefines` (read via ``services.defines``);
    this model only carries run-scoped settings that are not part of the
    moddable coefficient surface. The config is frozen to preserve determinism
    during a run.

    Attributes:
        rng_seed: Per-run RNG seed for byte-identical action replays
            (Constitution III.7). Threaded from the ``GameSession`` by the web
            bridge and serialized into the persisted run configuration.
    """

    model_config = ConfigDict(frozen=True)

    # Spec 061 US5 FR-024 (T080): per-tick RNG seed for byte-identical
    # replays. Threaded through from the GameSession's rng_seed by the
    # bridge so that resolving the same actions in the same order with
    # the same seed produces the same outcome.
    rng_seed: int = Field(
        default=0,
        description="RNG seed for deterministic action resolution (Constitution III.7)",
    )
