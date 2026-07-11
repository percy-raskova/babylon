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
    level_index_for,
    social_lattice_from_memberships,
    spatial_lattice_for_counties,
)

__all__ = [
    "LEVEL_INDEX",
    "atomization_index",
    "connectivity_cylinder",
    "level_index_for",
    "pieces",
    "social_lattice_from_memberships",
    "spatial_lattice_for_counties",
]
