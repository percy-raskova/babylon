"""Dangling sentinel: a dynamic string-name reference must land on something real.

The DUAL of :mod:`babylon.sentinels.inert` (declared construct with no
caller): here the defect is the opposite shape — a call site referencing a
target that does not exist. Registry = watched classes/protocols plus
watched receiver families plus the dated exemption list; checks = static AST
rules identifying every typed-receiver ``getattr(x, "name", default)`` call
and verifying ``"name"`` against the union of the receiver's real members.

Founding incident: ``web/game/engine_bridge.py``'s ``_persist_action_result``
reads ``getattr(persistence, "persist_action_result", None)`` (SINGULAR) —
every real backend (``RuntimePersistence``/``PostgresRuntimeExtensions``
protocols, ``PostgresRuntime``, ``RuntimeDatabase``) only ever declares
``persist_action_results`` (PLURAL, batched) — so the guarded branch is
structurally dead code with a heartbeat, silently falling through to the
Django-ORM fallback on every call.
"""

from babylon.sentinels.dangling.checks import (
    class_members,
    dangling_references,
    is_test_source,
    typed_getattr_sites,
)
from babylon.sentinels.dangling.registry import (
    DANGLING_EXEMPTIONS,
    PRODUCTION_ROOTS,
    WATCHED_CLASSES,
    WATCHED_RECEIVERS,
    WatchedClass,
    WatchedReceiver,
)

__all__ = [
    "DANGLING_EXEMPTIONS",
    "PRODUCTION_ROOTS",
    "WATCHED_CLASSES",
    "WATCHED_RECEIVERS",
    "WatchedClass",
    "WatchedReceiver",
    "class_members",
    "dangling_references",
    "is_test_source",
    "typed_getattr_sites",
]
