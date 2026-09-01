"""One override/range grammar for the development-only analysis suite.

This module is the single parser for the optimizer's two input concepts:
one fixed value and one swept range.

Grammar:

* Override: ``"category.field=VALUE"`` — one fixed value.
* Range: ``"category.field=start:end:step"`` — a swept range, inclusive of
  both endpoints, unlike Python ``range()``'s exclusive-end convention.
"""

from __future__ import annotations

import math
from decimal import Decimal

from tools.devtools.sim_analysis.params import (
    ParameterValue,
    get_parameter_type,
)

#: Tolerance fraction of ``step`` used for the inclusive-endpoint float
#: comparison.
_ENDPOINT_TOLERANCE_FRACTION = 0.1

#: Refuse accidental million-plus-point sweeps before allocating or running.
_MAX_RANGE_VALUES = 1_000_000


def _require_finite(component: str, value: ParameterValue) -> None:
    """Reject non-finite grammar components before range expansion."""
    if isinstance(value, bool):
        raise TypeError(f"{component} must be numeric, got: {value!r}")
    try:
        finite = math.isfinite(value)
    except OverflowError as exc:
        raise ValueError(f"{component} must be finite, got: {value!r}") from exc
    if not finite:
        raise ValueError(f"{component} must be finite, got: {value!r}")


def parse_override(spec: str) -> tuple[str, ParameterValue]:
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
    if not path:
        raise ValueError(f"override path must not be empty, got: {spec}")
    if ":" in value_str:
        raise ValueError(
            f"override value must be a single number, got a range-shaped value: {spec} "
            "(use parse_range for 'path=start:end:step')"
        )
    try:
        value = float(value_str)
    except ValueError as exc:
        raise ValueError(f"invalid value {value_str!r} in override {spec!r}: not numeric") from exc
    _require_finite("override value", value)
    if get_parameter_type(path) is int:
        if not value.is_integer():
            raise ValueError(f"integer parameter {path!r} cannot use fractional value {value!r}")
        return path, int(value)
    return path, value


def expand_range(
    start: ParameterValue,
    end: ParameterValue,
    step: ParameterValue,
) -> list[ParameterValue]:
    """Expand ``(start, end, step)`` into an inclusive, deterministic list.

    :param start: First value.
    :param end: Last value (included, subject to float tolerance).
    :param step: Increment; must be positive.
    :returns: Values from ``start`` to ``end`` inclusive, in fixed step
        increments. Decimal index arithmetic avoids binary accumulation drift
        without collapsing sub-micro coefficients.
    :raises ValueError: If any component is non-finite, ``step`` is not
        positive, the range is reversed, or adding ``step`` cannot advance
        the current float.
    """
    _require_finite("range start", start)
    _require_finite("range end", end)
    _require_finite("range step", step)
    if step <= 0:
        raise ValueError(f"step must be positive, got: {step}")
    if start > end:
        raise ValueError(f"range start must not exceed end, got: start={start}, end={end}")

    if type(start) is int and type(end) is int and type(step) is int:
        value_count = ((end - start) // step) + 1
        if value_count > _MAX_RANGE_VALUES:
            raise ValueError(
                f"range expands to {value_count} values; maximum is {_MAX_RANGE_VALUES}"
            )
        return list(range(start, end + 1, step))

    float_start = float(start)
    float_end = float(end)
    float_step = float(step)
    span = float_end - float_start
    tolerance = float_step * _ENDPOINT_TOLERANCE_FRACTION
    _require_finite("range span", span)
    _require_finite("range tolerance", tolerance)
    tolerated_span = span + tolerance
    _require_finite("range tolerated span", tolerated_span)
    step_count = tolerated_span / float_step
    _require_finite("range step count", step_count)
    value_count = math.floor(step_count) + 1
    if value_count > _MAX_RANGE_VALUES:
        raise ValueError(f"range expands to {value_count} values; maximum is {_MAX_RANGE_VALUES}")

    decimal_start = Decimal(str(float_start))
    decimal_step = Decimal(str(float_step))
    values: list[ParameterValue] = []
    previous: float | None = None
    for index in range(value_count):
        value = float(decimal_start + Decimal(index) * decimal_step)
        if not math.isfinite(value):
            raise ValueError(
                f"range expansion overflowed: start={float_start}, step={float_step}, index={index}"
            )
        if previous is not None and value <= previous:
            raise ValueError(
                "range step does not preserve distinct values at this magnitude: "
                f"previous={previous}, next={value}, step={float_step}"
            )
        values.append(value)
        previous = value
    return values


def parse_range(spec: str) -> tuple[str, list[ParameterValue]]:
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
    if not path:
        raise ValueError(f"range path must not be empty, got: {spec}")
    parts = range_str.split(":")
    if len(parts) != 3:
        raise ValueError(f"range must be 'path=start:end:step', got: {spec}")
    try:
        start, end, step = (float(p) for p in parts)
    except ValueError as exc:
        raise ValueError(f"invalid start:end:step in range {spec!r}: not numeric") from exc

    _require_finite("range start", start)
    _require_finite("range end", end)
    _require_finite("range step", step)
    if get_parameter_type(path) is int:
        components = {"start": start, "end": end, "step": step}
        fractional = {name: value for name, value in components.items() if not value.is_integer()}
        if fractional:
            raise ValueError(
                f"integer parameter {path!r} requires integer range components, got: {fractional}"
            )
        return path, expand_range(int(start), int(end), int(step))
    return path, expand_range(start, end, step)


__all__ = ["parse_override", "parse_range", "expand_range"]
