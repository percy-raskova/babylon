"""Unit tests for DepreciationConfig.

Tests for the depreciation configuration dataclass used in capital stock
computation via the perpetual inventory method.

Feature: 012-capital-stock-dynamics
Phase: 2 - Foundational (TDD)
Tasks: T008-T014
"""

from __future__ import annotations

import pytest

from babylon.economics.depreciation import (
    DEFAULT_DEPRECIATION_RATE,
    FAST_DEPRECIATION_RATE,
    MAX_DEPRECIATION_RATE,
    MIN_DEPRECIATION_RATE,
    SLOW_DEPRECIATION_RATE,
    DepreciationConfig,
)


class TestDepreciationConfigDefaults:
    """Tests for DepreciationConfig default values and validation."""

    def test_default_rate_is_007(self) -> None:
        """T008: DepreciationConfig default rate should be 0.07 (BEA average)."""
        config = DepreciationConfig()
        assert config.rate == DEFAULT_DEPRECIATION_RATE
        assert config.rate == 0.07

    def test_validation_rejects_rate_below_minimum(self) -> None:
        """T009: DepreciationConfig should reject rate < 0.01."""
        with pytest.raises(ValueError, match=r"Depreciation rate must be in"):
            DepreciationConfig(rate=0.005)

        with pytest.raises(ValueError, match=r"Depreciation rate must be in"):
            DepreciationConfig(rate=0.0)

        with pytest.raises(ValueError, match=r"Depreciation rate must be in"):
            DepreciationConfig(rate=-0.05)

    def test_validation_rejects_rate_above_maximum(self) -> None:
        """T010: DepreciationConfig should reject rate > 0.20."""
        with pytest.raises(ValueError, match=r"Depreciation rate must be in"):
            DepreciationConfig(rate=0.25)

        with pytest.raises(ValueError, match=r"Depreciation rate must be in"):
            DepreciationConfig(rate=0.50)

        with pytest.raises(ValueError, match=r"Depreciation rate must be in"):
            DepreciationConfig(rate=1.0)

    def test_validation_accepts_boundary_values(self) -> None:
        """Boundary values at min and max should be accepted."""
        # Minimum boundary
        config_min = DepreciationConfig(rate=MIN_DEPRECIATION_RATE)
        assert config_min.rate == 0.01

        # Maximum boundary
        config_max = DepreciationConfig(rate=MAX_DEPRECIATION_RATE)
        assert config_max.rate == 0.20


class TestDepreciationConfigFactoryMethods:
    """Tests for DepreciationConfig factory methods."""

    def test_slow_factory_returns_005(self) -> None:
        """T011: DepreciationConfig.slow() should return δ = 0.05."""
        config = DepreciationConfig.slow()
        assert config.rate == SLOW_DEPRECIATION_RATE
        assert config.rate == 0.05

    def test_fast_factory_returns_010(self) -> None:
        """T012: DepreciationConfig.fast() should return δ = 0.10."""
        config = DepreciationConfig.fast()
        assert config.rate == FAST_DEPRECIATION_RATE
        assert config.rate == 0.10

    def test_default_factory_returns_007(self) -> None:
        """DepreciationConfig.default() should return δ = 0.07."""
        config = DepreciationConfig.default()
        assert config.rate == DEFAULT_DEPRECIATION_RATE
        assert config.rate == 0.07


class TestDepreciationConfigSteadyStateK:
    """Tests for steady_state_K() method."""

    def test_steady_state_K_formula(self) -> None:
        """T013: steady_state_K() should compute K = I/δ."""
        config = DepreciationConfig(rate=0.07)

        # K = 70 / 0.07 = 1000
        assert config.steady_state_K(70.0) == pytest.approx(1000.0)

        # K = 35 / 0.07 = 500
        assert config.steady_state_K(35.0) == pytest.approx(500.0)

        # K = 140 / 0.07 = 2000
        assert config.steady_state_K(140.0) == pytest.approx(2000.0)

    def test_steady_state_K_with_different_rates(self) -> None:
        """Steady-state K should vary inversely with depreciation rate."""
        investment = 100.0

        slow = DepreciationConfig.slow()  # δ = 0.05
        default = DepreciationConfig.default()  # δ = 0.07
        fast = DepreciationConfig.fast()  # δ = 0.10

        # K = I/δ, so lower δ → higher K
        assert slow.steady_state_K(investment) == pytest.approx(2000.0)  # 100/0.05
        assert default.steady_state_K(investment) == pytest.approx(1428.57, rel=0.01)  # 100/0.07
        assert fast.steady_state_K(investment) == pytest.approx(1000.0)  # 100/0.10

        # Verify ordering: K_slow > K_default > K_fast
        assert slow.steady_state_K(investment) > default.steady_state_K(investment)
        assert default.steady_state_K(investment) > fast.steady_state_K(investment)


class TestDepreciationConfigNextK:
    """Tests for next_K() perpetual inventory formula."""

    def test_next_K_perpetual_inventory_formula(self) -> None:
        """T014: next_K() should compute K[t+1] = K[t] × (1-δ) + I[t]."""
        config = DepreciationConfig(rate=0.07)

        # Steady state: K_t = 1000, I_t = 70
        # K_{t+1} = 1000 × 0.93 + 70 = 930 + 70 = 1000
        assert config.next_K(1000.0, 70.0) == pytest.approx(1000.0)

        # Growing capital: K_t = 1000, I_t = 100
        # K_{t+1} = 1000 × 0.93 + 100 = 930 + 100 = 1030
        assert config.next_K(1000.0, 100.0) == pytest.approx(1030.0)

        # Declining capital: K_t = 1000, I_t = 50
        # K_{t+1} = 1000 × 0.93 + 50 = 930 + 50 = 980
        assert config.next_K(1000.0, 50.0) == pytest.approx(980.0)

    def test_next_K_clamps_to_non_negative(self) -> None:
        """next_K() should clamp result to >= 0."""
        config = DepreciationConfig(rate=0.20)  # High depreciation

        # Extreme case: K_t = 10, I_t = 0
        # K_{t+1} = 10 × 0.80 + 0 = 8 (still positive)
        assert config.next_K(10.0, 0.0) == pytest.approx(8.0)

        # Edge case: Very small K with zero investment
        # Should approach zero but never go negative
        K = 1.0
        for _ in range(100):
            K = config.next_K(K, 0.0)
        assert K >= 0.0

    def test_next_K_with_zero_current_K(self) -> None:
        """next_K() should work correctly when starting from zero."""
        config = DepreciationConfig(rate=0.07)

        # K_t = 0, I_t = 70
        # K_{t+1} = 0 × 0.93 + 70 = 70
        assert config.next_K(0.0, 70.0) == pytest.approx(70.0)


class TestDepreciationConfigImmutability:
    """Tests for DepreciationConfig immutability."""

    def test_config_is_frozen(self) -> None:
        """DepreciationConfig should be immutable (frozen dataclass)."""
        from dataclasses import FrozenInstanceError

        config = DepreciationConfig(rate=0.07)

        with pytest.raises(FrozenInstanceError):
            config.rate = 0.10  # type: ignore[misc]

    def test_config_is_hashable(self) -> None:
        """Frozen dataclass should be hashable for use in sets/dicts."""
        config1 = DepreciationConfig(rate=0.07)
        config2 = DepreciationConfig(rate=0.07)
        config3 = DepreciationConfig(rate=0.05)

        # Same values should have same hash
        assert hash(config1) == hash(config2)

        # Can use in set
        config_set = {config1, config2, config3}
        assert len(config_set) == 2  # config1 and config2 are equal
