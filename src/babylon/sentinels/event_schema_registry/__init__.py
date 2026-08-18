"""The event-schema registry sentinel family (theme 7, C-1 rescope).

Re-exports the loader/dataclasses (:mod:`.registry`), the BSL emit-site
scanner (:mod:`.bsl_emit_scan`), and the one-way ``EVENT_BUILDERS`` sync
check (:mod:`.sync`, R4.4.1) for convenient importing.
"""

from __future__ import annotations

from babylon.sentinels.event_schema_registry.bsl_emit_scan import (
    EmitSite,
    scan_directory,
    scan_file,
)
from babylon.sentinels.event_schema_registry.registry import (
    REGISTRY_PATH,
    EventSchemaRegistry,
    RegistryKey,
    Tier1Row,
    Tier2Row,
    Tier3Row,
    UnmintedRow,
    load_registry,
    normalize_key,
)
from babylon.sentinels.event_schema_registry.sync import event_builders_subset_violations

__all__ = [
    "REGISTRY_PATH",
    "EmitSite",
    "EventSchemaRegistry",
    "RegistryKey",
    "Tier1Row",
    "Tier2Row",
    "Tier3Row",
    "UnmintedRow",
    "event_builders_subset_violations",
    "load_registry",
    "normalize_key",
    "scan_directory",
    "scan_file",
]
