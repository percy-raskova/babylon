"""Performance optimization tests for hex hydrator (national-scale hydration).

Tests the three optimizations that unblock E:105:
  1. Parallel H3 polyfill via ProcessPoolExecutor (CPU-bound step)
  2. COPY-based bulk insert for hex_spatial_map (replaces executemany)
  3. COPY-based bulk insert for dynamic_hex_state (replaces executemany)

Determinism invariant: the optimized pipeline must produce the same set
of hex rows with the same values as the serial pipeline. Order may differ
(PK is (session_id, tick, h3_index)) but the row SET must be identical.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def _make_square(lon: float, lat: float, size: float = 0.3) -> object:  # type: ignore[name-defined]
    """Create a square shapely Polygon centered at (lon, lat)."""
    from shapely.geometry import Polygon

    half = size / 2
    return Polygon(
        [
            (lon - half, lat - half),
            (lon + half, lat - half),
            (lon + half, lat + half),
            (lon - half, lat + half),
        ]
    )


@pytest.fixture
def _force_parallel_path(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Force ``_polygons_to_hexes_parallel`` onto the ProcessPoolExecutor branch.

    ``_PARALLEL_POLYFILL_THRESHOLD`` is 8 in production; every fixture in
    this module uses fewer counties than that, so without this patch the
    "parallel" tests silently run the serial fallback (``len(polygons) <
    threshold``) and can never fail on a real parallel-path defect.
    Lowering the threshold to 1 forces any non-empty county set across it.
    ``ProcessPoolExecutor`` is wrapped (not replaced with a mock) so the
    real multi-process code still runs; the returned list records each
    real instantiation and is the observable that proves the branch
    actually executed rather than the serial one.
    """
    import concurrent.futures

    from babylon.persistence import hex_hydrator

    monkeypatch.setattr(hex_hydrator, "_PARALLEL_POLYFILL_THRESHOLD", 1)

    calls: list[int] = []
    real_executor_cls = concurrent.futures.ProcessPoolExecutor

    def _spy_process_pool_executor(
        *args: object, **kwargs: object
    ) -> concurrent.futures.ProcessPoolExecutor:
        calls.append(1)
        return real_executor_cls(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(concurrent.futures, "ProcessPoolExecutor", _spy_process_pool_executor)
    return calls


def test_parallel_polyfill_matches_serial(_force_parallel_path: list[int]) -> None:
    """Parallel H3 polyfill must produce identical cell sets to serial.

    ``_force_parallel_path`` forces this fixture set across
    ``_PARALLEL_POLYFILL_THRESHOLD`` so the real ``ProcessPoolExecutor``
    branch runs; the call-count assertion confirms it actually did before
    trusting the cell-set comparison.
    """
    from babylon.persistence.hex_hydrator import (
        _polygons_to_hexes,
        _polygons_to_hexes_parallel,
    )

    polygons = {
        "01001": _make_square(-86.7, 32.6),
        "01003": _make_square(-88.1, 30.7),
        "01005": _make_square(-85.3, 31.9),
        "04001": _make_square(-112.1, 32.9),
        "04003": _make_square(-109.5, 31.4),
    }
    serial = {fips: _polygons_to_hexes(poly) for fips, poly in polygons.items()}
    parallel = _polygons_to_hexes_parallel(polygons, max_workers=2)
    assert _force_parallel_path, (
        "ProcessPoolExecutor was never instantiated; parallel branch did not run"
    )
    assert set(parallel.keys()) == set(serial.keys())
    for fips in serial:
        assert parallel[fips] == serial[fips], (
            f"Cell mismatch for county {fips}: "
            f"serial={len(serial[fips])} cells, "
            f"parallel={len(parallel[fips])} cells"
        )


def test_parallel_polyfill_preserves_county_keys(_force_parallel_path: list[int]) -> None:
    """Every input county must appear in the output, even if polyfill is empty.

    ``_force_parallel_path`` forces this fixture set across
    ``_PARALLEL_POLYFILL_THRESHOLD`` so the real ``ProcessPoolExecutor``
    branch runs rather than the serial fallback.
    """
    from babylon.persistence.hex_hydrator import _polygons_to_hexes_parallel

    polygons = {
        "01001": _make_square(-86.7, 32.6),
        "01003": _make_square(-88.1, 30.7),
    }
    result = _polygons_to_hexes_parallel(polygons, max_workers=2)
    assert _force_parallel_path, (
        "ProcessPoolExecutor was never instantiated; parallel branch did not run"
    )
    assert set(result.keys()) == set(polygons.keys())
    for fips, cells in result.items():
        assert isinstance(cells, set)
        assert len(cells) > 0, f"County {fips} produced 0 cells"


def test_parallel_polyfill_deterministic_across_runs(_force_parallel_path: list[int]) -> None:
    """Parallel polyfill must be deterministic — same input → same output.

    ``_force_parallel_path`` forces both runs across
    ``_PARALLEL_POLYFILL_THRESHOLD`` so determinism is checked against the
    real ``ProcessPoolExecutor`` branch rather than the serial fallback.
    """
    from babylon.persistence.hex_hydrator import _polygons_to_hexes_parallel

    polygons = {
        "01001": _make_square(-86.7, 32.6),
        "01003": _make_square(-88.1, 30.7),
        "04001": _make_square(-112.1, 32.9),
    }
    run1 = _polygons_to_hexes_parallel(polygons, max_workers=2)
    run2 = _polygons_to_hexes_parallel(polygons, max_workers=2)
    assert _force_parallel_path, (
        "ProcessPoolExecutor was never instantiated; parallel branch did not run"
    )
    assert run1 == run2, "Parallel polyfill is non-deterministic across runs"
