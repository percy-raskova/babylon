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
from sqlalchemy import create_engine
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


# =============================================================================
# T053: BEA XLSX → SQLite → InterIndustryFlow → Leontief pipeline
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(
    not _BEA_USE_XLSX.exists(),
    reason="BEA Use XLSX not present at data/input-output/make-use/",
)
class TestInterIndustryFlowPipeline:
    """End-to-end BEA I-O XLSX → SQLite → tensor → Leontief pipeline.

    Uses an in-memory SQLite database to avoid polluting the real database.
    """

    @pytest.fixture()
    def in_memory_session_factory(self):  # type: ignore[no-untyped-def]
        """Provide an in-memory SQLite session factory with 3NF schema."""
        from babylon.reference.schema import NormalizedBase

        engine = create_engine("sqlite:///:memory:", echo=False)
        NormalizedBase.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        return factory

    def test_bea_loader_ingests_xlsx(self, in_memory_session_factory) -> None:  # type: ignore[no-untyped-def]
        """BEAIOLoader parses XLSX and inserts coefficients into SQLite."""
        pytest.importorskip("babylon_data", reason="BEAIOLoader requires babylon-data package")
        from babylon_data.bea.io_loader import BEAIOLoader  # type: ignore[import-not-found]

        loader = BEAIOLoader(data_dir=_PROJECT_ROOT / "data")
        with in_memory_session_factory() as session:
            stats = loader.load(session, reset=True, verbose=False)

        assert stats.total_facts > 0
        assert stats.files_processed > 0
        assert not stats.has_errors

    def test_inter_industry_flow_source_returns_tensor(
        self,
        in_memory_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """DefaultInterIndustryFlowSource reads SQLite and returns InterIndustryFlow."""
        pytest.importorskip("babylon_data", reason="BEAIOLoader requires babylon-data package")
        from babylon_data.bea.io_loader import BEAIOLoader  # type: ignore[import-not-found]

        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultInterIndustryFlowSource,
        )
        from babylon.economics.tensor_hierarchy.types import InterIndustryFlow

        loader = BEAIOLoader(data_dir=_PROJECT_ROOT / "data")
        with in_memory_session_factory() as session:
            loader.load(session, reset=True, verbose=False)

        source = DefaultInterIndustryFlowSource(in_memory_session_factory)
        available = source.available_years()
        assert len(available) > 0

        year = min(available)
        flow = source.get_direct_requirements(year)
        assert isinstance(flow, InterIndustryFlow)
        assert flow.n_industries > 0
        assert flow.coefficients.shape == (flow.n_industries, flow.n_industries)

    def test_leontief_inverse_non_negative(
        self,
        in_memory_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """Leontief inverse has non-negative elements (Perron-Frobenius)."""
        pytest.importorskip("babylon_data", reason="BEAIOLoader requires babylon-data package")
        from babylon_data.bea.io_loader import BEAIOLoader  # type: ignore[import-not-found]

        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultInterIndustryFlowSource,
            DefaultLeontiefComputer,
        )
        from babylon.economics.tensor_hierarchy.types import InterIndustryFlow, LeontiefInverse

        loader = BEAIOLoader(data_dir=_PROJECT_ROOT / "data")
        with in_memory_session_factory() as session:
            loader.load(session, reset=True, verbose=False)

        source = DefaultInterIndustryFlowSource(in_memory_session_factory)
        year = min(source.available_years())
        flow = source.get_direct_requirements(year)

        assert isinstance(flow, InterIndustryFlow)
        computer = DefaultLeontiefComputer()
        leontief = computer.compute_inverse(flow)

        assert isinstance(leontief, LeontiefInverse)
        # All elements should be >= 0 (allow small negative from floating point)
        assert np.all(leontief.inverse_matrix >= -1e-9)
        # Diagonal elements >= 1.0
        diag = np.diag(leontief.inverse_matrix)
        assert np.all(diag >= 1.0 - 1e-9)

    def test_department_aggregation_produces_4x4_matrix(
        self,
        in_memory_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """Department aggregation reduces ~70 industries to 4x4 matrix."""
        pytest.importorskip("babylon_data", reason="BEAIOLoader requires babylon-data package")
        from babylon_data.bea.io_loader import BEAIOLoader  # type: ignore[import-not-found]

        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultDepartmentAggregator,
            DefaultInterIndustryFlowSource,
        )
        from babylon.economics.tensor_hierarchy.types import InterIndustryFlow

        loader = BEAIOLoader(data_dir=_PROJECT_ROOT / "data")
        with in_memory_session_factory() as session:
            loader.load(session, reset=True, verbose=False)

        source = DefaultInterIndustryFlowSource(in_memory_session_factory)
        year = min(source.available_years())
        flow = source.get_direct_requirements(year)
        assert isinstance(flow, InterIndustryFlow)

        aggregator = DefaultDepartmentAggregator()
        mapping = aggregator.get_default_mapping()
        assert len(mapping) > 0

        dept_flow = aggregator.aggregate(flow, mapping)
        assert isinstance(dept_flow, InterIndustryFlow)
        assert dept_flow.n_industries == 4  # I, IIA, IIB, III

    def test_full_pipeline_end_to_end(
        self,
        in_memory_session_factory,  # type: ignore[no-untyped-def]
    ) -> None:
        """Full pipeline: XLSX → SQLite → InterIndustryFlow → Leontief → Departments."""
        pytest.importorskip("babylon_data", reason="BEAIOLoader requires babylon-data package")
        from babylon_data.bea.io_loader import BEAIOLoader  # type: ignore[import-not-found]

        from babylon.economics.tensor_hierarchy.inter_industry import (
            DefaultDepartmentAggregator,
            DefaultInterIndustryFlowSource,
            DefaultLeontiefComputer,
        )
        from babylon.economics.tensor_hierarchy.types import InterIndustryFlow, LeontiefInverse

        loader = BEAIOLoader(data_dir=_PROJECT_ROOT / "data")
        with in_memory_session_factory() as session:
            stats = loader.load(session, reset=True, verbose=False)
        assert stats.total_facts > 0

        source = DefaultInterIndustryFlowSource(in_memory_session_factory)
        year = min(source.available_years())
        flow = source.get_direct_requirements(year)
        assert isinstance(flow, InterIndustryFlow)

        # Compute Leontief
        leontief_computer = DefaultLeontiefComputer()
        leontief = leontief_computer.compute_inverse(flow)
        assert isinstance(leontief, LeontiefInverse)

        # Aggregate to departments
        aggregator = DefaultDepartmentAggregator()
        mapping = aggregator.get_default_mapping()
        dept_flow = aggregator.aggregate(flow, mapping)
        assert isinstance(dept_flow, InterIndustryFlow)
        assert dept_flow.n_industries == 4

        # Compute department-level Leontief
        dept_leontief = leontief_computer.compute_inverse(dept_flow)
        assert isinstance(dept_leontief, LeontiefInverse)
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
