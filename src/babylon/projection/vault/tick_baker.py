"""The county tick-baker — the vault's tick-commit adapter.

Satisfies the engine's ``TickCommitObserver`` seam *structurally* (duck
typing): the engine's tick loop calls ``on_tick_committed`` on whatever it
was handed, so this module composes :func:`babylon.projection.county.
project_county` with :class:`~babylon.projection.vault.materializer.
VaultMaterializer` without importing the engine — the projection layer's
import contract stays intact, and the composition root (an integration
test today, the client boot later) is the only place both sides meet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from babylon.projection.county import project_county

if TYPE_CHECKING:
    from babylon.projection.vault.materializer import VaultMaterializer

__all__ = ["CountyTickBaker"]


class CountyTickBaker:
    """Bake a fixed set of county dossiers at every committed tick.

    :param materializer: The vault materializer to bake through.
    :param county_fips: The county FIPS codes to project and bake each
        tick, processed in sorted order for deterministic vault history.
    """

    def __init__(self, materializer: VaultMaterializer, county_fips: tuple[str, ...]) -> None:
        self._materializer = materializer
        self._county_fips = tuple(sorted(county_fips))

    def on_tick_committed(self, *, tick: int, world: Any, graph: Any) -> None:
        """Project and bake every configured county for a committed tick.

        Read-only over ``world``/``graph`` per the observer contract; all
        writes go to the vault repository.

        :param tick: The committed tick number.
        :param world: The post-tick world state.
        :param graph: The post-tick engine graph.
        """
        for fips in self._county_fips:
            view = project_county(fips, graph=graph, world=world, tick=tick)
            self._materializer.bake_county(view, tick=tick)
