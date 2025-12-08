"""Component protocol definition.

The Component protocol defines the base interface for all component types
in the Entity-Component architecture. All concrete components must implement
this protocol.

The protocol is runtime-checkable, allowing isinstance() checks at runtime.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Component(Protocol):
    """Protocol defining the interface for all component types.

    All components in the Babylon simulation must implement this protocol.
    The protocol requires a component_type property that returns a string
    identifier for the component type.

    This protocol is runtime-checkable, meaning you can use isinstance()
    to verify that an object implements the Component interface.

    Example:
        >>> class MyComponent(BaseModel):
        ...     model_config = ConfigDict(frozen=True)
        ...     @property
        ...     def component_type(self) -> str:
        ...         return "my_component"
        ...
        >>> instance = MyComponent()
        >>> isinstance(instance, Component)
        True
    """

    @property
    def component_type(self) -> str:
        """Return the component type identifier.

        Returns:
            A string identifying the type of this component.
            For example: "material", "vitality", "spatial", etc.
        """
        ...
