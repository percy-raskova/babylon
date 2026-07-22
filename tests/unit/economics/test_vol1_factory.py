"""Unit tests for create_vol1_services (Capital Vol I U3 — transition_engine).

Feature: 021-capital-volume-i / vol1-value-production program, Unit U3

Before this unit, ``create_vol1_services`` wired 3 FRED-backed adapters
(``reserve_army_data_source``, ``productivity_data_source``,
``dispossession_data_source``) but no ``transition_engine`` — the field
``_simulate_transitions`` (domain/economics/tick/system/__init__.py) gates on
was never satisfied by any production caller of THIS factory (the one
canonical/web paths actually call). These tests pin the new contract: a real
``DefaultClassTransitionEngine`` whose dispossession calculator consumes the
SAME FRED adapter instance returned as ``dispossession_data_source`` — not a
second, independently-constructed ``HardcodedNationalDispossessionSource``
(the "no parallel Phi"-style collision the program prompt warns against for
any new Vol I data path).
"""

from __future__ import annotations

from babylon.domain.economics.dynamics.transition_engine import DefaultClassTransitionEngine
from babylon.domain.economics.factory import create_vol1_services

_EXPECTED_KEYS = frozenset(
    {
        "reserve_army_data_source",
        "productivity_data_source",
        "dispossession_data_source",
        "transition_engine",
    }
)


class TestCreateVol1Services:
    """Test create_vol1_services factory function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Factory returns exactly the 4 expected keys."""
        result = create_vol1_services(vol1_series_cache={}, fred_series_cache={})

        assert isinstance(result, dict)
        assert set(result.keys()) == _EXPECTED_KEYS

    def test_all_values_non_none(self) -> None:
        """Every value in the factory output is non-None."""
        result = create_vol1_services(vol1_series_cache={}, fred_series_cache={})

        for key, value in result.items():
            assert value is not None, f"Expected non-None value for key '{key}'"

    def test_transition_engine_is_default_class_transition_engine(self) -> None:
        """transition_engine is a real, non-mock DefaultClassTransitionEngine."""
        result = create_vol1_services(vol1_series_cache={}, fred_series_cache={})

        assert isinstance(result["transition_engine"], DefaultClassTransitionEngine)

    def test_transition_engine_shares_the_dispossession_adapter(self) -> None:
        """transition_engine's own dispossession calculator wraps the SAME
        adapter instance returned as dispossession_data_source — not a
        second, independently-constructed data source. White-box check
        (private attrs) because the whole point of this unit is proving NO
        parallel dispossession-data path exists, which only an identity
        check on the injected object can show.
        """
        result = create_vol1_services(vol1_series_cache={}, fred_series_cache={})

        engine = result["transition_engine"]
        disp_calc = engine._disp_calc  # noqa: SLF001 - identity check is the point
        assert disp_calc._data_source is result["dispossession_data_source"]  # noqa: SLF001

    def test_transition_engine_dispossession_reflects_real_fred_data(self) -> None:
        """A post-2020 UNRATE reading in the cache drives the SAME
        foreclosure/bankruptcy/eviction proxy the dispossession_data_source
        itself would report — proving the transition_engine sees real,
        not hardcoded, data for this county-year.
        """
        vol1_cache = {"UNRATE": {2022: 0.036}}
        result = create_vol1_services(vol1_series_cache=vol1_cache, fred_series_cache={})

        disp_source = result["dispossession_data_source"]
        expected_foreclosure = disp_source.get_foreclosure_rate("26163", 2022)
        expected_bankruptcy = disp_source.get_bankruptcy_rate("26163", 2022)
        expected_eviction = disp_source.get_eviction_rate("26163", 2022)

        disp_result = result["transition_engine"]._disp_calc.compute(  # noqa: SLF001
            "26163", 2022
        )
        assert disp_result.foreclosure_risk == expected_foreclosure
        assert disp_result.bankruptcy_risk == expected_bankruptcy
        assert disp_result.eviction_risk == expected_eviction
