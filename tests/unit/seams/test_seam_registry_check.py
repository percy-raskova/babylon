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

from babylon.seams.registry import SEAM_REGISTRY
from babylon.seams.types import LivenessClass, SeamEntry, SeamScope

# Tools are not a package on the pytest path (pythonpath = src, web); add the
# dir like the other tools/ tests (tests/unit/tools/test_dense_goldens.py).
_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(_TOOLS_DIR))

import seam_registry_check as sensor1  # type: ignore[import-not-found]  # noqa: E402

pytestmark = pytest.mark.unit

_TOOL_PATH = _TOOLS_DIR / "seam_registry_check.py"


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
    keys = sensor1._literal_str_tuple(sensor1._MAP_CONTRACT_PATH, sensor1._MAP_CONTRACT_VAR)
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
    """``seam_registry_check.py --check`` exits 0 today (CI fast-gate idiom)."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "--check"],
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
    with pytest.raises(sensor1.SeamCheckError):
        sensor1._literal_str_tuple(Path("/nonexistent/does_not_exist.py"), "X")


# --- Phase 2: tick_* payload existence (gating) + coverage/event advisories ---


def test_tick_write_set_extracts_engine_attrs() -> None:
    """The static tick write-set extractor reads the engine's update_node kwargs."""
    write_set = sensor1._tick_write_set(sensor1._GRAPH_BRIDGE_PATH)
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
    """The coverage advisory surfaces engine tick_* writes with no registry row."""
    findings = sensor1.check_tick_coverage()
    joined = "\n".join(findings)
    assert "tick_median_wage" in joined  # a real unregistered engine attr
    assert "tick_phi_hour" not in joined  # registered (map.imperial_rent) — excluded


def test_event_tables_advisory_flags_non_eventtype_vocabulary() -> None:
    """The event advisory catches templates/severity keys that are not EventTypes."""
    findings = sensor1.check_event_tables()
    # A dead narrator template key and the bus->pydantic coverage gap.
    assert any("_TEMPLATES" in f and "eviction_pipeline" in f for f in findings)
    assert any("_convert_bus_event_to_pydantic" in f and "drop to None" in f for f in findings)


def test_dict_keys_helper_reads_narrator_templates() -> None:
    """The dict-key extractor reads a real module-level dict literal."""
    keys = sensor1._literal_dict_keys(sensor1._NARRATOR_PATH, "_TEMPLATES")
    assert "uprising" in keys


def test_cli_still_exits_zero_despite_advisories() -> None:
    """Advisory findings print but MUST NOT gate — the CLI still exits 0."""
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, trusted path
        [sys.executable, str(_TOOL_PATH), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "SEAM ADVISORY" in result.stderr  # advisories are being emitted
    assert "advisory findings above" in result.stdout  # and summarized, non-gating
