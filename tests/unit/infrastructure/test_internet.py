"""Tests for internet access and consciousness field operations (Feature 036, T039-T041).

Tests verify:
- Internet access initialization from broadband data (FR-024)
- Consciousness field diffusion on connected component (FR-025)
- Surveillance intelligence generation (FR-027)
- OPSEC tradeoff (FR-028)
- Response modes: PERMIT/THROTTLE/SEVER (FR-029)
"""

from __future__ import annotations

import pytest

from babylon.config.defines import InfrastructureDefines, InfraTerrainDefines
from babylon.infrastructure.internet import (
    DefaultInternetAccessManager,
    DefaultInternetFieldOperator,
)
from babylon.infrastructure.types import InternetAccessState
from babylon.models.enums import InternetResponseMode


@pytest.mark.unit
class TestDefaultInternetAccessManagerInit:
    """Tests for internet access initialization (FR-024)."""

    def test_initialize_from_broadband(self) -> None:
        """County broadband penetration maps to hex internet_access."""
        defines = InfraTerrainDefines()
        manager = DefaultInternetAccessManager(defines=defines)

        # Mock broadband data: county FIPS → penetration fraction
        broadband = {"26163": 0.85}  # Wayne County: 85% penetration
        hex_to_county = {"hex_a": "26163", "hex_b": "26163", "hex_c": "26163"}

        manager.initialize_from_broadband(broadband, hex_to_county)

        state_a = manager.get_state("hex_a")
        assert state_a is not None
        assert state_a.internet_access is True

    def test_below_threshold_no_access(self) -> None:
        """Hex with penetration below threshold has no internet access."""
        defines = InfraTerrainDefines(internet_access_threshold=0.8)
        manager = DefaultInternetAccessManager(defines=defines)

        broadband = {"26163": 0.5}  # 50% < 80% threshold
        hex_to_county = {"hex_a": "26163"}

        manager.initialize_from_broadband(broadband, hex_to_county)

        state = manager.get_state("hex_a")
        assert state is not None
        assert state.internet_access is False

    def test_internet_quality_from_broadband(self) -> None:
        """Internet quality derived from high-speed broadband fraction."""
        defines = InfraTerrainDefines()
        manager = DefaultInternetAccessManager(defines=defines)

        broadband = {"26163": 0.9}
        # pct_100_20 data: 60% have 100/20 Mbps
        quality_data = {"26163": 0.6}
        hex_to_county = {"hex_a": "26163"}

        manager.initialize_from_broadband(
            broadband,
            hex_to_county,
            quality_data=quality_data,
        )

        state = manager.get_state("hex_a")
        assert state is not None
        assert state.internet_quality == pytest.approx(0.6)

    def test_default_surveillance_coupling(self) -> None:
        """Surveillance coupling set from InfraTerrainDefines default."""
        defines = InfraTerrainDefines(default_surveillance_coupling=0.4)
        manager = DefaultInternetAccessManager(defines=defines)

        broadband = {"26163": 0.9}
        hex_to_county = {"hex_a": "26163"}

        manager.initialize_from_broadband(broadband, hex_to_county)

        state = manager.get_state("hex_a")
        assert state is not None
        assert state.surveillance_coupling == pytest.approx(0.4)

    def test_water_hex_no_access(self) -> None:
        """WATER hexes default to internet_access=False (EC-009)."""
        defines = InfraTerrainDefines()
        manager = DefaultInternetAccessManager(defines=defines)

        broadband = {"26163": 0.9}
        hex_to_county = {"hex_a": "26163"}
        water_hexes = {"hex_a"}

        manager.initialize_from_broadband(
            broadband,
            hex_to_county,
            water_hexes=water_hexes,
        )

        state = manager.get_state("hex_a")
        assert state is not None
        assert state.internet_access is False

    def test_missing_county_no_access(self) -> None:
        """Hex whose county has no broadband data defaults to no access."""
        defines = InfraTerrainDefines()
        manager = DefaultInternetAccessManager(defines=defines)

        broadband = {}  # No data
        hex_to_county = {"hex_a": "99999"}

        manager.initialize_from_broadband(broadband, hex_to_county)

        state = manager.get_state("hex_a")
        assert state is not None
        assert state.internet_access is False


