"""Sensor 1 (continuity) coverage-gate tests — and its efficacy proof.

Two things are verified here, matching the Seam Observatory's own discipline
(a green sensor is worthless unless it is *shown* to red on a real defect):

1. The shipped registry reconciles with ``MAP_METRIC_PROPERTIES`` — both the
   in-process check and the CLI ``--check`` idiom (mirrors
   ``tests/unit/config/test_constants_sync.py``).
2. The sensor is **not vacuous**: dropping a real map metric from an injected
   registry, or injecting a phantom one, is caught loudly and names the metric.
   This is the TDD red phase for Sensor 1 (Constitution III.11 / the build
   plan's "sensor efficacy proof").
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from babylon.sentinels._ast import literal_dict_keys, literal_str_tuple, tick_write_set
from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.seam import checks as sensor1
from babylon.sentinels.seam.registry import SEAM_REGISTRY
from babylon.sentinels.seam.types import LivenessClass, SeamEntry, SeamScope

pytestmark = pytest.mark.unit

# The family CLI dispatches ``sentinel_check.py <sensor> --check`` — no sys.path
# hack, because the check logic lives in the importable ``babylon.sentinels``
# package (only the thin subprocess-idiom test needs the tool path).
_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
_TOOL_PATH = _TOOLS_DIR / "sentinel_check.py"


def _map_entry(wire_key: str) -> SeamEntry:
    """A minimal valid MAP-scope registry row for a given wire key."""
    return SeamEntry(
        payload=wire_key,
        wire_keys=(wire_key,),
        scope=SeamScope.MAP,
        owner_layer="test",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
    )


def test_ast_helper_extracts_the_map_contract_literal() -> None:
    """The static extractor reads MAP_METRIC_PROPERTIES without importing web/."""
    keys = literal_str_tuple(sensor1._MAP_CONTRACT_PATH, sensor1._MAP_CONTRACT_VAR)
    assert "imperial_rent" in keys
    assert len(keys) >= 10


def test_real_registry_reconciles_with_map_contract() -> None:
    """The shipped registry's MAP-scope keys equal MAP_METRIC_PROPERTIES (green)."""
    assert sensor1.check_map_metrics() == []


def test_dropped_map_metric_is_flagged() -> None:
    """Removing a real map metric from the registry reds the sensor (efficacy)."""
    broken = tuple(
        e
        for e in SEAM_REGISTRY
        if not (e.scope is SeamScope.MAP and "imperial_rent" in e.wire_keys)
    )
    assert len(broken) == len(SEAM_REGISTRY) - 1  # exactly one row removed

    violations = sensor1.check_map_metrics(registry=broken)

    assert len(violations) == 1
    assert "imperial_rent" in violations[0]
    assert "not" in violations[0].lower()


def test_phantom_map_metric_is_flagged() -> None:
    """A registry map metric the contract never emits is flagged as a phantom."""
    with_phantom = (*SEAM_REGISTRY, _map_entry("bogus_metric"))

    violations = sensor1.check_map_metrics(registry=with_phantom)

    assert len(violations) == 1
    assert "bogus_metric" in violations[0]
    assert "phantom" in violations[0].lower()


def test_cli_check_exits_zero_on_real_registry() -> None:
    """``sentinel_check.py seam --check`` exits 0 today (CI fast-gate idiom)."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "seam", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Sensor 1 reds against the shipped registry:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_missing_source_is_infrastructure_error_not_violation() -> None:
    """A missing/unparseable source raises SeamCheckError (exit 2), never a silent pass."""
    with pytest.raises(SentinelCheckError):
        literal_str_tuple(Path("/nonexistent/does_not_exist.py"), "X")


# --- Phase 2: tick_* payload existence (gating) + coverage/event advisories ---


def test_tick_write_set_extracts_engine_attrs() -> None:
    """The static tick write-set extractor reads the engine's update_node kwargs."""
    write_set = tick_write_set(sensor1._GRAPH_BRIDGE_PATH)
    assert "tick_phi_hour" in write_set
    assert "tick_median_wage" in write_set
    assert len(write_set) >= 30  # the engine stamps ~30 tick_* attrs per territory


def test_registered_tick_payloads_exist_in_engine() -> None:
    """Every shipped tick_* payload is actually written by the engine (green)."""
    assert sensor1.check_tick_payloads_exist() == []


