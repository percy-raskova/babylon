"""Adjoint-cylinder instances: bindings to Babylon's actual carriers.

Each module here grounds a piece of ``babylon.domain.dialectics.core`` in a
concrete Babylon data structure. Phase B (this package's first instance)
binds :class:`babylon.domain.dialectics.core.cylinder.AdjointCylinder` to the
solidarity subgraph; later phases add the value-form (MELT) and scale
(spatial hierarchy) instances. See ``project/06-lawverian-dialectics.md``
for the full phase plan.
"""

from babylon.domain.dialectics.instances.connectivity import (
    atomization_index,
    connectivity_cylinder,
    pieces,
)
from babylon.domain.dialectics.instances.levels import (
    LEVEL_INDEX,
    SpatialLatticeRungs,
    cz_adjunction,
    level_index_for,
    msa_adjunction,
    social_lattice_from_memberships,
    spatial_lattice_for_counties,
    spatial_lattice_rungs_for_counties,
)

__all__ = [
    "LEVEL_INDEX",
    "SpatialLatticeRungs",
    "atomization_index",
    "connectivity_cylinder",
    "cz_adjunction",
    "level_index_for",
    "msa_adjunction",
    "pieces",
    "social_lattice_from_memberships",
    "spatial_lattice_for_counties",
    "spatial_lattice_rungs_for_counties",
]
