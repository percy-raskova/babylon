"""Unit tests for the predefined scope resolver (T019, spec-064)."""

from __future__ import annotations

import pytest

from babylon.engine.headless_runner.scopes import (
    DETROIT_TRI_COUNTY_FIPS,
    MICHIGAN_FIPS,
    UnknownScopeError,
    resolve_scope,
)


class TestPredefinedScopes:
    """Each documented scope resolves to its declared FIPS set + externals."""

    def test_michigan_canada_has_83_counties_and_canada(self) -> None:
        scope = resolve_scope("michigan-canada")
        assert len(scope.scope_fips) == 83
        assert scope.scope_fips == MICHIGAN_FIPS
        assert scope.external_node_ids == frozenset({"canada"})

    def test_michigan_statewide_no_canada_has_83_counties_and_no_externals(
        self,
    ) -> None:
        scope = resolve_scope("michigan-statewide-no-canada")
        assert len(scope.scope_fips) == 83
        assert scope.scope_fips == MICHIGAN_FIPS
        assert scope.external_node_ids == frozenset()

    def test_detroit_tri_county_yields_wayne_oakland_macomb(self) -> None:
        scope = resolve_scope("detroit-tri-county")
        assert scope.scope_fips == frozenset({"26163", "26125", "26099"})
        assert scope.scope_fips == DETROIT_TRI_COUNTY_FIPS
        assert scope.external_node_ids == frozenset({"canada"})

    def test_national_yields_at_least_3000_fips(self) -> None:
        scope = resolve_scope("national")
        assert len(scope.scope_fips) >= 3000
        assert all(len(f) == 5 and f.isdigit() for f in scope.scope_fips)
        assert scope.external_node_ids == frozenset({"canada", "china"})

    def test_unknown_scope_raises(self) -> None:
        with pytest.raises(UnknownScopeError, match="Unknown scope"):
            resolve_scope("not-a-real-scope")