def test_dead_tick_payload_is_flagged() -> None:
    """A registry row citing a non-existent engine tick attr reds the gate (efficacy)."""
    dead = SeamEntry(
        payload="tick_does_not_exist",
        wire_keys=("phantom",),
        scope=SeamScope.MAP,
        owner_layer="test",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
    )
    violations = sensor1.check_tick_payloads_exist(registry=(dead,))
    assert len(violations) == 1
    assert "tick_does_not_exist" in violations[0]


def test_tick_coverage_advisory_lists_unregistered_engine_attrs() -> None:
    """The coverage advisory surfaces engine tick_* writes with no registry row.

    Wave 2 Gap-1 registered ``tick_median_wage`` (territory.tick_median_wage);
    Wave 2 Round 2 (owner ruling 1) wires the real throughput calculator and
    registers ``tick_throughput_position``/``tick_supply_chain_depth`` too
    (territory.throughput_position/territory.supply_chain_depth) — they have
    graduated out of the advisory list, same as tick_median_wage before them.
    """
    findings = sensor1.check_tick_coverage()
    joined = "\n".join(findings)
    assert "tick_throughput_position" not in joined  # now registered (territory scope)
    assert "tick_supply_chain_depth" not in joined  # now registered (territory scope)
    assert "tick_median_wage" not in joined  # now registered (territory.tick_median_wage)
    assert "tick_phi_hour" not in joined  # registered (map.imperial_rent) — excluded


def test_severity_vocabulary_is_clean_and_gates() -> None:
    """After the drift repair, every _EVENT_SEVERITY key is a real EventType (gating)."""
    assert sensor1.check_severity_vocabulary() == []


def test_severity_vocabulary_reds_on_non_eventtype_key(tmp_path: Path) -> None:
    """A regression that keys _EVENT_SEVERITY on a non-EventType string reds the gate."""
    fake = tmp_path / "fake_bridge.py"
    fake.write_text(
        '_EVENT_SEVERITY = {"economic_crisis": "critical", "totally_fake_event": "warning"}\n'
    )
    violations = sensor1.check_severity_vocabulary(path=fake)
    assert len(violations) == 1
    assert "totally_fake_event" in violations[0]


def test_narrator_vocabulary_advisory_flags_unreachable_templates() -> None:
    """The narrator advisory still surfaces the crafted-but-unreachable templates."""
    findings = sensor1.check_narrator_vocabulary()
    assert any("ecological_collapse" in f for f in findings)  # a crafted endgame template


def test_event_coverage_advisory_reports_converter_gap() -> None:
    """The coverage advisory reports EventTypes dropped before the wire."""
    findings = sensor1.check_event_coverage()
    assert any("_convert_bus_event_to_pydantic" in f and "drop to None" in f for f in findings)


def test_dict_keys_helper_reads_narrator_templates() -> None:
    """The dict-key extractor reads a real module-level dict literal."""
    keys = literal_dict_keys(sensor1._NARRATOR_PATH, "_TEMPLATES")
    assert "uprising" in keys


def test_cli_still_exits_zero_despite_advisories() -> None:
    """Advisory findings print but MUST NOT gate — the CLI still exits 0."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "seam", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "SEAM ADVISORY" in result.stderr  # advisories are being emitted
    assert "advisory findings above" in result.stdout  # and summarized, non-gating


def test_survival_calculus_inspector_rows_are_registered() -> None:
    """Wave 2 W2.5b (owner ruling 3): p_acquiescence/p_revolution
    (SurvivalSystem.step, survival.py:143) get INSPECTOR-scope rows —
    real every tick, so MUST_BE_LIVE (follows the W1.4 inspector-row
    precedent)."""
    inspector_wire_keys = {e.wire_keys[0] for e in SEAM_REGISTRY if e.scope is SeamScope.INSPECTOR}
    assert {"p_acquiescence", "p_revolution"} <= inspector_wire_keys

    entries = {
        e.wire_keys[0]: e
        for e in SEAM_REGISTRY
        if e.scope is SeamScope.INSPECTOR and e.wire_keys[0] in ("p_acquiescence", "p_revolution")
    }
    for entry in entries.values():
        assert entry.liveness_class is LivenessClass.MUST_BE_LIVE
