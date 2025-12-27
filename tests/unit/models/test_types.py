"""Tests for babylon.models.types.

TDD Red Phase: These tests define the contract for constrained value types.
Each type must:
1. Accept values within its valid range
2. Reject values outside its valid range with ValidationError
3. Handle IEEE 754 floating-point edge cases
4. Work correctly in Pydantic models
"""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError, create_model

from babylon.models.types import (
    Coefficient,
    Currency,
    Ideology,
    Intensity,
    Probability,
    Ratio,
)

# =============================================================================
# TEST UTILITIES
# =============================================================================


def make_model_with_field(field_type: Any, field_name: str = "value") -> type[BaseModel]:
    """Create a test model with a single field of the given type.

    Uses Pydantic's create_model to properly handle Annotated types.
    """
    return create_model(
        "TestModel",
        **{field_name: (field_type, ...)},  # ... means required
    )


# =============================================================================
# PROBABILITY TESTS [0.0, 1.0]
# =============================================================================


@pytest.mark.math
class TestProbability:
    """Probability: [0.0, 1.0] - used for P(S|A), P(S|R), tension.

    A probability represents the likelihood of an event occurring.
    It must be bounded between 0 (impossible) and 1 (certain).
    """

    @pytest.fixture
    def model(self) -> type[BaseModel]:
        """Model with a Probability field."""
        return make_model_with_field(Probability, "prob")

    # Boundary tests
    def test_accepts_zero(self, model: type[BaseModel]) -> None:
        """0.0 = impossible event is valid."""
        instance = model(prob=0.0)
        assert instance.prob == 0.0

    def test_accepts_one(self, model: type[BaseModel]) -> None:
        """1.0 = certain event is valid."""
        instance = model(prob=1.0)
        assert instance.prob == 1.0

    def test_accepts_midpoint(self, model: type[BaseModel]) -> None:
        """0.5 = coin flip is valid."""
        instance = model(prob=0.5)
        assert instance.prob == 0.5

    def test_accepts_small_positive(self, model: type[BaseModel]) -> None:
        """Small positive values are valid."""
        instance = model(prob=0.001)
        assert instance.prob == pytest.approx(0.001)

    def test_accepts_near_one(self, model: type[BaseModel]) -> None:
        """Values near 1.0 are valid."""
        instance = model(prob=0.999)
        assert instance.prob == pytest.approx(0.999)

    # Rejection tests
    def test_rejects_negative(self, model: type[BaseModel]) -> None:
        """Negative probabilities are invalid."""
        with pytest.raises(ValidationError):
            model(prob=-0.001)

    def test_rejects_negative_one(self, model: type[BaseModel]) -> None:
        """Strongly negative values are invalid."""
        with pytest.raises(ValidationError):
            model(prob=-1.0)

    def test_rejects_greater_than_one(self, model: type[BaseModel]) -> None:
        """Probabilities > 1.0 are invalid."""
        with pytest.raises(ValidationError):
            model(prob=1.001)

    def test_rejects_large_positive(self, model: type[BaseModel]) -> None:
        """Large positive values are invalid."""
        with pytest.raises(ValidationError):
            model(prob=2.0)

    # Edge case tests
    def test_handles_float_precision_addition(self, model: type[BaseModel]) -> None:
        """0.1 + 0.2 = 0.30000000000000004 should work."""
        val = 0.1 + 0.2  # IEEE 754 gives 0.30000000000000004
        instance = model(prob=val)
        assert instance.prob == pytest.approx(0.3, abs=1e-9)


# =============================================================================
# IDEOLOGY TESTS [-1.0, 1.0]
# =============================================================================


