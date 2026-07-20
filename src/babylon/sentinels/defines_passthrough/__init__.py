"""Defines-passthrough sentinel: a production call must thread live defines through.

The error class (task #42 fix wave 1, review MEDIUM-1): a formulas-layer
function declaring an OPTIONAL ``defines`` parameter, called without it --
silently falling back to that function's own schema-default coefficients
instead of the run's ``services.defines``/``defines.yaml``. Registry =
watched functions (whose ``defines`` parameter is optional, resolved by
introspecting the declaring file's own AST) plus the dated exemption list;
checks = a single static AST rule finding every call site that supplies
neither the keyword nor the correctly-positioned positional argument.

Founding specimens: ``ideology.py``'s ``route_agitation_to_ternary`` and
``compute_exploitation_visibility`` calls (the sibling instances of the bug
the task #42-A fix for ``compute_agitation_delta`` left unfixed in the SAME
per-node loop), plus ``sovereignty.py``'s ``calculate_metabolic_impact``
call (an unrelated third instance this sentinel's own repo-wide survey
found) -- all three fixed in the same fix wave that landed this sentinel.
``sovereign.py``'s ``Sovereign.metabolic_impact`` computed_field is the one
architectural exemption (a Pydantic property has no services/defines object
reachable at all).
"""

from babylon.sentinels.defines_passthrough.checks import (
    is_test_source,
    main,
    missing_defines_passthrough,
)
from babylon.sentinels.defines_passthrough.registry import (
    DEFINES_PASSTHROUGH_EXEMPTIONS,
    EXCLUDED_DIRS,
    PRODUCTION_ROOTS,
    WATCHED_FUNCTIONS,
    WatchedFunction,
)

__all__ = [
    "DEFINES_PASSTHROUGH_EXEMPTIONS",
    "EXCLUDED_DIRS",
    "PRODUCTION_ROOTS",
    "WATCHED_FUNCTIONS",
    "WatchedFunction",
    "is_test_source",
    "main",
    "missing_defines_passthrough",
]
