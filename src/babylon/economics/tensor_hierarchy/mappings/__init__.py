"""Typed BEA-to-Department mapping, loaded once at import time.

Spec 058 / FR-009 — replaces the per-call TOML reparse pattern in
:meth:`babylon.economics.tensor_hierarchy.inter_industry.DefaultDepartmentAggregator.get_default_mapping`
with a singleton :class:`BEAMappings` constant.

Per the 2026-05-08 commit-7 reformulation: the actual TOML on disk uses a
``{departments: {I: [bea_codes], IIA: [...], IIB: [...], III: [...]}}``
shape (4 departments, no per-row weights), not the row-array shape with
fractional weights that the original ``contracts/bea_mappings.md`` sketched.
The Pydantic model has been adjusted to match the file on disk; the legacy
``dict[str, str]`` flat-mapping output (consumed by ``aggregate``) is exposed
via :meth:`BEAMappings.as_flat_dict`.

If the TOML is missing or malformed, import fails fast with a clear
traceback — louder and more diagnostic than today's runtime fallback to
an empty dict.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Final

from babylon.economics.tensor_hierarchy.mappings._models import VALID_DEPARTMENTS, BEAMappings

__all__ = ["BEA_TO_DEPARTMENT", "BEAMappings", "VALID_DEPARTMENTS"]

_TOML_PATH: Final[Path] = Path(__file__).parent / "bea_to_department.toml"

with _TOML_PATH.open("rb") as _f:
    _RAW = tomllib.load(_f)

BEA_TO_DEPARTMENT: Final[BEAMappings] = BEAMappings.model_validate(_RAW)
"""Singleton, validated, frozen mapping. Construct once; consume many."""
