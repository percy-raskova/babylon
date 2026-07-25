"""Behavioral contract for the three BDD assertion layers (Task 11)."""

import pytest

from babylon.projection.view_models import EconomyView
from babylon.tui.shell.bdd.assertions import (
    CoverageError,
    InvariantError,
    RenderError,
    assert_coverage,
    assert_invariants,
    assert_render,
)
from babylon.tui.shell.bdd.harness import TutorialStep


def _econ(**overrides) -> EconomyView:
    base = {"economy_id": "USA", "verified_tick": 1}
    base.update(overrides)
    return EconomyView(**base)


def test_coverage_reds_when_a_verb_is_never_exercised():
    steps = [TutorialStep(verb="educate", expect_text=())]
    with pytest.raises(CoverageError) as e:
        assert_coverage(steps)
    assert "attack" in str(e.value)  # names a missing verb


def test_render_layer_matches_expected_text():
    assert_render("FUNDAMENTAL THEOREM: wage balance +0.25", ("wage balance +0.25",))
    with pytest.raises(RenderError):
        assert_render("nothing here", ("wage balance +0.25",))


def test_invariants_catch_negative_phi_component():
    good = _econ(
        phi_unequal_exchange=10.0,
        phi_reproduction=5.0,
        phi_domestic=3.0,
        phi_decomposition_total=18.0,
    )
    assert_invariants(good, replay_hashes=["abc", "abc", "abc"])
    with pytest.raises(InvariantError):
        assert_invariants(_econ(phi_unequal_exchange=-1.0), replay_hashes=["abc", "abc"])


def test_invariants_catch_broken_phi_closure():
    with pytest.raises(InvariantError):
        assert_invariants(
            _econ(
                phi_unequal_exchange=10.0,
                phi_reproduction=5.0,
                phi_domestic=3.0,
                phi_decomposition_total=99.0,  # violates total = UE + repro + dom
            ),
            replay_hashes=["abc"],
        )


def test_invariants_catch_replay_hash_drift():
    with pytest.raises(InvariantError):
        assert_invariants(_econ(), replay_hashes=["abc", "def"])


def test_invariants_accept_honest_absence():
    # All-None Φ feeds are an absence, not a violation.
    assert_invariants(_econ(), replay_hashes=["abc", "abc"])