@pytest.mark.math
class TestIdeology:
    """Ideology: [-1.0, 1.0] - revolutionary to reactionary spectrum.

    -1.0 = fully revolutionary (class conscious, anti-capitalist)
    +1.0 = fully reactionary (false consciousness, pro-status-quo)
     0.0 = neutral/apolitical
    """

    @pytest.fixture
    def model(self) -> type[BaseModel]:
        """Model with an Ideology field."""
        return make_model_with_field(Ideology, "ideology")

    # Boundary tests
    def test_accepts_negative_one(self, model: type[BaseModel]) -> None:
        """-1.0 = fully revolutionary is valid."""
        instance = model(ideology=-1.0)
        assert instance.ideology == -1.0

    def test_accepts_positive_one(self, model: type[BaseModel]) -> None:
        """+1.0 = fully reactionary is valid."""
        instance = model(ideology=1.0)
        assert instance.ideology == 1.0

    def test_accepts_zero(self, model: type[BaseModel]) -> None:
        """0.0 = neutral is valid."""
        instance = model(ideology=0.0)
        assert instance.ideology == 0.0

    def test_accepts_negative_half(self, model: type[BaseModel]) -> None:
        """-0.5 = leaning revolutionary is valid."""
        instance = model(ideology=-0.5)
        assert instance.ideology == -0.5

    def test_accepts_positive_half(self, model: type[BaseModel]) -> None:
        """+0.5 = leaning reactionary is valid."""
        instance = model(ideology=0.5)
        assert instance.ideology == 0.5

    # Rejection tests
    def test_rejects_less_than_negative_one(self, model: type[BaseModel]) -> None:
        """Values < -1.0 are invalid."""
        with pytest.raises(ValidationError):
            model(ideology=-1.001)

    def test_rejects_greater_than_one(self, model: type[BaseModel]) -> None:
        """Values > 1.0 are invalid."""
        with pytest.raises(ValidationError):
            model(ideology=1.001)

    def test_rejects_large_magnitude(self, model: type[BaseModel]) -> None:
        """Large magnitude values are invalid."""
        with pytest.raises(ValidationError):
            model(ideology=-5.0)
        with pytest.raises(ValidationError):
            model(ideology=5.0)


# =============================================================================
# CURRENCY TESTS [0.0, infinity)
# =============================================================================


@pytest.mark.math
class TestCurrency:
    """Currency: [0.0, inf) - wealth, wages, rent, GDP.

    Currency represents economic value. It can be zero (destitute)
    or arbitrarily large, but never negative.
    """

    @pytest.fixture
    def model(self) -> type[BaseModel]:
        """Model with a Currency field."""
        return make_model_with_field(Currency, "wealth")

    # Boundary tests
    def test_accepts_zero(self, model: type[BaseModel]) -> None:
        """0.0 = destitute is valid."""
        instance = model(wealth=0.0)
        assert instance.wealth == 0.0

    def test_accepts_positive(self, model: type[BaseModel]) -> None:
        """Positive values are valid."""
        instance = model(wealth=100.0)
        assert instance.wealth == 100.0

    def test_accepts_large_values(self, model: type[BaseModel]) -> None:
        """Large values (like GDP) are valid."""
        instance = model(wealth=1_000_000_000.0)
        assert instance.wealth == 1_000_000_000.0

    def test_accepts_small_positive(self, model: type[BaseModel]) -> None:
        """Small positive values are valid."""
        instance = model(wealth=0.01)
        assert instance.wealth == pytest.approx(0.01)

    # Rejection tests
    def test_rejects_negative(self, model: type[BaseModel]) -> None:
        """Negative currency is invalid (no debt representation)."""
        with pytest.raises(ValidationError):
            model(wealth=-0.01)

    def test_rejects_strongly_negative(self, model: type[BaseModel]) -> None:
        """Strongly negative values are invalid."""
        with pytest.raises(ValidationError):
            model(wealth=-1000.0)


# =============================================================================
# INTENSITY TESTS [0.0, 1.0]
# =============================================================================


@pytest.mark.math
class TestIntensity:
    """Intensity: [0.0, 1.0] - contradiction intensity.

    0.0 = dormant (contradiction not yet manifest)
    1.0 = rupture threshold (phase transition imminent)
    """

    @pytest.fixture
    def model(self) -> type[BaseModel]:
        """Model with an Intensity field."""
        return make_model_with_field(Intensity, "tension")

    # Boundary tests
    def test_accepts_zero(self, model: type[BaseModel]) -> None:
        """0.0 = dormant is valid."""
        instance = model(tension=0.0)
        assert instance.tension == 0.0

    def test_accepts_one(self, model: type[BaseModel]) -> None:
        """1.0 = rupture threshold is valid."""
        instance = model(tension=1.0)
        assert instance.tension == 1.0

    def test_accepts_midpoint(self, model: type[BaseModel]) -> None:
        """0.5 = moderate tension is valid."""
        instance = model(tension=0.5)
        assert instance.tension == 0.5

    # Rejection tests
    def test_rejects_negative(self, model: type[BaseModel]) -> None:
        """Negative intensity is invalid."""
        with pytest.raises(ValidationError):
            model(tension=-0.1)

    def test_rejects_greater_than_one(self, model: type[BaseModel]) -> None:
        """Intensity > 1.0 is invalid (capped at rupture)."""
        with pytest.raises(ValidationError):
            model(tension=1.1)


