"""The P1 exit criterion — county end-to-end (Program 24, The Archive).

The charter's exit: *one entity kind (county) end-to-end — tick →
projection → baked page → rendered → snapshot golden*. Pinned here as a
chain with an equality joint in the middle:

1. ``tick → projection ≡ committed fixture`` — the live 5-tick
   ``single_county`` run's projection must equal
   ``tests/fixtures/projection/county_26163.json`` byte-for-byte in model
   terms (drift between engine and fixture fails loudly here, which is what
   keeps the fixture honest).
2. ``fixture → baked page`` — the vault materializer bakes the committed
   fixture into the stable-slug page with its statblock and absence blocks.
3. ``baked page → rendered → snapshot golden`` — the SVG snapshot over the
   ArchiveApp rendering that baked page (``e2e_snapshot_app.py``).

In-process engine, no Postgres, no live DB — the persist/commit seam's
mechanics are separately pinned by
``tests/unit/engine/headless_runner/test_tick_commit_observer.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TOOLS_DIR = _REPO_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from record_projection_fixtures import (  # type: ignore[import-not-found]  # noqa: E402
    COUNTY_FIPS,
    DEFAULT_OUTPUT,
    harvest_county_view,
)

from babylon.projection.fixtures.recorder import load_county_fixture  # noqa: E402
from babylon.projection.vault.materializer import VaultMaterializer  # noqa: E402

pytestmark = [pytest.mark.integration]


class TestCountyEndToEnd:
    """The keel's exit chain, joint by joint."""

    def test_live_projection_equals_committed_fixture(self) -> None:
        """tick → projection ≡ the committed fixture (the honesty joint).

        A drift here means the engine's county outputs moved without the
        fixture being re-harvested (``mise run archive:record-fixtures``)
        — exactly the staleness this test exists to catch.
        """
        live = harvest_county_view()
        committed = load_county_fixture(DEFAULT_OUTPUT)

        assert live == committed

    def test_fixture_bakes_to_stable_slug_page(self, tmp_path: Path) -> None:
        """fixture → baked page: stable slug, statblock body, honest absences."""
        view = load_county_fixture(DEFAULT_OUTPUT)
        page_path = VaultMaterializer(tmp_path / "vault").bake_county(view, tick=view.verified_tick)

        assert page_path == tmp_path / "vault" / "county" / f"{COUNTY_FIPS}.md"
        content = page_path.read_text(encoding="utf-8")
        assert f"id: county/{COUNTY_FIPS}" in content
        assert "```{statblock} county/" + COUNTY_FIPS in content
        assert "population:" in content
        # This scenario seeds no CLAIMS edge — the sovereign renders as a
        # loud absence block, never a fabricated claimant.
        assert view.sovereign_id is None
        assert "```{absence} sovereign_id" in content

    def test_baked_page_renders_to_snapshot_golden(self, snap_compare: Any) -> None:
        """baked page → rendered → SVG snapshot golden (the exit's last joint)."""
        assert snap_compare("./e2e_snapshot_app.py")
