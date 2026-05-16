"""Unit tests for Bug B — employment_proxy unit fix /52 → /12 (spec-066 US4).

Spec: 066-marx-coherence-fixes (T055).

BLS QCEW reports monthly average employment (a stock, not a flow).
Dividing by 52 weeks treats stock as flow and undercounts by ~4.3x.
The correct division is by 12 months for annual average.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


def test_divides_by_12_not_52() -> None:
    """T055: hex_hydrator computes employment_proxy = SUM(employment) / 12, not / 52.

    Given a mocked QCEW employment SUM of 1,200,000 for Wayne County, the
    hydrator output should be 100,000 (= 1,200,000 / 12), not ~23,077
    (= 1,200,000 / 52).
    """
    pytest.skip("WIP — implemented in spec-066 US4 phase (T058 fixes hex_hydrator.py:~410)")
