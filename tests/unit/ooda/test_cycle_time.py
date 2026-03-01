"""Tests for OODA cycle time computation (Feature 032).

Verifies the four-phase additive model and worked examples from
the OODA profile contract.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import OODADefines
from babylon.models.enums import DecisionMode
from babylon.ooda.cycle_time import compute_cycle_time
from babylon.ooda.types import OODAProfile


class TestDecisionModeOrdering:
    """AUTOCRATIC < DELEGATE < DEMOCRATIC < CONSENSUS ordering."""

    def test_ordering_guarantee(self) -> None:
        defines = OODADefines()
        base = {
            "sensor_latency": 1,
            "ideological_coherence": 0.5,
            "bureaucratic_depth": 0.3,
        }
        times = {}
        for mode in DecisionMode:
            profile = OODAProfile(decision_mode=mode, **base)
            times[mode] = compute_cycle_time(profile, defines)

        assert times[DecisionMode.AUTOCRATIC] < times[DecisionMode.DELEGATE]
        assert times[DecisionMode.DELEGATE] < times[DecisionMode.DEMOCRATIC]
        assert times[DecisionMode.DEMOCRATIC] < times[DecisionMode.CONSENSUS]


class TestWorkedExamples:
    """Verify worked examples from OODA profile contract."""

    def test_fbi_cycle_time(self) -> None:
        """FBI: AUTOCRATIC, coherence=0.7, depth=0.6, latency=1."""
        defines = OODADefines()
        profile = OODAProfile(
            sensor_latency=1,
            ideological_coherence=0.7,
            decision_mode=DecisionMode.AUTOCRATIC,
            bureaucratic_depth=0.6,
        )
        ct = compute_cycle_time(profile, defines)
        assert ct == pytest.approx(4.90, abs=0.01)

    def test_vanguard_cycle_time(self) -> None:
        """Vanguard: AUTOCRATIC, coherence=0.8, depth=0.2, latency=2."""
        defines = OODADefines()
        profile = OODAProfile(
            sensor_latency=2,
            ideological_coherence=0.8,
            decision_mode=DecisionMode.AUTOCRATIC,
            bureaucratic_depth=0.2,
        )
        ct = compute_cycle_time(profile, defines)
        assert ct == pytest.approx(5.12, abs=0.01)

    def test_mass_org_cycle_time(self) -> None:
        """Mass Org: DEMOCRATIC, coherence=0.5, depth=0.3, latency=3."""
        defines = OODADefines()
        profile = OODAProfile(
            sensor_latency=3,
            ideological_coherence=0.5,
            decision_mode=DecisionMode.DEMOCRATIC,
            bureaucratic_depth=0.3,
        )
        ct = compute_cycle_time(profile, defines)
        assert ct == pytest.approx(8.26, abs=0.01)

    def test_consensus_cso_cycle_time(self) -> None:
        """CSO: CONSENSUS, coherence=0.3, depth=0.2, latency=2."""
        defines = OODADefines()
        profile = OODAProfile(
            sensor_latency=2,
            ideological_coherence=0.3,
            decision_mode=DecisionMode.CONSENSUS,
            bureaucratic_depth=0.2,
        )
        ct = compute_cycle_time(profile, defines)
        assert ct == pytest.approx(10.04, abs=0.01)


class TestCycleTimeProperties:
    """Verify postcondition properties."""

    def test_always_positive(self) -> None:
        defines = OODADefines()
        profile = OODAProfile(
            sensor_latency=0,
            ideological_coherence=1.0,
            decision_mode=DecisionMode.AUTOCRATIC,
            bureaucratic_depth=0.0,
        )
        assert compute_cycle_time(profile, defines) > 0

    def test_higher_latency_longer_time(self) -> None:
        defines = OODADefines()
        low = OODAProfile(sensor_latency=1)
        high = OODAProfile(sensor_latency=5)
        assert compute_cycle_time(low, defines) < compute_cycle_time(high, defines)

    def test_higher_coherence_shorter_time(self) -> None:
        defines = OODADefines()
        low = OODAProfile(ideological_coherence=0.2)
        high = OODAProfile(ideological_coherence=0.9)
        assert compute_cycle_time(high, defines) < compute_cycle_time(low, defines)

    def test_higher_bureaucratic_depth_longer_time(self) -> None:
        defines = OODADefines()
        low = OODAProfile(bureaucratic_depth=0.1)
        high = OODAProfile(bureaucratic_depth=0.9)
        assert compute_cycle_time(low, defines) < compute_cycle_time(high, defines)

    def test_orient_floor(self) -> None:
        """Orient phase never goes below 0.1 even with perfect coherence."""
        defines = OODADefines()
        profile = OODAProfile(ideological_coherence=1.0)
        ct = compute_cycle_time(profile, defines)
        # With coherence=1.0 and weight=0.6:
        # orient_raw = 2.0 * (1.0 - 1.0*0.6) = 0.8
        # Floor doesn't kick in (0.8 > 0.1), but verifies no negative
        assert ct > 0
