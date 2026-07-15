"""Regression test for the DBImportShareSource / InterIndustryFlowSource
industry-order alignment bug (Program 17 / Item 1a).

``DBImportShareSource.get_import_shares`` (production_chain_rent.py) used to
``GROUP BY``/``ORDER BY`` its result by ``target.bea_code`` alone, while
``DefaultInterIndustryFlowSource.get_industry_codes``/``get_direct_requirements``
(inter_industry.py) order by ``(target.line_number, target.bea_code)``.
Verified empirically against the real reference SQLite
(``data/sqlite/marxist-data-3NF.sqlite``) that these two orderings are NOT
the same permutation. Wiring both sources into the same Leontief pipeline
as-is raises ``ValueError`` inside ``ProductionChainDecomposer.decompose``
the first time real (non-mock) data flows through, because
``flow.industries != shares.industries`` (see
``babylon.domain.economics.tick.system.imperial_rent``).

This test hits the real reference DB directly (no synthetic fixture can
reproduce the ordering divergence — it depends on the actual row order in
``dim_bea_industry``), so it is marked ``requires_reference_db``.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tensor_hierarchy.inter_industry import (
    DefaultInterIndustryFlowSource,
)
from babylon.domain.economics.tensor_hierarchy.production_chain_rent import (
    DBImportShareSource,
)
from babylon.reference.database import get_normalized_session_factory

pytestmark = [pytest.mark.unit, pytest.mark.requires_reference_db]

_TEST_YEAR = 2015


@pytest.mark.unit
def test_import_share_source_industry_order_matches_flow_source() -> None:
    """DBImportShareSource's industry order must match the canonical
    (line_number, bea_code) order used by DefaultInterIndustryFlowSource —
    ProductionChainDecomposer.decompose requires the two vectors to align
    perfectly (production_chain_rent.py:108-110)."""
    session_factory = get_normalized_session_factory()

    flow_source = DefaultInterIndustryFlowSource(session_factory)
    import_share_source = DBImportShareSource(session_factory)

    canonical_order = flow_source.get_industry_codes()
    shares = import_share_source.get_import_shares(_TEST_YEAR)

    assert shares.industries == canonical_order
