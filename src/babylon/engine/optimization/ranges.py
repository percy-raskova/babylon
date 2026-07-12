"""One override/range grammar for the optimization package.

Unifies three parallel, slightly-inconsistent grammars that previously lived
in ``tools/parameter_analysis.py`` (``--param path=value``),
``tools/tune_parameters.py`` (``--param``/``--start``/``--end``/``--step``
as separate flags), and ``tools/landscape_analysis.py`` (``start:end:step``
strings). All three expressed the same two ideas — "one value" and "a swept
range" — with different syntax; this module is the single parser both
concepts route through from here on.

Grammar:

* Override: ``"category.field=VALUE"`` — one fixed value.
* Range: ``"category.field=start:end:step"`` — a swept range, inclusive of
  both endpoints (matching ``landscape_analysis.py``'s float-tolerance
  behavior, not Python ``range()``'s exclusive-end convention).
"""

from __future__ import annotations

#: Tolerance fraction of ``step`` used for the inclusive-endpoint float
#: comparison (matches ``tools/landscape_analysis.py::parse_range``).
_ENDPOINT_TOLERANCE_FRACTION = 0.1

#: Decimal places values are rounded to, avoiding float-accumulation drift
#: across many additions of ``step`` (matches the source tools).
_ROUND_NDIGITS = 6


def parse_override(spec: str) -> tuple[str, float]:
    """Parse a fixed-value override: ``"category.field=VALUE"``.

    :param spec: Override spec string.
    :returns: ``(param_path, value)``.
    :raises ValueError: If ``spec`` is not ``"path=value"`` shaped, or the
        value is not numeric.

    Example::

        >>> parse_override("economy.extraction_efficiency=0.5")
        ('economy.extraction_efficiency', 0.5)
    """
    if "=" not in spec:
        raise ValueError(f"override must be 'path=value', got: {spec}")
    path, value_str = spec.split("=", 1)
    path = path.strip()
    if ":" in value_str:
        raise ValueError(
            f"override value must be a single number, got a range-shaped value: {spec} "
            "(use parse_range for 'path=start:end:step')"
        )
    try:
        value = float(value_str)
    except ValueError as exc:
        raise ValueError(f"invalid value {value_str!r} in override {spec!r}: not numeric") from exc
    return path, value


def expand_range(start: float, end: float, step: float) -> list[float]:
    """Expand ``(start, end, step)`` into an inclusive, deterministic list.

    :param start: First value.
    :param end: Last value (included, subject to float tolerance).
    :param step: Increment; must be positive.
    :returns: Values from ``start`` to ``end`` inclusive, in fixed step
        increments, each rounded to :data:`_ROUND_NDIGITS` places.
    :raises ValueError: If ``step`` is not positive.
    """
    if step <= 0:
        raise ValueError(f"step must be positive, got: {step}")

    values: list[float] = []
    current = start
    tolerance = step * _ENDPOINT_TOLERANCE_FRACTION
    while current <= end + tolerance:
        values.append(round(current, _ROUND_NDIGITS))
        current += step
    return values


def parse_range(spec: str) -> tuple[str, list[float]]:
    """Parse a swept range: ``"category.field=start:end:step"``.

    :param spec: Range spec string.
    :returns: ``(param_path, values)`` — ``values`` from
        :func:`expand_range`.
    :raises ValueError: If ``spec`` is not ``"path=start:end:step"`` shaped.

    Example::

        >>> parse_range("economy.extraction_efficiency=0.1:0.3:0.1")
        ('economy.extraction_efficiency', [0.1, 0.2, 0.3])
    """
    if "=" not in spec:
        raise ValueError(f"range must be 'path=start:end:step', got: {spec}")
    path, range_str = spec.split("=", 1)
    path = path.strip()
    parts = range_str.split(":")
    if len(parts) != 3:
        raise ValueError(f"range must be 'path=start:end:step', got: {spec}")
    try:
        start, end, step = (float(p) for p in parts)
    except ValueError as exc:
        raise ValueError(f"invalid start:end:step in range {spec!r}: not numeric") from exc
    return path, expand_range(start, end, step)


__all__ = ["parse_override", "parse_range", "expand_range"]
