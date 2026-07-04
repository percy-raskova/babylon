"""Unit tests for the Observatory SQL builders (spec-096, no DB).

These pin the read-only boundary at the SQL level: queries reference ONLY the
declared view interfaces + ``tick_commit`` (+ optional ``game_session``), never
the raw sparse ``dynamic_hex_state``, and every value is a bound parameter.
"""

from __future__ import annotations

import pytest

from observatory import queries

pytestmark = pytest.mark.unit

_SID = "bc680a68-0000-4000-8000-000000000000"

# Every SQL string the module can emit, for the "no raw table" sweep.
_ALL_STATIC_SQL = [
    queries.SESSIONS_SQL,
    queries.TICK_RANGE_SQL,
    queries.COMMITS_SQL,
    queries.HEX_FRAME_SQL,
]


class TestNoRawDynamicHexState:
    def test_no_static_sql_reads_raw_delta_table(self) -> None:
        for sql in _ALL_STATIC_SQL:
            assert "dynamic_hex_state" not in sql

    def test_series_builders_never_touch_raw_table(self) -> None:
        for scope in ("national", "state", "county"):
            sql, _ = queries.build_series_query(scope, _SID, "USA", 0, 10)
            assert "dynamic_hex_state" not in sql

    def test_hex_query_uses_asof_view(self) -> None:
        sql, _ = queries.build_hex_query(_SID, 3, None, None, 10)
        assert "v_hex_state_asof" in sql
        assert "dynamic_hex_state" not in sql


class TestSeriesQueryBuilder:
    def test_scope_selects_correct_view(self) -> None:
        assert (
            "v_national_value_aggregate"
            in queries.build_series_query("national", _SID, "USA", 0, 5)[0]
        )
        assert "v_state_value_aggregate" in queries.build_series_query("state", _SID, "26", 0, 5)[0]
        assert (
            "v_county_value_aggregate"
            in queries.build_series_query("county", _SID, "26163", 0, 5)[0]
        )

    def test_values_are_bound_parameters(self) -> None:
        sql, params = queries.build_series_query("county", _SID, "26163", 2, 9)
        # 4 placeholders: session_id, scope_id, from_tick, to_tick
        assert sql.count("%s") == 4
        assert params == (_SID, "26163", 2, 9)
        # The concrete values must NOT be interpolated into the SQL text.
        assert _SID not in sql
        assert "26163" not in sql

    def test_unknown_scope_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown scope"):
            queries.build_series_query("galactic", _SID, "x", 0, 1)


class TestHexQueryBuilder:
    def test_bounded_query_has_limit(self) -> None:
        sql, params = queries.build_hex_query(_SID, 4, None, None, 10)
        assert "LIMIT %s" in sql
        # session_id, tick, fetch_limit
        assert params == (_SID, 4, 10)
        assert sql.count("%s") == 3

    def test_county_filter_adds_parameter(self) -> None:
        sql, params = queries.build_hex_query(_SID, 4, "26163", None, 10)
        assert "county_fips = %s" in sql
        assert params == (_SID, 4, "26163", 10)

    def test_after_h3_cursor_adds_predicate(self) -> None:
        sql, params = queries.build_hex_query(_SID, 4, None, "872a91055ffffff", 10)
        assert "h3_index > %s" in sql
        assert params == (_SID, 4, "872a91055ffffff", 10)

    def test_county_and_cursor_combined(self) -> None:
        sql, params = queries.build_hex_query(_SID, 4, "26163", "872a91055ffffff", 10)
        assert params == (_SID, 4, "26163", "872a91055ffffff", 10)
        assert "county_fips = %s" in sql
        assert "h3_index > %s" in sql


class TestScopeWhitelist:
    def test_scope_views_are_declared_interfaces_only(self) -> None:
        views = {v for v, _c, _d in queries.SCOPE_VIEWS.values()}
        assert views == {
            "v_national_value_aggregate",
            "v_state_value_aggregate",
            "v_county_value_aggregate",
        }
