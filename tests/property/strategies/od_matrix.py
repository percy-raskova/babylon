"""Hypothesis strategy for generating sparse OD matrices.

Spec 053 T012: Generates row-stochastic ``scipy.sparse.csr_matrix`` instances
for property-based tests of LODES wage circulation (INV-003 / contracts/
circulation_v.md).

Four flavors:
    - ``identity``    — N×N identity (no redistribution; per-hex v unchanged).
    - ``empty_rows``  — at least one row is entirely zero (some hexes have no
      outflow); circulation must still conserve sum(v).
    - ``dense``       — every row has multiple non-zero entries.
    - ``random``      — Bernoulli mask with non-negative random weights.

At large N, density defaults to ≤0.01 to match empirical LODES sparsity and
keep matrix construction tractable.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy
from scipy import sparse


def _row_normalize(matrix: sparse.csr_matrix) -> sparse.csr_matrix:
    """Normalize each row to sum to 1.0; rows that sum to 0 stay zero."""
    matrix = matrix.tocsr().copy()
    row_sums = np.array(matrix.sum(axis=1)).flatten()
    nonzero = row_sums > 0
    inv = np.zeros_like(row_sums)
    inv[nonzero] = 1.0 / row_sums[nonzero]
    diag = sparse.diags(inv)
    return (diag @ matrix).tocsr()


def _identity_strategy(n: int) -> SearchStrategy[sparse.csr_matrix]:
    return st.just(sparse.eye(n, dtype=np.float64, format="csr"))


@st.composite
def _random_strategy(
    draw: st.DrawFn,
    n: int,
    density: float,
    *,
    force_zero_row: bool = False,
    force_dense_rows: bool = False,
) -> sparse.csr_matrix:
    seed = draw(st.integers(min_value=0, max_value=2**31 - 1))
    rng = np.random.default_rng(seed)
    # Bernoulli mask
    nnz_target = max(1, int(n * n * density))
    rows = rng.integers(0, n, size=nnz_target)
    cols = rng.integers(0, n, size=nnz_target)
    weights = rng.uniform(0.0, 1.0, size=nnz_target)

    if force_dense_rows and n > 1:
        # Ensure every row has ≥2 non-zero entries by adding fill-in
        for r in range(n):
            extra_cols = rng.integers(0, n, size=2)
            extra_w = rng.uniform(0.1, 1.0, size=2)
            rows = np.concatenate([rows, [r, r]])
            cols = np.concatenate([cols, extra_cols])
            weights = np.concatenate([weights, extra_w])

    matrix = sparse.coo_matrix((weights, (rows, cols)), shape=(n, n)).tocsr()
    matrix.sum_duplicates()

    if force_zero_row and n > 1:
        # Pick a random row and zero it out (use lil for efficient row mutation,
        # then convert back to csr).
        zero_row = int(rng.integers(0, n))
        lil = matrix.tolil()
        lil.rows[zero_row] = []
        lil.data[zero_row] = []
        matrix = lil.tocsr()

    return _row_normalize(matrix)


def od_matrix_strategy(
    n: int,
    *,
    density: float | None = None,
    flavor: Literal["identity", "empty_rows", "dense", "random"] = "random",
) -> SearchStrategy[sparse.csr_matrix]:
    """Generate row-stochastic sparse CSR OD matrices.

    Args:
        n: Matrix dimension (typically equal to the paired HexGrid's hex count).
        density: Bernoulli density for ``random``/``empty_rows``/``dense``.
            Default scales as ``min(0.05, 100 / n)`` so large matrices stay
            tractable (~100 non-zeros per row at N=2000+, matching LODES).
        flavor: Distribution shape:
            - ``identity``    — identity matrix (no redistribution)
            - ``empty_rows``  — at least one zero row
            - ``dense``       — every row has ≥2 non-zero entries
            - ``random``      — pure Bernoulli mask

    Returns:
        A Hypothesis ``SearchStrategy[scipy.sparse.csr_matrix]`` producing
        row-stochastic matrices (each non-zero row sums to 1.0 within float
        precision).
    """
    if flavor == "identity":
        return _identity_strategy(n)
    if density is None:
        density = min(0.05, 100.0 / max(n, 1))
    return _random_strategy(
        n,
        density,
        force_zero_row=(flavor == "empty_rows"),
        force_dense_rows=(flavor == "dense"),
    )
