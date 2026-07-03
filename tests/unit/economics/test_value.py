"""Validation tests for the Marxian value poles in :mod:`babylon.economics.value`.

Provenance (C1.7 test-migration ledger): these construction/validation
intents were previously pinned only inside the dormant dialectics layer's
suites — ``UseValue``/``ExchangeValue`` in
``tests/unit/engine/dialectics/test_commodity.py`` and
``ConcreteLabor``/``AbstractLabor`` in
``tests/unit/engine/dialectics/test_production.py``. Those files were retired
with ``babylon.engine.dialectics`` (``project/06-lawverian-dialectics.md`` §5
item 6), but the four pole types themselves live on in
``babylon.economics.value`` and had no other coverage, so their field
contracts are migrated here verbatim.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.value import AbstractLabor, ConcreteLabor, ExchangeValue, UseValue

pytestmark = pytest.mark.math


class TestUseValue:
    """UseValue pole construction and validation (V1 Ch1)."""

    def test_default_construction(self) -> None:
        uv = UseValue()
        assert uv.utility >= 0.0
        assert uv.demand >= 0.0

    def test_custom_values(self) -> None:
        uv = UseValue(utility=0.8, demand=120.0)
        assert uv.utility == 0.8
        assert uv.demand == 120.0

    def test_utility_bounded_0_1(self) -> None:
        with pytest.raises(ValidationError):
            UseValue(utility=-0.1)
        with pytest.raises(ValidationError):
            UseValue(utility=1.1)


class TestExchangeValue:
    """ExchangeValue pole construction and validation (V1 Ch1)."""

    def test_default_construction(self) -> None:
        ev = ExchangeValue()
        assert ev.price >= 0.0
        assert ev.snlt >= 0.0

    def test_custom_values(self) -> None:
        ev = ExchangeValue(price=50.0, snlt=40.0)
        assert ev.price == 50.0
        assert ev.snlt == 40.0

    def test_snlt_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ExchangeValue(snlt=-1.0)

    def test_price_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ExchangeValue(price=-1.0)


class TestConcreteLabor:
    """ConcreteLabor pole construction and validation (V1 Ch1§2)."""

    def test_default_construction(self) -> None:
        cl = ConcreteLabor()
        assert 0.0 <= cl.skill <= 1.0
        assert 0.0 <= cl.intensity <= 1.0
        assert cl.hours >= 0.0

    def test_custom_values(self) -> None:
        cl = ConcreteLabor(skill=0.8, intensity=0.6, hours=8.0, labor_type="spinning")
        assert cl.skill == 0.8
        assert cl.intensity == 0.6
        assert cl.hours == 8.0
        assert cl.labor_type == "spinning"

    def test_skill_bounded(self) -> None:
        with pytest.raises(ValidationError):
            ConcreteLabor(skill=-0.1)
        with pytest.raises(ValidationError):
            ConcreteLabor(skill=1.1)

    def test_intensity_bounded(self) -> None:
        with pytest.raises(ValidationError):
            ConcreteLabor(intensity=-0.1)
        with pytest.raises(ValidationError):
            ConcreteLabor(intensity=1.1)


class TestAbstractLabor:
    """AbstractLabor pole construction and validation (V1 Ch1§2)."""

    def test_default_construction(self) -> None:
        al = AbstractLabor()
        assert al.snlt >= 0.0
        assert al.productivity > 0.0

    def test_custom_values(self) -> None:
        al = AbstractLabor(snlt=4.0, productivity=1.5)
        assert al.snlt == 4.0
        assert al.productivity == 1.5

    def test_snlt_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            AbstractLabor(snlt=-1.0)

    def test_productivity_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            AbstractLabor(productivity=0.0)
        with pytest.raises(ValidationError):
            AbstractLabor(productivity=-1.0)