# =============================================================================
# COEFFICIENT TESTS [0.0, 1.0]
# =============================================================================


@pytest.mark.math
class TestCoefficient:
    """Coefficient: [0.0, 1.0] - formula parameters (alpha, lambda, k).

    Coefficients modify the strength of effects in formulas.
    0.0 = no effect, 1.0 = maximum effect.
    """

    @pytest.fixture
    def model(self) -> type[BaseModel]:
        """Model with a Coefficient field."""
        return make_model_with_field(Coefficient, "alpha")

    # Boundary tests
    def test_accepts_zero(self, model: type[BaseModel]) -> None:
        """0.0 = no effect is valid."""
        instance = model(alpha=0.0)
        assert instance.alpha == 0.0

    def test_accepts_one(self, model: type[BaseModel]) -> None:
        """1.0 = full effect is valid."""
        instance = model(alpha=1.0)
        assert instance.alpha == 1.0

    def test_accepts_typical_value(self, model: type[BaseModel]) -> None:
        """Typical coefficient value is valid."""
        instance = model(alpha=0.25)
        assert instance.alpha == pytest.approx(0.25)

    # Rejection tests
    def test_rejects_negative(self, model: type[BaseModel]) -> None:
        """Negative coefficients are invalid."""
        with pytest.raises(ValidationError):
            model(alpha=-0.1)

    def test_rejects_greater_than_one(self, model: type[BaseModel]) -> None:
        """Coefficients > 1.0 are invalid."""
        with pytest.raises(ValidationError):
            model(alpha=1.5)


# =============================================================================
# RATIO TESTS (0.0, infinity)
# =============================================================================


@pytest.mark.math
class TestRatio:
    """Ratio: (0.0, inf) - wage ratios, exchange ratios.

    Ratios compare two quantities. Zero is invalid (division result).
    Ratio > 1.0 means numerator > denominator.
    """

    @pytest.fixture
    def model(self) -> type[BaseModel]:
        """Model with a Ratio field."""
        return make_model_with_field(Ratio, "exchange_ratio")

    # Boundary tests
    def test_accepts_one(self, model: type[BaseModel]) -> None:
        """1.0 = equal exchange is valid."""
        instance = model(exchange_ratio=1.0)
        assert instance.exchange_ratio == 1.0

    def test_accepts_greater_than_one(self, model: type[BaseModel]) -> None:
        """Ratio > 1.0 (exploitation) is valid."""
        instance = model(exchange_ratio=2.5)
        assert instance.exchange_ratio == 2.5

    def test_accepts_less_than_one(self, model: type[BaseModel]) -> None:
        """Ratio < 1.0 is valid."""
        instance = model(exchange_ratio=0.5)
        assert instance.exchange_ratio == 0.5

    def test_accepts_large_ratio(self, model: type[BaseModel]) -> None:
        """Large ratios (severe exploitation) are valid."""
        instance = model(exchange_ratio=20.0)
        assert instance.exchange_ratio == 20.0

    def test_accepts_small_positive(self, model: type[BaseModel]) -> None:
        """Small positive ratios are valid."""
        instance = model(exchange_ratio=0.001)
        assert instance.exchange_ratio == pytest.approx(0.001)

    # Rejection tests
    def test_rejects_zero(self, model: type[BaseModel]) -> None:
        """Zero ratio is invalid (undefined)."""
        with pytest.raises(ValidationError):
            model(exchange_ratio=0.0)

    def test_rejects_negative(self, model: type[BaseModel]) -> None:
        """Negative ratios are invalid."""
        with pytest.raises(ValidationError):
            model(exchange_ratio=-1.0)


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


# =============================================================================
# QUANTIZATION TESTS (RED PHASE - 10^-5 Grid)
# =============================================================================