@pytest.mark.unit
class TestDefaultInternetAccessManagerOpsec:
    """Tests for OPSEC tradeoff (FR-028)."""

    def test_apply_opsec_reduces_coupling(self) -> None:
        """OPSEC investment reduces surveillance coupling."""
        defines = InfraTerrainDefines()
        infra_defines = InfrastructureDefines(opsec_tradeoff_ratio=0.5)
        manager = DefaultInternetAccessManager(defines=defines)

        # Set up a hex with internet access
        manager.set_state(
            InternetAccessState(
                h3_index="hex_a",
                internet_access=True,
                internet_quality=0.8,
                surveillance_coupling=0.6,
            ),
        )

        result = manager.apply_opsec(
            "hex_a",
            org_id="org_1",
            opsec_investment=0.4,
            infra_defines=infra_defines,
        )

        # coupling_after = 0.6 - (0.4 * 0.5) = 0.4
        assert result.coupling_after == pytest.approx(0.4)
        assert result.coupling_before == pytest.approx(0.6)

    def test_opsec_reduces_throughput(self) -> None:
        """OPSEC investment also reduces consciousness throughput."""
        defines = InfraTerrainDefines()
        infra_defines = InfrastructureDefines(opsec_tradeoff_ratio=0.5)
        manager = DefaultInternetAccessManager(defines=defines)

        manager.set_state(
            InternetAccessState(
                h3_index="hex_a",
                internet_access=True,
                internet_quality=0.8,
                surveillance_coupling=0.6,
            ),
        )

        result = manager.apply_opsec(
            "hex_a",
            org_id="org_1",
            opsec_investment=0.4,
            infra_defines=infra_defines,
        )

        assert result.throughput_reduction > 0.0

    def test_opsec_clamps_coupling_to_zero(self) -> None:
        """Coupling cannot go below zero."""
        defines = InfraTerrainDefines()
        infra_defines = InfrastructureDefines(opsec_tradeoff_ratio=1.0)
        manager = DefaultInternetAccessManager(defines=defines)

        manager.set_state(
            InternetAccessState(
                h3_index="hex_a",
                internet_access=True,
                surveillance_coupling=0.1,
            ),
        )

        result = manager.apply_opsec(
            "hex_a",
            org_id="org_1",
            opsec_investment=0.5,
            infra_defines=infra_defines,
        )

        assert result.coupling_after == pytest.approx(0.0)


@pytest.mark.unit
class TestDefaultInternetAccessManagerResponse:
    """Tests for response mode transitions (FR-029)."""

    def test_sever_response(self) -> None:
        """SEVER: zero throughput, zero surveillance, visible, nonzero backfire."""
        defines = InfraTerrainDefines()
        infra_defines = InfrastructureDefines()
        manager = DefaultInternetAccessManager(defines=defines)

        manager.set_state(
            InternetAccessState(
                h3_index="hex_a",
                internet_access=True,
                surveillance_coupling=0.5,
                response_mode=InternetResponseMode.PERMIT,
            ),
        )

        result = manager.set_response_mode(
            "hex_a",
            InternetResponseMode.SEVER,
            infra_defines=infra_defines,
        )

        assert result.new_mode == InternetResponseMode.SEVER
        assert result.throughput_effect == pytest.approx(0.0)
        assert result.surveillance_effect == pytest.approx(0.0)
        assert result.visibility is True
        assert result.backfire_magnitude > 0.0

    def test_throttle_response(self) -> None:
        """THROTTLE: reduced throughput, maintained surveillance, not visible."""
        defines = InfraTerrainDefines()
        infra_defines = InfrastructureDefines(throttle_throughput_fraction=0.3)
        manager = DefaultInternetAccessManager(defines=defines)

        manager.set_state(
            InternetAccessState(
                h3_index="hex_a",
                internet_access=True,
                surveillance_coupling=0.5,
                response_mode=InternetResponseMode.PERMIT,
            ),
        )

        result = manager.set_response_mode(
            "hex_a",
            InternetResponseMode.THROTTLE,
            infra_defines=infra_defines,
        )

        assert result.new_mode == InternetResponseMode.THROTTLE
        assert result.throughput_effect == pytest.approx(0.3)
        assert result.surveillance_effect == pytest.approx(1.0)
        assert result.visibility is False

    def test_permit_response(self) -> None:
        """PERMIT: full throughput, full surveillance."""
        defines = InfraTerrainDefines()
        infra_defines = InfrastructureDefines()
        manager = DefaultInternetAccessManager(defines=defines)

        manager.set_state(
            InternetAccessState(
                h3_index="hex_a",
                internet_access=True,
                surveillance_coupling=0.5,
                response_mode=InternetResponseMode.SEVER,
            ),
        )

        result = manager.set_response_mode(
            "hex_a",
            InternetResponseMode.PERMIT,
            infra_defines=infra_defines,
        )

        assert result.new_mode == InternetResponseMode.PERMIT
        assert result.throughput_effect == pytest.approx(1.0)
        assert result.surveillance_effect == pytest.approx(1.0)
        assert result.visibility is False


