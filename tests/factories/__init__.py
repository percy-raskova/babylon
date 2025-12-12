"""Factory package for creating test domain objects.

This package provides factory classes that create properly configured
domain objects for testing. These factories replace scattered fixture
definitions across test files with a centralized, reusable API.

The primary entry point is :class:`DomainFactory`, which provides methods
for creating :class:`~babylon.models.SocialClass`, :class:`~babylon.models.Relationship`,
and :class:`~babylon.models.WorldState` instances with sensible test defaults.

Example::

    from tests.factories import DomainFactory

    factory = DomainFactory()
    worker = factory.create_worker()
    owner = factory.create_owner()
    state = factory.create_world_state(
        entities={"C001": worker, "C002": owner},
        relationships=[]
    )
"""

from tests.factories.domain import DomainFactory

__all__ = ["DomainFactory"]