@pytest.mark.math
class TestTypeQuantization:
    """Test that constrained types apply SnapToGrid quantization.

    Epoch 0 Physics Hardening requires all constrained types to snap
    values to a 10^-5 grid (0.00001 resolution) to prevent floating-point
    drift accumulation over long simulations.

    This is implemented via Pydantic AfterValidator on each type.
    """

    def test_probability_quantizes_on_assignment(self) -> None:
        """Probability values are snapped to 10^-5 grid.

        Input: 0.123456789 (9 decimal places)
        Expected: 0.12346 (5 decimal places, rounded)
        """
        Model = make_model_with_field(Probability, "prob")

        model = Model(prob=0.123456789)

        assert model.prob == 0.12346

    def test_ideology_quantizes_on_assignment(self) -> None:
        """Ideology values are snapped to 10^-5 grid.

        Ideology ranges from -1 to 1, quantization applies throughout.
        """
        Model = make_model_with_field(Ideology, "ideology")

        # Positive value
        model_pos = Model(ideology=0.567891234)
        assert model_pos.ideology == 0.56789

        # Negative value
        model_neg = Model(ideology=-0.567891234)
        assert model_neg.ideology == -0.56789

    def test_currency_quantizes_on_assignment(self) -> None:
        """Currency values are snapped to 10^-5 grid.

        Currency can be large values; quantization applies to decimal portion.
        """
        Model = make_model_with_field(Currency, "wealth")

        model = Model(wealth=1234.567891)

        assert model.wealth == 1234.56789

    def test_intensity_quantizes_on_assignment(self) -> None:
        """Intensity values are snapped to 10^-5 grid.

        Intensity [0, 1] used for contradiction tension.
        """
        Model = make_model_with_field(Intensity, "tension")

        model = Model(tension=0.999994)

        assert model.tension == 0.99999

    def test_coefficient_quantizes_on_assignment(self) -> None:
        """Coefficient values are snapped to 10^-5 grid.

        Coefficients [0, 1] used for formula parameters.
        """
        Model = make_model_with_field(Coefficient, "alpha")

        model = Model(alpha=0.251234567)

        assert model.alpha == 0.25123

    def test_ratio_quantizes_on_assignment(self) -> None:
        """Ratio values are snapped to 10^-5 grid.

        Ratio (0, inf) used for exchange ratios.
        """
        Model = make_model_with_field(Ratio, "exchange_ratio")

        model = Model(exchange_ratio=2.718281828)

        assert model.exchange_ratio == 2.71828


@pytest.mark.math
class TestTypeSerialization:
    """Test that constrained types serialize correctly to JSON."""

    def test_probability_serializes_to_float(self) -> None:
        """Probability serializes as plain float in JSON."""
        Model = make_model_with_field(Probability, "p")
        instance = Model(p=0.75)
        json_data = instance.model_dump_json()
        assert '"p":0.75' in json_data or '"p": 0.75' in json_data

    def test_ideology_serializes_to_float(self) -> None:
        """Ideology serializes as plain float in JSON."""
        Model = make_model_with_field(Ideology, "i")
        instance = Model(i=-0.5)
        json_data = instance.model_dump_json()
        assert '"-0.5"' not in json_data  # Not a string
        assert "-0.5" in json_data  # Is a number

    def test_currency_serializes_to_float(self) -> None:
        """Currency serializes as plain float in JSON."""
        Model = make_model_with_field(Currency, "c")
        instance = Model(c=1000.0)
        json_data = instance.model_dump_json()
        assert "1000" in json_data

    def test_round_trip_preserves_values(self) -> None:
        """Model survives JSON round-trip."""

        class FullModel(BaseModel):
            prob: Probability
            ideology: Ideology
            wealth: Currency
            tension: Intensity
            alpha: Coefficient
            ratio: Ratio

        original = FullModel(
            prob=0.75,
            ideology=-0.3,
            wealth=500.0,
            tension=0.8,
            alpha=0.25,
            ratio=2.5,
        )

        json_str = original.model_dump_json()
        restored = FullModel.model_validate_json(json_str)

        assert restored.prob == pytest.approx(original.prob)
        assert restored.ideology == pytest.approx(original.ideology)
        assert restored.wealth == pytest.approx(original.wealth)
        assert restored.tension == pytest.approx(original.tension)
        assert restored.alpha == pytest.approx(original.alpha)
        assert restored.ratio == pytest.approx(original.ratio)
