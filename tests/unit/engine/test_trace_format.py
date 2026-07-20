"""The trace byte contract: shortest-repr floats, RFC4180-minimal CSV, LF, trailing newline."""

from __future__ import annotations

import pytest

from babylon.engine.trace_format import format_trace_value, trace_rows_to_csv_bytes

pytestmark = pytest.mark.unit


def test_bool_renders_python_style() -> None:
    assert format_trace_value(True) == "True"
    assert format_trace_value(False) == "False"


def test_float_renders_shortest_roundtrip_repr() -> None:
    assert format_trace_value(0.1) == "0.1"
    assert format_trace_value(1.0) == "1.0"
    assert format_trace_value(1.179e9) == "1179000000.0"


def test_csv_bytes_contract() -> None:
    got = trace_rows_to_csv_bytes(["tick", "x"], [["0", "1.0"], ["1", "2.0"]])
    assert got == b"tick,x\n0,1.0\n1,2.0\n"
