"""Structural-conformance pin: ServiceContainer satisfies ServicesProtocol.

The kernel protocol is the DI contract lower layers type against
(Program 14 Phase 1); the engine's concrete ``ServiceContainer`` must keep
satisfying it. The module-level annotated assignment is checked by MyPy
strict on every ``mise run check``; the runtime test guards the attribute
surface against dataclass-field renames MyPy could miss on ``Any`` fields.
"""

from __future__ import annotations

import dataclasses

import pytest

from babylon.engine.services import ServiceContainer
from babylon.kernel.services import ServicesProtocol

#: MyPy-strict structural check — fails typecheck if the container ever stops
#: satisfying the kernel protocol.
_CONFORMS: ServicesProtocol = ServiceContainer.create()


@pytest.mark.unit
class TestServicesProtocolConformance:
    """ServiceContainer ↔ ServicesProtocol surface agreement."""

    def test_every_protocol_attribute_exists_on_container(self) -> None:
        container = ServiceContainer.create()
        protocol_attrs = {
            name for name in ServicesProtocol.__annotations__ if not name.startswith("_")
        }
        missing = {name for name in protocol_attrs if not hasattr(container, name)}
        assert missing == set(), f"container lost protocol attributes: {missing}"

    def test_protocol_mirrors_full_container_field_surface(self) -> None:
        container_fields = {f.name for f in dataclasses.fields(ServiceContainer)}
        protocol_attrs = set(ServicesProtocol.__annotations__)
        unmirrored = container_fields - protocol_attrs
        assert unmirrored == set(), (
            f"ServiceContainer grew fields the kernel protocol does not mirror: "
            f"{unmirrored} — add them to babylon.kernel.services.ServicesProtocol"
        )
