"""The kernel — Babylon's bottom layer (Program 14, Constitution II.6).

Framework abstractions every layer may import and that import nothing above
themselves at runtime: the event bus, the system base class + protocol, the
graph substrate protocol, and the DI services protocol. These are exactly the
constructs whose former home inside ``babylon.engine`` forced economics,
persistence, and formulas to import the engine backward (the cycles broken in
Program 14 Phase 1).

Layering law (enforced by import-linter): ``kernel`` < ``models``/``formulas``
< domain packages < ``engine``. Annotations may reference upward under
``TYPE_CHECKING``; the runtime import graph may not.
"""

from babylon.kernel.event_bus import Event, EventBus
from babylon.kernel.graph_protocol import GraphProtocol
from babylon.kernel.services import ServicesProtocol
from babylon.kernel.system_base import SystemBase, resolve_rng
from babylon.kernel.system_protocol import ContextType, System

__all__ = [
    "ContextType",
    "Event",
    "EventBus",
    "GraphProtocol",
    "ServicesProtocol",
    "System",
    "SystemBase",
    "resolve_rng",
]
