"""OrganizationActionSpy — patches OODASystem._resolve_for_organization
to record per-org action-resolution events for spec-056 US2.

Per research.md §2 (revised post-F1): the F1 helper extraction made
``OODASystem._resolve_for_organization`` a named class member, which
is exactly the seam ``unittest.mock.patch.object`` expects. This spy
patches that method via ``patch.object`` and records each per-org
invocation BEFORE forwarding to the original.

If a future refactor renames or removes ``_resolve_for_organization``,
``patch.object`` raises ``AttributeError`` immediately on ``__enter__`` —
the desired fail-loud behavior; the seam dependency is documented here.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import patch

from babylon.engine.systems.ooda import OODASystem

if TYPE_CHECKING:
    from types import TracebackType

    from tests.property.harness.causal_harness import OrganizationActionEvent


class OrganizationActionSpy:
    """Context manager that patches ``OODASystem._resolve_for_organization``
    to record one ``OrganizationActionEvent`` per per-org invocation.

    Usage::

        with OrganizationActionSpy() as org_spy:
            engine.run_tick(graph, services, context)
        # org_spy.events now holds one OrganizationActionEvent per org
        # whose action was resolved this tick (in OODA order).
    """

    def __init__(self) -> None:
        self.events: list[OrganizationActionEvent] = []
        self._action_index = 0
        self._patcher: object | None = None

    def __enter__(self) -> OrganizationActionSpy:
        from tests.property.harness.causal_harness import OrganizationActionEvent

        original = OODASystem._resolve_for_organization

        def wrapped(
            system_self: OODASystem,
            *args: object,
            **kwargs: object,
        ) -> object:
            # Recover the per-org id from kwargs or positional args.
            # Signature: _resolve_for_organization(self, score, org_data_lookup,
            #   player_actions, defines)
            score = kwargs.get("score") if "score" in kwargs else (args[0] if args else None)
            org_id = getattr(score, "org_id", None) or "<unknown>"
            self.events.append(
                OrganizationActionEvent(
                    organization_id=str(org_id),
                    action_resolution_index=self._action_index,
                    monotonic_timestamp_ns=time.monotonic_ns(),
                )
            )
            self._action_index += 1
            return original(system_self, *args, **kwargs)

        self._patcher = patch.object(
            OODASystem, "_resolve_for_organization", wrapped, autospec=False
        )
        self._patcher.start()  # type: ignore[attr-defined]
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._patcher is not None:
            self._patcher.stop()  # type: ignore[attr-defined]
        # Sanity: timestamps strictly monotonic across recorded events
        if exc_type is None and len(self.events) >= 2:
            for prev, curr in zip(self.events, self.events[1:], strict=False):
                assert curr.monotonic_timestamp_ns >= prev.monotonic_timestamp_ns, (
                    f"OrganizationActionSpy timestamp non-monotonic at "
                    f"action {curr.action_resolution_index}"
                )
