"""Capital Volume II: Circulation of Capital.

Feature: 023-capital-volume-ii

Models capital as a process (M-C-P-C'-M') rather than a static snapshot.
Adds turnover time, fixed/circulating capital decomposition, reproduction
schema balance conditions, inventory/realization tracking, circulation
costs classification, and integrated crisis detection.

See Also:
    :mod:`babylon.economics.tensor`: ValueTensor4x3 (Volume I production)
    :mod:`babylon.economics.tick`: TickDynamicsSystem pipeline integration
    :mod:`babylon.economics.crisis`: TRPF crisis mechanics (Feature 018)
"""
