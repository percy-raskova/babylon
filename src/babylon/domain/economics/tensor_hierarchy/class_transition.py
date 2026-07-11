"""ClassTransitionMatrix computation and stub data source.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Implements:
- DefaultClassTransitionComputer: Computes stationary distribution and
  performs class aggregation on ClassTransitionMatrix tensors.
- DefaultClassTransitionSource: Stub returning NoDataSentinel (PSID data
  loader deferred pending constitutional amendment US5).

See Also:
    :mod:`babylon.domain.economics.tensor_hierarchy.types`: ClassTransitionMatrix,
        StationaryDistribution types.
    :mod:`babylon.domain.economics.tensor_hierarchy.protocols`: ClassTransitionSource
        protocol.
"""

from __future__ import annotations

import logging

import numpy as np

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.tensor_hierarchy.types import (
    ClassTransitionMatrix,
    StationaryDistribution,
)

logger = logging.getLogger(__name__)

# Reason used in all NoDataSentinel instances from this stub loader
_STUB_REASON = "PSID data source pending constitutional amendment (US5 deferred loader)"


class DefaultClassTransitionComputer:
    """Computes stationary distribution and class aggregation for transition matrices.

    The stationary distribution pi satisfies the fixed-point equation:

    .. math::

        \\pi P = \\pi, \\quad \\sum_i \\pi_i = 1

    Computed as the dominant left eigenvector of P (equivalently, the
    right eigenvector of P^T with eigenvalue = 1.0).

    Class aggregation uses block-sum reduction: rows and columns are summed
    within target groups, then re-normalized to preserve row stochasticity.

    Example:
        >>> computer = DefaultClassTransitionComputer()
        >>> pi = computer.stationary_distribution(ctm)
        >>> assert abs(pi.distribution.sum() - 1.0) < 1e-9
    """

    def stationary_distribution(self, ctm: ClassTransitionMatrix) -> StationaryDistribution:
        """Compute long-run class distribution from the transition matrix.

        Uses eigendecomposition of P^T to find the eigenvector corresponding
        to eigenvalue 1.0. Normalizes to sum = 1.0.

        Args:
            ctm: ClassTransitionMatrix with row-stochastic transition matrix.

        Returns:
            StationaryDistribution with pi[i] = long-run probability of class i.

        Raises:
            numpy.linalg.LinAlgError: If eigendecomposition fails.
        """
        p = ctm.transition_matrix
        eigenvalues, eigenvectors = np.linalg.eig(p.T)

        # Find the eigenvalue closest to 1.0
        idx = int(np.argmin(np.abs(eigenvalues - 1.0)))
        pi = np.real(eigenvectors[:, idx])

        # Ensure all elements are non-negative (numerical noise can make tiny
        # values slightly negative)
        pi = np.clip(pi, 0.0, None)

        # Normalize to sum = 1.0
        total = pi.sum()
        if total > 0.0:
            pi = pi / total
        else:
            # Degenerate case: fall back to uniform distribution
            n = ctm.n_classes
            pi = np.ones(n, dtype=np.float64) / n

        return StationaryDistribution(
            period=ctm.period,
            classes=ctm.classes,
            distribution=pi,
        )

    def aggregate_classes(
        self,
        ctm: ClassTransitionMatrix,
        mapping: dict[str, str],
    ) -> ClassTransitionMatrix:
        """Produce a coarser transition matrix by merging class groups.

        For each target class, the aggregated row is computed as a
        weighted average of the source rows, where weights are the
        stationary distribution masses of the merged classes.

        The aggregation algorithm:
        1. Group source indices by target class label.
        2. For each (orig_target, dest_target) pair, sum the flow:
           flow[orig_target, dest_target] = sum of P[i, j] for all i
           mapped to orig_target and j mapped to dest_target, weighted
           by stationary mass of each i.
        3. Re-normalize rows to sum to 1.0.

        Areas not present in mapping are excluded.

        Args:
            ctm: Source ClassTransitionMatrix.
            mapping: Dict mapping source class name -> target class name.

        Returns:
            ClassTransitionMatrix with aggregated classes (row-stochastic).
        """
        targets = sorted(set(mapping.values()))
        target_to_idx: dict[str, int] = {t: i for i, t in enumerate(targets)}
        n_targets = len(targets)

        # Map source indices to target indices
        src_to_tgt: dict[int, int] = {}
        for src_idx, src_class in enumerate(ctm.classes):
            tgt = mapping.get(src_class)
            if tgt is not None and tgt in target_to_idx:
                src_to_tgt[src_idx] = target_to_idx[tgt]

        # Compute stationary weights for source classes
        pi = self.stationary_distribution(ctm)
        weights = pi.distribution

        # Accumulate weighted flows into aggregated matrix
        agg_matrix = np.zeros((n_targets, n_targets), dtype=np.float64)
        agg_weights = np.zeros(n_targets, dtype=np.float64)

        for src_idx in range(ctm.n_classes):
            orig_tgt = src_to_tgt.get(src_idx)
            if orig_tgt is None:
                continue
            w = weights[src_idx]
            agg_weights[orig_tgt] += w
            for dst_idx in range(ctm.n_classes):
                dest_tgt = src_to_tgt.get(dst_idx)
                if dest_tgt is None:
                    continue
                agg_matrix[orig_tgt, dest_tgt] += w * ctm.transition_matrix[src_idx, dst_idx]

        # Re-normalize rows by accumulated weight
        for i in range(n_targets):
            row_weight = agg_weights[i]
            if row_weight > 0.0:
                agg_matrix[i] /= row_weight

        # Ensure exact row-stochasticity (clean up floating point drift)
        row_sums = agg_matrix.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1.0)
        agg_matrix = agg_matrix / row_sums

        return ClassTransitionMatrix(
            period=ctm.period,
            classes=targets,
            transition_matrix=agg_matrix,
        )


class DefaultClassTransitionSource:
    """Stub data source for ClassTransitionMatrix (PSID loader deferred).

    Returns NoDataSentinel for all queries. The production implementation
    requires PSID (Panel Study of Income Dynamics) data, which requires a
    constitutional amendment for US5 to proceed.

    Example:
        >>> source = DefaultClassTransitionSource()
        >>> matrix = source.get_transition_matrix((2015, 2020))
        >>> bool(matrix)  # NoDataSentinel is falsy
        False
    """

    def get_transition_matrix(self, period: tuple[int, int]) -> NoDataSentinel:
        """Return NoDataSentinel — PSID data loader is deferred.

        Args:
            period: (start_year, end_year) transition period.

        Returns:
            NoDataSentinel with reason explaining the deferred loader.
        """
        return NoDataSentinel("national", period[0], _STUB_REASON)

    def get_stationary_distribution(self, period: tuple[int, int]) -> NoDataSentinel:
        """Return NoDataSentinel — no transition matrix available.

        Args:
            period: (start_year, end_year) transition period.

        Returns:
            NoDataSentinel with reason explaining the deferred loader.
        """
        return NoDataSentinel("national", period[0], _STUB_REASON)


__all__ = [
    "DefaultClassTransitionComputer",
    "DefaultClassTransitionSource",
]
