"""Integration tests for the Tensor Hierarchy pipeline (Feature 025).

Feature: 025-tensor-hierarchy
TDD Phase: GREEN (pipeline is complete)

Tests the end-to-end pipelines:
- T053: BEA XLSX → SQLite → InterIndustryFlow → Leontief inverse
- T054: Gamma module → VisibilityMetric → ShadowSubsidy
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from sqlalchemy.orm import sessionmaker

# =============================================================================
# Path Constants
# =============================================================================

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_BEA_USE_XLSX = (
    _PROJECT_ROOT / "data/input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx"
)
_BEA_LEONTIEF_XLSX = (
    _PROJECT_ROOT / "data/input-output/total-domestic-requirements/IxI_Domestic_Summary.xlsx"
)
# Babylon-data trove root (Spec 059 symlink target). The GDP-by-industry
# XLSX (consumed by BEANationalLoader to populate dim_bea_industry) lives
# in the trove, not the repo's data/.
_BABYLON_DATA_ROOT = Path("/media/user/data/babylon-data")
_GDP_FILE = _BABYLON_DATA_ROOT / "gdp-by-industry" / "GrossOutput.xlsx"


# =============================================================================
# T053: BEA XLSX → SQLite → InterIndustryFlow → Leontief pipeline
# =============================================================================


@pytest.mark.integration
class TestInterIndustryFlowPipeline:
    """End-to-end BEA I-O XLSX → SQLite → tensor → Leontief pipeline.

    The class-scoped ``populated_session_factory`` fixture handles the
    full two-stage ingest once per test class:

      1. ``BEANationalLoader`` populates ``dim_bea_industry`` from the
         GDP-by-industry XLSX in the babylon-data trove, applying the
         concordance bridge so ``bea_code`` matches the IO XLSX's
         column header codes.
      2. ``BEAIOLoader`` populates ``fact_bea_io_coefficients`` from
         the IO Use Summary XLSX in the repo's ``data/``.

    Three skip gates protect non-dev environments (ordered by priority):

      a. ``pytest.importorskip("babylon_data")`` — fires on CI without
         the babylon-data mount.
      b. ``_GDP_FILE.exists()`` — fires if GDP-by-industry XLSX absent.
      c. ``_BEA_USE_XLSX.exists()`` — fires if repo's IO Use XLSX absent.

    See ``ai-docs/decisions/ADR037_test_skip_remediation.yaml`` for the
    history of this test (the two-layer bug it surfaced and the
    namespace-bridge fix).
    """

    @pytest.fixture(scope="class")
    def populated_session_factory(self):  # type: ignore[no-untyped-def]
        """Session factory with both BEA tables populated.

        Runs ``BEANationalLoader`` → ``BEAIOLoader`` once per test class.
        Returns a ``sessionmaker`` bound to an in-memory SQLite engine;
        each test checks out its own session.
        """
        pytest.importorskip("babylon_data", reason="BEA pipeline requires babylon-data package")
        if not _GDP_FILE.exists():
            pytest.skip(
                f"BEA GDP-by-industry XLSX absent; needs babylon-data mount at {_BABYLON_DATA_ROOT}"
            )
        if not _BEA_USE_XLSX.exists():
            pytest.skip("BEA Use XLSX absent from data/input-output/make-use/")

        from babylon_data.bea.io_loader import BEAIOLoader  # type: ignore[import-not-found]
        from babylon_data.bea.loader_national import (  # type: ignore[import-not-found]
            BEANationalLoader,
        )
        from tests.conftest import create_reference_engine

        engine = create_reference_engine()
        factory = sessionmaker(bind=engine)

        nat_loader = BEANationalLoader(data_dir=_BABYLON_DATA_ROOT)
        io_loader = BEAIOLoader(data_dir=_PROJECT_ROOT / "data")
        with factory() as session:
            nat_loader.load(session, reset=True, verbose=False)
            stats = io_loader.load(session, reset=True, verbose=False)
            assert stats.total_facts > 0, (
                f"BEA pipeline produced 0 facts after both loaders ran. errors={stats.errors}"
            )
            session.commit()
        return factory

    def test_bea_loader_ingests_xlsx(self, populated_session_factory) -> None:  # type: ignore[no-untyped-def]
        """BEAIOLoader successfully ingests the IO Use XLSX into the 3NF schema."""
        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultInterIndustryFlowSource,
        )

        source = DefaultInterIndustryFlowSource(populated_session_factory)
        years = source.available_years()
        assert len(years) > 0, "BEAIOLoader populated 0 facts"

    def test_inter_industry_flow_source_returns_tensor(
        self,
        populated_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """DefaultInterIndustryFlowSource reads SQLite and returns InterIndustryFlow."""
        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultInterIndustryFlowSource,
        )
        from babylon.economics.tensor_hierarchy.types import InterIndustryFlow

        source = DefaultInterIndustryFlowSource(populated_session_factory)
        year = min(source.available_years())
        flow = source.get_direct_requirements(year)
        assert isinstance(flow, InterIndustryFlow)
        assert flow.n_industries > 0
        assert flow.coefficients.shape == (flow.n_industries, flow.n_industries)

    def test_leontief_inverse_non_negative(
        self,
        populated_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """Leontief inverse has non-negative elements (Perron-Frobenius)."""
        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultInterIndustryFlowSource,
            DefaultLeontiefComputer,
        )
        from babylon.economics.tensor_hierarchy.types import LeontiefInverse

        source = DefaultInterIndustryFlowSource(populated_session_factory)
        flow = source.get_direct_requirements(min(source.available_years()))
        leontief = DefaultLeontiefComputer().compute_inverse(flow)

        assert isinstance(leontief, LeontiefInverse)
        assert np.all(leontief.inverse_matrix >= -1e-9)
        assert np.all(np.diag(leontief.inverse_matrix) >= 1.0 - 1e-9)

    def test_department_aggregation_produces_4x4_matrix(
        self,
        populated_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """Department aggregation reduces ~70 industries to 4x4 matrix."""
        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultDepartmentAggregator,
            DefaultInterIndustryFlowSource,
        )
        from babylon.economics.tensor_hierarchy.types import InterIndustryFlow

        source = DefaultInterIndustryFlowSource(populated_session_factory)
        flow = source.get_direct_requirements(min(source.available_years()))

        aggregator = DefaultDepartmentAggregator()
        mapping = aggregator.get_default_mapping()
        assert len(mapping) > 0

        dept_flow = aggregator.aggregate(flow, mapping)
        assert isinstance(dept_flow, InterIndustryFlow)
        assert dept_flow.n_industries == 4  # I, IIA, IIB, III

    def test_full_pipeline_end_to_end(
        self,
        populated_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """Full pipeline: SQLite → InterIndustryFlow → Leontief → Departments."""
        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultDepartmentAggregator,
            DefaultInterIndustryFlowSource,
            DefaultLeontiefComputer,
        )
        from babylon.economics.tensor_hierarchy.types import InterIndustryFlow, LeontiefInverse

        source = DefaultInterIndustryFlowSource(populated_session_factory)
        flow = source.get_direct_requirements(min(source.available_years()))

        leontief_computer = DefaultLeontiefComputer()
        leontief = leontief_computer.compute_inverse(flow)
        assert isinstance(leontief, LeontiefInverse)

        aggregator = DefaultDepartmentAggregator()
        dept_flow = aggregator.aggregate(flow, aggregator.get_default_mapping())
        assert isinstance(dept_flow, InterIndustryFlow)
        assert dept_flow.n_industries == 4

        dept_leontief = leontief_computer.compute_inverse(dept_flow)
        assert dept_leontief.n_industries == 4


# =============================================================================
# T054: Gamma module → VisibilityMetric → ShadowSubsidy pipeline
# =============================================================================


@pytest.mark.integration
class TestVisibilityPipeline:
    """Integration test for gamma module → VisibilityMetric → ShadowSubsidy.

    Tests using the DefaultVisibilitySource adapter that wraps the gamma module.
    Some tests require real ATUS/QCEW data; others use mocks.
    """

    def test_visibility_source_returns_sentinel_for_missing_year(self) -> None:
        """DefaultVisibilitySource returns NoDataSentinel when gamma has no data."""
        from unittest.mock import MagicMock

        from babylon.economics.tensor import NoDataSentinel
        from babylon.economics.tensor_hierarchy.visibility import DefaultVisibilitySource

        # Mock gamma calculator that returns NoDataSentinel
        mock_gamma = MagicMock()
        mock_gamma.compute.return_value = NoDataSentinel("national", 1900, "No ATUS data")
        mock_shadow = MagicMock()

        source = DefaultVisibilitySource(
            gamma_calculator=mock_gamma,
            shadow_calculator=mock_shadow,
        )
        result = source.get_visibility(1900)
        assert isinstance(result, NoDataSentinel)

    def test_visibility_source_constructs_visibility_metric(self) -> None:
        """DefaultVisibilitySource constructs VisibilityMetric from gamma output."""
        from unittest.mock import MagicMock

        from babylon.economics.gamma.types import GammaIII
        from babylon.economics.tensor_hierarchy.types import VisibilityMetric
        from babylon.economics.tensor_hierarchy.visibility import DefaultVisibilitySource

        # Mock a valid GammaIIIResult
        mock_result = MagicMock(spec=GammaIII)
        mock_result.gamma_iii = 0.333
        mock_result.year = 2022

        mock_gamma = MagicMock()
        mock_gamma.compute.return_value = mock_result
        mock_shadow = MagicMock()

        source = DefaultVisibilitySource(
            gamma_calculator=mock_gamma,
            shadow_calculator=mock_shadow,
        )
        result = source.get_visibility(2022)
        assert isinstance(result, VisibilityMetric)
        assert result.g_33 == pytest.approx(0.333)
        assert result.g_11 == pytest.approx(0.97)  # QCEW coverage rate for productive depts
        assert result.year == 2022

    def test_shadow_subsidy_computation(self) -> None:
        """ShadowSubsidy computed correctly from visibility via gamma module."""
        from unittest.mock import MagicMock

        from babylon.economics.gamma.types import GammaIII, ShadowSubsidy
        from babylon.economics.tensor_hierarchy.types import ShadowSubsidyTensor
        from babylon.economics.tensor_hierarchy.visibility import DefaultVisibilitySource

        mock_result = MagicMock(spec=GammaIII)
        mock_result.gamma_iii = 0.5
        mock_result.year = 2022

        mock_gamma = MagicMock()
        mock_gamma.compute.return_value = mock_result

        # Shadow calculator returns a ShadowSubsidy object
        mock_shadow_result = MagicMock(spec=ShadowSubsidy)
        mock_shadow_result.phi_iii_labor_hours = 50.0
        mock_shadow_result.phi_iii_dollars = None
        mock_shadow_result.melt_available = False

        mock_shadow = MagicMock()
        mock_shadow.compute_phi_iii.return_value = mock_shadow_result

        source = DefaultVisibilitySource(
            gamma_calculator=mock_gamma,
            shadow_calculator=mock_shadow,
        )
        result = source.get_shadow_subsidy(2022)
        assert isinstance(result, ShadowSubsidyTensor)
        assert result.phi_iii_labor_hours > 0.0
        assert result.year == 2022

    def test_g33_less_than_g11(self) -> None:
        """VisibilityMetric maintains g_33 < g_11 constraint."""
        from unittest.mock import MagicMock

        from babylon.economics.gamma.types import GammaIII
        from babylon.economics.tensor_hierarchy.types import VisibilityMetric
        from babylon.economics.tensor_hierarchy.visibility import DefaultVisibilitySource

        mock_result = MagicMock(spec=GammaIII)
        mock_result.gamma_iii = 0.333
        mock_result.year = 2020

        mock_gamma = MagicMock()
        mock_gamma.compute.return_value = mock_result
        mock_shadow = MagicMock()

        source = DefaultVisibilitySource(
            gamma_calculator=mock_gamma,
            shadow_calculator=mock_shadow,
        )
        result = source.get_visibility(2020)
        assert isinstance(result, VisibilityMetric)
        assert result.g_33 < result.g_11
