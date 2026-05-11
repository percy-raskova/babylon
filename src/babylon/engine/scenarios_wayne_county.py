"""Backward-compat shim — Spec 059 US4 / ADR-006.1.

The original ``engine/scenarios_wayne_county.py`` module was migrated into the
``engine.scenarios`` package as :class:`~babylon.engine.scenarios.wayne_county.WayneCountyScenario`.
This shim re-exports ``create_wayne_county_scenario`` so existing imports
(``from babylon.engine.scenarios_wayne_county import create_wayne_county_scenario``)
continue to resolve unchanged (FR-003 / contracts/import-equivalence.md C5).

New code SHOULD import from :mod:`babylon.engine.scenarios` directly.
"""

from __future__ import annotations

from babylon.engine.scenarios import create_wayne_county_scenario

__all__ = ["create_wayne_county_scenario"]
