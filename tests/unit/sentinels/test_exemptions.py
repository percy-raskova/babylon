"""Tests for the shared, unified sentinel-exemption record.

``babylon.sentinels.exemptions`` is the ONE convention every gate in the
family uses to hold a known finding open (owner ruling, gate-governance
task, 2026-07-18) — replacing five copy-pasted ``XxxExemption`` Pydantic
classes (``InertExemption``, ``UnconsumedExemption``,
``MaskedArithmeticExemption``, ``AggregationExemption``,
``FogContainmentExemption``) and the vocabulary sentinel's un-structured
``(path, literal)``/``(path, node_type, attribute)`` tuple sets, which
carried a reason only as a source comment, never as validated data.

Three tiers:

- **Shape teeth** — a malformed row (blank field, bad date, an
  unanchored ``tracking_task``) must FAIL at construction, never be
  silently accepted.
- **Exact-match teeth** — :func:`~babylon.sentinels.exemptions.is_exempt`
  matches on the FULL ``key`` tuple only. A new violation that merely
  resembles an exempted one (same shape, different symbol; or the same
  symbol checked under a DIFFERENT rule/kind) must NOT be silently
  absorbed.
- **Staleness is informational, not a time bomb** — see
  :func:`~babylon.sentinels.exemptions.stale_exemptions`: nothing here
  fails a build on a calendar date; a future gate MAY choose to print the
  advisory, never gate on it (a hard-coded expiry would be exactly the
  "arbitrary date CI breakage" the governance task explicitly warns
  against).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.sentinels.exemptions import SentinelExemption, is_exempt, stale_exemptions

pytestmark = pytest.mark.unit


def _exemption(**overrides: object) -> SentinelExemption:
    fields: dict[str, object] = {
        "key": ("computed_field", "reification_buffer"),
        "reason": "wiring the consumer is baseline-moving, tracked separately",
        "owner": "Persephone Raskova",
        "date": "2026-07-18",
        "tracking_task": "#42",
    }
    fields.update(overrides)
    return SentinelExemption(**fields)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Shape teeth -- malformed rows FAIL at construction
# ---------------------------------------------------------------------------


def test_well_formed_exemption_constructs_cleanly() -> None:
    exemption = _exemption()
    assert exemption.key == ("computed_field", "reification_buffer")
    assert exemption.tracking_task == "#42"


def test_empty_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="key"):
        _exemption(key=())


def test_blank_key_part_is_rejected() -> None:
    with pytest.raises(ValidationError, match="key"):
        _exemption(key=("computed_field", "   "))


@pytest.mark.parametrize("field_name", ["reason", "owner", "date", "tracking_task"])
def test_blank_scalar_field_is_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        _exemption(**{field_name: "   "})


@pytest.mark.parametrize("bad_date", ["2026/07/18", "18-07-2026", "not-a-date", "2026-7-18", ""])
def test_non_iso_date_is_rejected(bad_date: str) -> None:
    with pytest.raises(ValidationError, match="date"):
        _exemption(date=bad_date)


@pytest.mark.parametrize(
    "bad_task",
    [
        "fix this someday",  # prose, no real anchor
        "task 42",  # missing the '#'
        "see the audit report",
        "TODO",
    ],
)
def test_unanchored_tracking_task_is_rejected(bad_task: str) -> None:
    with pytest.raises(ValidationError, match="tracking_task"):
        _exemption(tracking_task=bad_task)


@pytest.mark.parametrize("good_task", ["#42", "#1", "N/A (permanent by design)", "n/a"])
def test_anchored_tracking_task_is_accepted(good_task: str) -> None:
    assert _exemption(tracking_task=good_task).tracking_task == good_task


def test_exemption_is_frozen() -> None:
    exemption = _exemption()
    with pytest.raises(ValidationError):
        exemption.owner = "someone else"  # type: ignore[misc]


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SentinelExemption(
            key=("computed_field", "reification_buffer"),
            reason="x",
            owner="x",
            date="2026-07-18",
            tracking_task="#42",
            name="reification_buffer",  # legacy field name -- must not silently work
        )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Exact-match teeth -- is_exempt() never absorbs a lookalike
# ---------------------------------------------------------------------------


def test_is_exempt_matches_the_exact_key() -> None:
    exemptions = (_exemption(),)
    assert is_exempt(("computed_field", "reification_buffer"), exemptions)


def test_is_exempt_does_not_absorb_a_different_symbol_same_kind() -> None:
    """Same shape ('computed_field', <name>), a DIFFERENT name -- must still fail."""
    exemptions = (_exemption(),)
    assert not is_exempt(("computed_field", "some_other_unread_field"), exemptions)


def test_is_exempt_does_not_absorb_the_same_symbol_different_kind() -> None:
    """The exact bug latent in the pre-unification inert sentinel: a bare
    ``name``-keyed set exempted BOTH ``DECLARED_STORES`` and
    ``DECLARED_PRODUCERS`` rows sharing one name. Tagging the key with its
    *kind* ('store' vs 'producer') closes that hole."""
    exemptions = (_exemption(key=("store", "reification_buffer")),)
    assert not is_exempt(("producer", "reification_buffer"), exemptions)


def test_is_exempt_false_on_empty_registry() -> None:
    assert not is_exempt(("computed_field", "reification_buffer"), ())


# ---------------------------------------------------------------------------
# Staleness -- informational surfacing, no hard-coded expiry
# ---------------------------------------------------------------------------


def test_stale_exemptions_flags_rows_older_than_threshold() -> None:
    old = _exemption(date="2020-01-01")
    fresh = _exemption(key=("computed_field", "other"), date="2026-07-18")
    flagged = stale_exemptions((old, fresh), as_of="2026-07-18", max_age_days=90)
    assert flagged == (old,)


def test_stale_exemptions_empty_when_nothing_old() -> None:
    fresh = _exemption(date="2026-07-18")
    assert stale_exemptions((fresh,), as_of="2026-07-18", max_age_days=90) == ()
