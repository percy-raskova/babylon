"""Unit tests for God Mode Dashboard theme module.

Tests the Bunker Constructivism color palette and profit_rate_to_rgb()
color mapping function.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from babylon.ui.dashboard.theme import (
    BUNKER_CONSTRUCTIVISM,
    DATA_GREEN_RGB,
    PHOSPHOR_BURN_RED_RGB,
    QSS_THEME,
    profit_rate_to_hex,
    profit_rate_to_rgb,
)


class TestBunkerConstructivismPalette:
    """Tests for the Bunker Constructivism color palette constants."""

    def test_palette_has_required_colors(self) -> None:
        """Verify all required theme colors are defined."""
        required_colors = [
            "void",
            "wet_concrete",
            "soot",
            "data_green",
            "phosphor_burn_red",
            "amber_warning",
            "steel_gray",
        ]
        for color in required_colors:
            assert color in BUNKER_CONSTRUCTIVISM, f"Missing color: {color}"

    def test_colors_are_valid_hex(self) -> None:
        """Verify all colors are valid hex color strings."""
        import re

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for name, color in BUNKER_CONSTRUCTIVISM.items():
            assert hex_pattern.match(color), f"Invalid hex for {name}: {color}"

    def test_data_green_rgb_matches_hex(self) -> None:
        """Verify DATA_GREEN_RGB matches the hex definition."""
        # #39FF14 = (57, 255, 20)
        assert DATA_GREEN_RGB == (57, 255, 20)

    def test_phosphor_burn_red_rgb_matches_hex(self) -> None:
        """Verify PHOSPHOR_BURN_RED_RGB matches the hex definition."""
        # #D40000 = (212, 0, 0)
        assert PHOSPHOR_BURN_RED_RGB == (212, 0, 0)


class TestQssTheme:
    """Tests for the QSS stylesheet."""

    def test_qss_theme_not_empty(self) -> None:
        """Verify QSS theme is defined."""
        assert QSS_THEME
        assert len(QSS_THEME) > 0

    def test_qss_contains_main_window_style(self) -> None:
        """Verify QMainWindow styling is included."""
        assert "QMainWindow" in QSS_THEME

    def test_qss_contains_widget_style(self) -> None:
        """Verify QWidget styling is included."""
        assert "QWidget" in QSS_THEME

    def test_qss_uses_theme_colors(self) -> None:
        """Verify QSS uses colors from the theme palette."""
        # wet_concrete background
        assert "#1a1a1a" in QSS_THEME.lower()
        # data_green text
        assert "#39ff14" in QSS_THEME.lower()


class TestProfitRateToRgbRawRange:
    """Tests for profit_rate_to_rgb() with use_realistic_range=False (raw [0,1])."""

    def test_rate_zero_returns_red(self) -> None:
        """profit_rate=0.0 should return phosphor_burn_red."""
        result = profit_rate_to_rgb(0.0, use_realistic_range=False)
        assert result == PHOSPHOR_BURN_RED_RGB
        assert result == (212, 0, 0)

    def test_rate_one_returns_green(self) -> None:
        """profit_rate=1.0 should return data_green."""
        result = profit_rate_to_rgb(1.0, use_realistic_range=False)
        assert result == DATA_GREEN_RGB
        assert result == (57, 255, 20)

    def test_rate_half_returns_midpoint(self) -> None:
        """profit_rate=0.5 should return midpoint color."""
        result = profit_rate_to_rgb(0.5, use_realistic_range=False)
        # Midpoint calculation:
        # r = 212 + (57 - 212) * 0.5 = 212 - 77.5 = 134.5 -> 134
        # g = 0 + (255 - 0) * 0.5 = 127.5 -> 127
        # b = 0 + (20 - 0) * 0.5 = 10
        assert result == (134, 127, 10)

    def test_rate_quarter_returns_interpolated(self) -> None:
        """profit_rate=0.25 should interpolate toward red."""
        result = profit_rate_to_rgb(0.25, use_realistic_range=False)
        # r = 212 + (57 - 212) * 0.25 = 212 - 38.75 = 173.25 -> 173
        # g = 0 + 255 * 0.25 = 63.75 -> 63
        # b = 0 + 20 * 0.25 = 5
        assert result == (173, 63, 5)

    def test_rate_three_quarters_returns_interpolated(self) -> None:
        """profit_rate=0.75 should interpolate toward green."""
        result = profit_rate_to_rgb(0.75, use_realistic_range=False)
        # r = 212 + (57 - 212) * 0.75 = 212 - 116.25 = 95.75 -> 95
        # g = 0 + 255 * 0.75 = 191.25 -> 191
        # b = 0 + 20 * 0.75 = 15
        assert result == (95, 191, 15)

    def test_negative_rate_clamped_to_zero(self) -> None:
        """Negative profit_rate should clamp to 0.0 (red)."""
        result = profit_rate_to_rgb(-0.5, use_realistic_range=False)
        assert result == PHOSPHOR_BURN_RED_RGB

    def test_rate_above_one_clamped_to_one(self) -> None:
        """profit_rate > 1.0 should clamp to 1.0 (green)."""
        result = profit_rate_to_rgb(1.5, use_realistic_range=False)
        assert result == DATA_GREEN_RGB

    def test_rate_epsilon_below_zero_clamped(self) -> None:
        """Edge case: tiny negative value should clamp to red."""
        result = profit_rate_to_rgb(-0.001, use_realistic_range=False)
        assert result == PHOSPHOR_BURN_RED_RGB

    def test_rate_epsilon_above_one_clamped(self) -> None:
        """Edge case: tiny above-one value should clamp to green."""
        result = profit_rate_to_rgb(1.001, use_realistic_range=False)
        assert result == DATA_GREEN_RGB

    def test_returns_tuple_of_three_ints(self) -> None:
        """Result should be tuple of 3 integers."""
        result = profit_rate_to_rgb(0.5, use_realistic_range=False)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(c, int) for c in result)

    def test_all_values_in_valid_range(self) -> None:
        """All RGB values should be in [0, 255]."""
        for rate in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
            r, g, b = profit_rate_to_rgb(rate, use_realistic_range=False)
            assert 0 <= r <= 255, f"Red out of range at rate={rate}"
            assert 0 <= g <= 255, f"Green out of range at rate={rate}"
            assert 0 <= b <= 255, f"Blue out of range at rate={rate}"


class TestProfitRateToRgbRealisticRange:
    """Tests for profit_rate_to_rgb() with realistic Piketty range (3-8%)."""

    def test_piketty_min_returns_red(self) -> None:
        """3% profit_rate (Piketty floor) should return red."""
        result = profit_rate_to_rgb(0.03)  # 3%
        assert result == PHOSPHOR_BURN_RED_RGB

    def test_piketty_max_returns_green(self) -> None:
        """8% profit_rate (Piketty ceiling) should return green."""
        result = profit_rate_to_rgb(0.08)  # 8%
        assert result == DATA_GREEN_RGB

    def test_piketty_midpoint_returns_amber(self) -> None:
        """5.5% profit_rate (midpoint) should return midpoint color."""
        result = profit_rate_to_rgb(0.055)  # 5.5%
        # (0.055 - 0.03) / (0.08 - 0.03) = 0.025 / 0.05 = 0.5
        assert result == (134, 127, 10)  # Same as raw 0.5

    def test_below_piketty_min_clamped_to_red(self) -> None:
        """0% profit_rate (below Piketty floor) should clamp to red."""
        result = profit_rate_to_rgb(0.0)  # 0% - below floor
        assert result == PHOSPHOR_BURN_RED_RGB

    def test_above_piketty_max_clamped_to_green(self) -> None:
        """15% profit_rate (above Piketty ceiling) should clamp to green."""
        result = profit_rate_to_rgb(0.15)  # 15% - above ceiling
        assert result == DATA_GREEN_RGB


class TestProfitRateToHex:
    """Tests for profit_rate_to_hex() color mapping function."""

    def test_rate_zero_returns_red_hex_raw(self) -> None:
        """profit_rate=0.0 with raw range should return red hex."""
        result = profit_rate_to_hex(0.0, use_realistic_range=False)
        assert result == "#d40000"

    def test_rate_one_returns_green_hex_raw(self) -> None:
        """profit_rate=1.0 with raw range should return green hex."""
        result = profit_rate_to_hex(1.0, use_realistic_range=False)
        assert result == "#39ff14"

    def test_rate_half_returns_midpoint_hex_raw(self) -> None:
        """profit_rate=0.5 with raw range should return midpoint hex."""
        result = profit_rate_to_hex(0.5, use_realistic_range=False)
        # (134, 127, 10) -> #867f0a
        assert result == "#867f0a"

    def test_returns_lowercase_hex(self) -> None:
        """Result should be lowercase hex string."""
        result = profit_rate_to_hex(0.075)  # realistic midpoint
        assert result == result.lower()
        assert result.startswith("#")
        assert len(result) == 7

    def test_negative_rate_clamped(self) -> None:
        """Negative profit_rate should clamp to red."""
        result = profit_rate_to_hex(-1.0, use_realistic_range=False)
        assert result == "#d40000"

    def test_rate_above_one_clamped(self) -> None:
        """profit_rate > 1.0 should clamp to green."""
        result = profit_rate_to_hex(2.0, use_realistic_range=False)
        assert result == "#39ff14"

    def test_piketty_range_hex(self) -> None:
        """Test hex output with realistic Piketty range (3-8%)."""
        assert profit_rate_to_hex(0.03) == "#d40000"  # 3% -> red
        assert profit_rate_to_hex(0.08) == "#39ff14"  # 8% -> green
        assert profit_rate_to_hex(0.055) == "#867f0a"  # 5.5% -> midpoint
