"""Adjoint-cylinder instances: bindings to Babylon's actual carriers.

Each module here grounds a piece of ``babylon.dialectics.core`` in a
concrete Babylon data structure. Phase B (this package's first instance)
binds :class:`babylon.dialectics.core.cylinder.AdjointCylinder` to the
solidarity subgraph; later phases add the value-form (MELT) and scale
(spatial hierarchy) instances. See ``project/06-lawverian-dialectics.md``
for the full phase plan.
"""

from babylon.dialectics.instances.connectivity import (
    atomization_index,
    connectivity_cylinder,
    pieces,
)

__all__ = [
    "atomization_index",
    "connectivity_cylinder",
    "pieces",
]
