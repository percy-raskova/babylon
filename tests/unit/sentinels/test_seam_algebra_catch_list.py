"""The T1.1 day-one catch-list integration test (Unit 7, design §3.3 / §4 U7).

Design §3.3's table names five findings (F-EC-1, F-1, F-2, F-EC-2, F-3) that
T1.1 must discharge to green -- "each either fixed or carried as an
owner-gated declared exemption row ... with its rationale + recommended fix.
The mutation test for each check proves the check reds when its disposition
is reverted." U7's own acceptance criterion widens this to "the F-* ledger
test enumerates all five + wall-clock leaks and passes" -- this module is
that single, consolidated ledger, cutting ACROSS the individual per-check
test modules (``test_seam_algebra.py``'s F-EC-1 test,
``test_seam_algebra_gate_satisfaction.py``'s F-1/F-2 tests,
``test_seam_algebra_wallclock.py``'s six leak tests) that already prove each
finding's efficacy in isolation.

Each ledger entry is EITHER:

- a **red witness** — a live seam-algebra check that reds when the entry's
  exemption row is removed (F-EC-1 via ``check_disconnected_subsystems``,
  F-1/F-2 via ``check_gate_satisfaction``, the six wall-clock leaks via
  ``check_wallclock_call_sites``) -- these ALSO carry a declared exemption
  row (the "held open, not fixed" disposition every one of these five
  chose); or
- a **declared exemption/disposition row with a rationale** and no live
  check at all (F-EC-2's full L-ACC static check is R-EC-2, explicitly
  staged post-T1.1; F-3's "warn instead of raise" pattern has no generic
  scanner in this family) -- :data:`~babylon.sentinels.seam_algebra.registry.
  OPEN_FINDINGS_LEDGER` records these two using the SAME dated
  :class:`~babylon.sentinels.exemptions.SentinelExemption` shape, per the
  gate-governance ruling (2026-07-18: one exemption model, never a bespoke
  class), even though no checker ever calls :func:`~babylon.sentinels.
  exemptions.is_exempt` against them.

Every entry below satisfies BOTH halves where a live check exists, and just
the exemption half where it does not -- proving the "either/or" acceptance
criterion is met for the full 12-item catch list (5 named F-* findings, F-2
contributing two rows -- one per silent-skip site -- plus the 6 wall-clock
leaks), not asserted by name alone.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import pytest

from babylon.sentinels.exemptions import SentinelExemption
from babylon.sentinels.seam_algebra.checks import (
    check_disconnected_subsystems,
    check_gate_satisfaction,
    check_wallclock_call_sites,
)
from babylon.sentinels.seam_algebra.registry import (
    GATE_SATISFACTION_EXEMPTIONS,
    OPEN_FINDINGS_LEDGER,
    SEAM_ALGEBRA_EXEMPTIONS,
    WALLCLOCK_EXEMPTIONS,
)

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _CatchListEntry:
    """One day-one catch-list item: where its disposition row lives, and
    (optionally) the live check that reds when that row is removed.

    :ivar finding_id: Agent-legible label for this ledger row (matches the
        design §3.3 table's own finding IDs where one exists).
    :ivar exemptions: The declared exemption/disposition tuple this entry's
        row lives in.
    :ivar key: The exact :class:`SentinelExemption.key` identifying this
        entry's row within ``exemptions``.
    :ivar red_witness: A callable taking the REMAINING exemptions (this
        entry's own row removed) and returning the corresponding check's
        findings, or ``None`` when no live seam-algebra check enforces this
        finding (a disposition-only entry, per the class docstring).
    """

    finding_id: str
    exemptions: tuple[SentinelExemption, ...]
    key: tuple[str, ...]
    red_witness: Callable[[tuple[SentinelExemption, ...]], list[str]] | None


#: The full 12-item day-one catch list: 5 named F-* findings (design §3.3's
#: table, F-2 contributing two rows -- one per silent-skip site) + the 6
#: wall-clock leaks (T1.1 U7's own witnesses).
_LEDGER: Final[tuple[_CatchListEntry, ...]] = (
    _CatchListEntry(
        finding_id="F-EC-1",
        exemptions=SEAM_ALGEBRA_EXEMPTIONS,
        key=("construct", "anisotropic_observation_error"),
        red_witness=lambda remaining: check_disconnected_subsystems(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="F-1",
        exemptions=GATE_SATISFACTION_EXEMPTIONS,
        key=("gate", "run_audit_session_id"),
        red_witness=lambda remaining: check_gate_satisfaction(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="F-2 (financial_layer_distribution_calculator)",
        exemptions=GATE_SATISFACTION_EXEMPTIONS,
        key=("gate", "financial_layer_distribution_calculator"),
        red_witness=lambda remaining: check_gate_satisfaction(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="F-2 (vol2_circulation_vol2_step)",
        exemptions=GATE_SATISFACTION_EXEMPTIONS,
        key=("gate", "vol2_circulation_vol2_step"),
        red_witness=lambda remaining: check_gate_satisfaction(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="F-EC-2",
        exemptions=OPEN_FINDINGS_LEDGER,
        key=("finding", "F-EC-2"),
        red_witness=None,  # full L-ACC static check is R-EC-2, staged post-T1.1
    ),
    _CatchListEntry(
        finding_id="F-3",
        exemptions=OPEN_FINDINGS_LEDGER,
        key=("finding", "F-3"),
        red_witness=None,  # no generic raise-vs-warn scanner exists in this family
    ),
    _CatchListEntry(
        finding_id="wallclock: jsonl_recorder_session_dir_timestamp",
        exemptions=WALLCLOCK_EXEMPTIONS,
        key=("wallclock", "jsonl_recorder_session_dir_timestamp"),
        red_witness=lambda remaining: check_wallclock_call_sites(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="wallclock: jsonl_recorder_summary_ended_at",
        exemptions=WALLCLOCK_EXEMPTIONS,
        key=("wallclock", "jsonl_recorder_summary_ended_at"),
        red_witness=lambda remaining: check_wallclock_call_sites(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="wallclock: jsonl_recorder_export_zip_timestamp",
        exemptions=WALLCLOCK_EXEMPTIONS,
        key=("wallclock", "jsonl_recorder_export_zip_timestamp"),
        red_witness=lambda remaining: check_wallclock_call_sites(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="wallclock: tick_state_recorder_generated_at",
        exemptions=WALLCLOCK_EXEMPTIONS,
        key=("wallclock", "tick_state_recorder_generated_at"),
        red_witness=lambda remaining: check_wallclock_call_sites(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="wallclock: run_manifest_wallclock_start",
        exemptions=WALLCLOCK_EXEMPTIONS,
        key=("wallclock", "run_manifest_wallclock_start"),
        red_witness=lambda remaining: check_wallclock_call_sites(exemptions=remaining),
    ),
    _CatchListEntry(
        finding_id="wallclock: run_manifest_wallclock_end",
        exemptions=WALLCLOCK_EXEMPTIONS,
        key=("wallclock", "run_manifest_wallclock_end"),
        red_witness=lambda remaining: check_wallclock_call_sites(exemptions=remaining),
    ),
)


def test_the_ledger_covers_exactly_the_twelve_day_one_items() -> None:
    """WIRING: a deleted/renamed ledger entry above must fail this test even
    though every OTHER assertion in this module is entry-scoped. 12 = 5 named
    F-* findings (F-2 contributes two rows, one per silent-skip site) + 6
    wall-clock leaks."""
    assert len(_LEDGER) == 12
    assert len({entry.finding_id for entry in _LEDGER}) == 12


@pytest.mark.parametrize("entry", _LEDGER, ids=[entry.finding_id for entry in _LEDGER])
def test_catch_list_entry_has_a_declared_disposition_row_with_a_rationale(
    entry: _CatchListEntry,
) -> None:
    """Half one of the acceptance criterion: every entry has a dated,
    owner-approved exemption/disposition row, and that row's rationale is not
    blank (Constitution III.11 -- ``SentinelExemption`` itself already
    enforces this at construction; re-asserted here as the ledger's own
    positive control)."""
    exemption = next((e for e in entry.exemptions if e.key == entry.key), None)
    assert exemption is not None, f"{entry.finding_id}: no declared row for key {entry.key!r}"
    assert exemption.reason.strip(), f"{entry.finding_id}: exemption has a blank rationale"
    assert exemption.owner.strip(), f"{entry.finding_id}: exemption has a blank owner"
    assert exemption.date.strip(), f"{entry.finding_id}: exemption has a blank date"


@pytest.mark.parametrize(
    "entry",
    [entry for entry in _LEDGER if entry.red_witness is not None],
    ids=[entry.finding_id for entry in _LEDGER if entry.red_witness is not None],
)
def test_catch_list_entry_is_a_red_witness_when_its_row_is_reverted(
    entry: _CatchListEntry,
) -> None:
    """Half two of the acceptance criterion (where a live check exists):
    removing ONLY this entry's own exemption row reds that check --
    proving the disposition is load-bearing, not decorative."""
    assert entry.red_witness is not None  # narrows the type for mypy
    remaining = tuple(exemption for exemption in entry.exemptions if exemption.key != entry.key)
    findings = entry.red_witness(remaining)
    assert findings, f"{entry.finding_id}: removing its exemption did not red the live check"


def test_the_two_disposition_only_entries_have_no_live_check_by_design() -> None:
    """F-EC-2 and F-3 are the two entries this ledger declares
    disposition-only -- confirms the split is exactly {F-EC-2, F-3}, not a
    silently-widening set."""
    disposition_only = {entry.finding_id for entry in _LEDGER if entry.red_witness is None}
    assert disposition_only == {"F-EC-2", "F-3"}
