"""Launcher for the organization-dossier ``ArchiveApp`` snapshot test.

Mirrors ``tests/unit/tui/snapshot_app.py``'s fresh-instance discipline
exactly: ``pytest-textual-snapshot``'s ``snap_compare`` fixture executes this
file via ``runpy.run_path`` per snapshot run, and a module-level singleton
that some *other* in-process test already ran would render with stale
mounted state (an order-dependent snapshot flake) — so a FRESH ``ArchiveApp``
is always constructed here, never re-exported from ``babylon.tui.app``.

Fixture-fed, not engine-driven (Program 24 P2 WO-18, fixture-first
discipline): the :class:`~babylon.projection.view_models.OrganizationView`
below is hand-built (the same RWP shape used across
``tests/unit/projection/test_organization.py``), rendered through the real
:func:`~babylon.projection.vault.render_organization.render_organization`
pipeline into a BAKED page — the fence body already carries its
``key: value`` rows, so ``BabylonFence`` takes the baked path
(``tui/directives.py``'s ``_directive_statblock``), exactly as a real vault
page would.
"""

from __future__ import annotations

from babylon.projection.vault.render_organization import render_organization
from babylon.projection.view_models import OrganizationView
from babylon.tui.app import ArchiveApp

_ORG_VIEW = OrganizationView(
    org_id="org_rwp",
    verified_tick=847,
    name="Revolutionary Workers Party",
    org_type="political_faction",
    class_character="proletarian",
    legal_standing="registered",
    budget=5_000.0,
    territory_ids=("territory_detroit",),
    headquarters_id="territory_detroit",
    is_institution=False,
    heat=0.3,
    consciousness_tendency="revolutionary",
    cohesion=0.6,
    cadre_level=0.7,
)
"""A fully-populated RWP-shaped dossier — no absence blocks in this golden."""

_PAGE = render_organization(_ORG_VIEW, verified_tick=847)

app = ArchiveApp(page=_PAGE)

__all__ = ["app"]

if __name__ == "__main__":
    app.run()
