"""The shared trace-CSV byte contract (Program: qa:regression modernization, E2b).

Extracted verbatim from ``tools/regression_test.py``'s ``_format_dense_value`` /
``dense_trace_to_csv_bytes`` (which now import and delegate to this module — a
byte-neutral move, not a rewrite) so every trace/dense-golden producer in the
codebase — the ``qa:regression`` CLI *and* the headless-runner artifact bundle
(``dense_trace.csv``, Task 10) — shares one serializer instead of two
independently-drifting copies.

This module is intentionally dependency-free (stdlib ``csv``/``io`` only, no
``babylon.*`` imports): it sits below every layering contract
(``kernel < models/formulas < topology < domain < engine``, Program 14) so any
layer, including the headless runner, can import it without an import-linter
violation.

Byte contract (Constitution III.12 corollary — this is a serialization used
as a cross-process/cross-run behavioral contract, not an implementation
detail, so the layout is SPECIFIED, not merely implied by one call site):

* Floats: Python's ``repr()`` — the shortest decimal string that round-trips
  to the exact IEEE-754 double (CPython's ``repr_float`` since 3.1;
  deterministic and reproducible across any CPython 3.x process).
* Bools: ``str(bool)`` (``"True"``/``"False"``) — checked before the float
  branch, since ``bool`` is an ``int`` subclass and would otherwise be
  swallowed by it.
* CSV: UTF-8, comma-delimited, RFC 4180 minimal quoting
  (``csv.QUOTE_MINIMAL``), ``\\n`` line terminator (not the platform
  default), header row, trailing newline.

See Also:
    ``docs/reference/determinism-contract.rst`` ("Dense Golden Traces") for
    the wider dense-trace column/schema conventions this byte contract feeds.
"""

from __future__ import annotations

import csv
import io


def format_trace_value(value: float | bool) -> str:
    """Format one trace/dense-golden scalar per the documented float/bool policy.

    Floats use Python's ``repr()`` (the shortest round-trippable decimal for
    the IEEE-754 double). Bools render via ``str(bool)`` (``"True"``/
    ``"False"``) — checked first since ``bool`` is an ``int`` subclass and
    would otherwise be swallowed by a float branch.

    Args:
        value: A float or bool captured from simulation state.

    Returns:
        The exact string written to the trace CSV cell.
    """
    if isinstance(value, bool):
        return str(value)
    return repr(value)


def trace_rows_to_csv_bytes(header: list[str], rows: list[list[str]]) -> bytes:
    """Serialize a pre-formatted header + row set to the canonical CSV byte stream.

    Args:
        header: Ordered column names.
        rows: Pre-formatted string cells (see :func:`format_trace_value`),
            each row aligned to ``header``.

    Returns:
        The exact bytes written to (or compared against) a committed dense
        golden or the headless-runner bundle's ``dense_trace.csv``: UTF-8,
        comma-delimited, RFC 4180 minimal quoting, ``\\n`` line terminator,
        header row, trailing newline.
    """
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


__all__ = ["format_trace_value", "trace_rows_to_csv_bytes"]
