#!/usr/bin/env python3
"""Fog-containment sentinel probe: no political field escapes an out-of-reach mask.

The dynamic harness for ``babylon.sentinels.fog`` (Track 1 Task 10). The
sentinel package is layer 0.5 and may not import ``game.fog.filter`` (a
``web.game.*`` module — ``babylon.*`` must never depend on ``web``, only the
reverse), so the Hypothesis property test lives here, the same split
``tools/aggregation_symmetry_probe.py``/``tools/partition_probe.py`` use for
their own web/engine-touching harnesses.

**The property.** For a node id NOT in ``reach`` (organizing reach), with an
EMPTY :class:`~game.fog.ledger.IntelLedger` (guaranteeing
:func:`~game.fog.ledger.read_intel` always returns tier ``"unknown"``),
:func:`game.fog.filter.apply_fog` must mask EVERY political field present in
the payload to ``None`` — regardless of the field's original value's shape
(float, int, string, bool, or already-``None``). Hypothesis generates the
``(field subset, arbitrary per-field value, node id)`` combination; a
single escaping field is a gating violation.

This is deliberately narrower than the full ``apply_fog`` contract (it does
not re-test the reach-bypass or ledger-exact/-approximate paths — those are
already pinned by ``tests/unit/web/fog/test_filter.py``'s example tests):
the property that is genuinely under-tested by hand-written examples is
"does EVERY field, of EVERY shape, actually get masked", which is exactly
what property-based generation is for.

Run directly::

    poetry run python tools/fog_containment_probe.py --check

or through the family CLI: ``poetry run python tools/sentinel_check.py fog
--check``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WEB_DIR = _REPO_ROOT / "web"
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor  # noqa: E402
from babylon.sentinels.exemptions import is_exempt  # noqa: E402
from babylon.sentinels.fog.registry import FOG_CONTAINMENT_EXEMPTIONS  # noqa: E402

_MAX_EXAMPLES = 200

#: Arbitrary per-field values a real payload might carry — floats (the
#: numeric political fields: heat/agitation/solidarity_index/cadre_level/
#: cohesion/consciousness_tendency-as-score), strings (dominant_class/
#: colonial_stance/dominant_community), booleans, ints, and None (a field
#: already honestly absent before fog ever touches it).
_VALUE_STRATEGY = st.one_of(
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
    st.text(max_size=20),
    st.integers(min_value=-1_000_000, max_value=1_000_000),
    st.booleans(),
    st.none(),
)


@st.composite
def _payload_case(draw: st.DrawFn) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Draw ``(payload, fields)`` — a non-empty subset of the org-political
    field family, each mapped to an arbitrary value, with any declared
    exemption removed from consideration.
    """
    from game.fog.filter import ORG_POLITICAL_FIELDS

    candidates = [
        f
        for f in ORG_POLITICAL_FIELDS
        if not is_exempt(("political_field", f), FOG_CONTAINMENT_EXEMPTIONS)
    ]
    fields = tuple(
        draw(
            st.lists(st.sampled_from(candidates), unique=True, min_size=1, max_size=len(candidates))
        )
    )
    payload = {field: draw(_VALUE_STRATEGY) for field in fields}
    return payload, fields


def _run_property() -> None:
    """Run the Hypothesis property; raises ``AssertionError`` on any escape."""
    from game.fog.filter import apply_fog
    from game.fog.ledger import IntelLedger

    @given(case=_payload_case(), node_id=st.text(min_size=1, max_size=12))
    @settings(
        max_examples=_MAX_EXAMPLES, deadline=None, suppress_health_check=[HealthCheck.too_slow]
    )
    def _property(case: tuple[dict[str, Any], tuple[str, ...]], node_id: str) -> None:
        payload, fields = case
        result = apply_fog(
            dict(payload),
            "organization",
            node_id,
            reach=frozenset(),  # empty reach -> node_id is always out of reach
            ledger=IntelLedger(),  # empty ledger -> read_intel always tier="unknown"
            tick=0,
            staleness_ticks=10,
            unknown_ticks=20,
            political_fields=fields,
        )
        for field in fields:
            assert result[field] is None, (
                f"political field {field!r} escaped apply_fog: "
                f"input={payload[field]!r} output={result[field]!r} node_id={node_id!r}"
            )

    _property()


def check_no_political_field_escapes() -> list[str]:
    """Run the Hypothesis property and translate any failure into a finding.

    :returns: A single violation string on the FIRST (Hypothesis-shrunk)
        escaping case, or ``[]`` when the property holds across every
        generated example.
    :raises SentinelCheckError: If ``game.fog.filter``/``game.fog.ledger``
        cannot be imported — an infrastructure failure, never a silent pass.
    """
    try:
        _run_property()
    except AssertionError as exc:
        return [
            f"apply_fog failed to mask a political field on a Hypothesis-generated "
            f"case: {exc}\n"
            "    fix: every name in POLITICAL_FIELDS/ORG_POLITICAL_FIELDS must be "
            "masked to None for an out-of-reach node with no ledger coverage -- "
            "check apply_fog's masking loop, or add a reasoned SentinelExemption "
            "(key=('political_field', field), reason, owner, date, tracking_task) to "
            "FOG_CONTAINMENT_EXEMPTIONS -- never a silent field removal from "
            "POLITICAL_FIELDS.\n"
            "    WHY THIS FAILS: Constitution VIII.12 (silent no-op / disarmed "
            "guardrail) -- a fog gate that masks most shapes but silently misses one "
            "(an empty string, a nested structure, an already-falsy value) is worse "
            "than no gate: every existing example test only proves the shapes "
            "someone thought to write, and this is exactly the failure mode "
            "Hypothesis's generation + shrinking is built to surface."
        ]
    except ImportError as exc:
        raise SentinelCheckError(f"cannot import game.fog.filter/game.fog.ledger: {exc}") from exc
    return []


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (also routed from ``tools/sentinel_check.py fog``).

    :param argv: CLI args; ``--check`` is accepted for family-CLI parity
        (the behavior is always to gate).
    :returns: 0 clean, 1 gating violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Fog containment — Hypothesis property: no political field escapes "
            "an out-of-reach mask (Constitution VIII.12)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)

    gating: tuple[LabelledCheck, ...] = (
        ("no-political-field-escapes", check_no_political_field_escapes),
    )

    def summary(advisory_count: int) -> str:
        _ = advisory_count
        return f"FOG clean: {_MAX_EXAMPLES} Hypothesis-generated cases, no political field escaped."

    return run_sensor("FOG", gating, (), summary)


if __name__ == "__main__":
    sys.exit(main())