@pytest.mark.unit
class TestDefaultInternetFieldOperator:
    """Tests for consciousness field diffusion and surveillance (FR-025, FR-027)."""

    def _make_manager_with_hexes(
        self,
        hex_configs: dict[str, dict[str, object]],
    ) -> DefaultInternetAccessManager:
        """Create a manager pre-loaded with hex states."""
        defines = InfraTerrainDefines(default_surveillance_coupling=0.3)
        manager = DefaultInternetAccessManager(defines=defines)
        for h3_index, config in hex_configs.items():
            manager.set_state(
                InternetAccessState(
                    h3_index=h3_index,
                    internet_access=bool(config.get("internet_access", True)),
                    internet_quality=float(config.get("internet_quality", 0.8)),
                    surveillance_coupling=float(
                        config.get("surveillance_coupling", 0.3),
                    ),
                    response_mode=str(
                        config.get("response_mode", InternetResponseMode.PERMIT),
                    ),
                ),
            )
        return manager

    def test_connected_component_excludes_sever(self) -> None:
        """SEVER hexes are excluded from connected component."""
        manager = self._make_manager_with_hexes(
            {
                "hex_a": {"response_mode": InternetResponseMode.PERMIT},
                "hex_b": {"response_mode": InternetResponseMode.SEVER},
                "hex_c": {"response_mode": InternetResponseMode.PERMIT},
            },
        )
        operator = DefaultInternetFieldOperator(manager)

        component = operator.get_connected_component()
        assert "hex_a" in component
        assert "hex_b" not in component
        assert "hex_c" in component

    def test_connected_component_excludes_no_access(self) -> None:
        """Hexes without internet_access are excluded."""
        manager = self._make_manager_with_hexes(
            {
                "hex_a": {"internet_access": True},
                "hex_b": {"internet_access": False},
            },
        )
        operator = DefaultInternetFieldOperator(manager)

        component = operator.get_connected_component()
        assert "hex_a" in component
        assert "hex_b" not in component

    def test_propagate_consciousness_mean_field(self) -> None:
        """Consciousness diffuses via mean-field on connected component."""
        manager = self._make_manager_with_hexes(
            {
                "hex_a": {},
                "hex_b": {},
                "hex_c": {},
            },
        )
        operator = DefaultInternetFieldOperator(manager)

        field_values = {"hex_a": 1.0, "hex_b": 0.0, "hex_c": 0.0}
        diffusion_rate = 0.5

        result = operator.propagate_consciousness(field_values, diffusion_rate)

        # Mean of connected component = 1/3
        # Each hex moves toward mean by diffusion_rate
        # hex_a: 1.0 + 0.5 * (1/3 - 1.0) = 1.0 - 1/3 = 0.667
        # hex_b: 0.0 + 0.5 * (1/3 - 0.0) = 1/6 ≈ 0.167
        assert result["hex_a"] < 1.0
        assert result["hex_b"] > 0.0
        assert result["hex_c"] > 0.0

    def test_throttle_reduces_diffusion(self) -> None:
        """THROTTLE hexes have reduced diffusion rate."""
        manager = self._make_manager_with_hexes(
            {
                "hex_a": {"response_mode": InternetResponseMode.PERMIT},
                "hex_b": {"response_mode": InternetResponseMode.THROTTLE},
            },
        )
        operator = DefaultInternetFieldOperator(
            manager,
            infra_defines=InfrastructureDefines(throttle_throughput_fraction=0.3),
        )

        field_values = {"hex_a": 1.0, "hex_b": 0.0}
        result = operator.propagate_consciousness(field_values, diffusion_rate=1.0)

        # hex_b is throttled, so it receives less diffusion
        # With full rate, hex_b would get more
        # Throttled hex_b should still change but less than hex_a
        assert result["hex_b"] > 0.0  # Still receives some
        assert result["hex_b"] < result["hex_a"]  # Less than permit hex

    def test_generate_surveillance(self) -> None:
        """Surveillance generates intelligence = flow * coupling * capacity."""
        manager = self._make_manager_with_hexes(
            {
                "hex_a": {"surveillance_coupling": 0.5},
                "hex_b": {"surveillance_coupling": 0.8},
            },
        )
        operator = DefaultInternetFieldOperator(manager)

        flow_magnitudes = {"hex_a": 2.0, "hex_b": 3.0}
        analytical_capacity = 0.6

        results = operator.generate_surveillance(
            flow_magnitudes,
            analytical_capacity,
        )

        assert len(results) == 2

        # hex_a: 2.0 * 0.5 * 0.6 = 0.6
        result_a = next(r for r in results if r.h3_index == "hex_a")
        assert result_a.intelligence_generated == pytest.approx(0.6)

        # hex_b: 3.0 * 0.8 * 0.6 = 1.44
        result_b = next(r for r in results if r.h3_index == "hex_b")
        assert result_b.intelligence_generated == pytest.approx(1.44)

    def test_surveillance_zero_coupling(self) -> None:
        """Zero coupling generates zero intelligence."""
        manager = self._make_manager_with_hexes(
            {
                "hex_a": {"surveillance_coupling": 0.0},
            },
        )
        operator = DefaultInternetFieldOperator(manager)

        flow_magnitudes = {"hex_a": 5.0}
        results = operator.generate_surveillance(flow_magnitudes, 1.0)

        assert len(results) == 1
        assert results[0].intelligence_generated == pytest.approx(0.0)

    def test_sever_hex_excluded_from_surveillance(self) -> None:
        """SEVER hexes generate no surveillance (zero coupling effect)."""
        manager = self._make_manager_with_hexes(
            {
                "hex_a": {
                    "response_mode": InternetResponseMode.SEVER,
                    "surveillance_coupling": 0.5,
                },
            },
        )
        operator = DefaultInternetFieldOperator(manager)

        # SEVER hex is excluded from connected component,
        # so surveillance is only computed on connected hexes
        flow_magnitudes = {"hex_a": 5.0}
        results = operator.generate_surveillance(flow_magnitudes, 1.0)

        # hex_a severed → not in connected component → no surveillance
        assert len(results) == 0


@pytest.mark.unit
class TestInternetStateSerialization:
    """Tests for manager state serialization."""

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Manager state survives serialization roundtrip."""
        defines = InfraTerrainDefines()
        manager = DefaultInternetAccessManager(defines=defines)

        manager.set_state(
            InternetAccessState(
                h3_index="hex_a",
                internet_access=True,
                internet_quality=0.7,
                surveillance_coupling=0.4,
                response_mode=InternetResponseMode.THROTTLE,
            ),
        )

        data = manager.to_dict()
        restored = DefaultInternetAccessManager.from_dict(data, defines=defines)

        state = restored.get_state("hex_a")
        assert state is not None
        assert state.internet_access is True
        assert state.internet_quality == pytest.approx(0.7)
        assert state.surveillance_coupling == pytest.approx(0.4)
        assert state.response_mode == InternetResponseMode.THROTTLE
