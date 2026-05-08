"""Spec 058 / SC-006: pin the public import surface of the new
``babylon.models.enums`` and ``babylon.config.defines`` packages.

Per the 2026-05-08 Q2 clarification, Bundle 1 commits to preserving
``from <pkg> import X`` for every historical symbol, plus an explicitly
declared ``__all__`` in each new ``__init__.py``. This test pins both
contracts: it asserts that ``__all__`` is declared and that the set of
exported names is invariant across the split (commit 2 for enums; commit
3 for defines).

Baseline symbol sets were captured at commit-time from the pre-split
monolithic modules (`enums.py` and `defines.py`).
"""

from __future__ import annotations

import pytest

# --- Baseline symbol sets (pre-split, captured 2026-05-08) -------------------

EXPECTED_DEFINES_PUBLIC: frozenset[str] = frozenset(
    {
        # 42 child *Defines classes (41 from Spec 058 + 1 from Spec 057: LeontiefRentDefines)
        "AidDefines",
        "ArcGISDefines",
        "BehavioralDefines",
        "BifurcationDefines",
        "CarceralDefines",
        "ClassDynamicsDefines",
        "ClassSystemDefines",
        "CommunityDefines",
        "ConsciousnessDefines",
        "ContradictionFieldDefines",
        "CrisisDefines",
        "DispossessionDefines",
        "EconomyDefines",
        "EdgeTransitionDefines",
        "EndgameDefines",
        "ExternalDataDefines",
        "InfraTerrainDefines",
        "InfrastructureDefines",
        "InitialDefines",
        "InstitutionDefines",
        "LeontiefRentDefines",  # Spec 057 / FR-001
        "LifecycleDefines",
        "MetabolismDefines",
        "MobilizeDefines",
        "MoveDefines",
        "NegotiateDefines",
        "OODADefines",
        "OrganizationDefines",
        "PrecisionDefines",
        "RentCircuitDefines",
        "ReserveArmyDefines",
        "ServicesDefines",
        "SolidarityDefines",
        "StateApparatusAIDefines",
        "StruggleDefines",
        "SurvivalDefines",
        "TensionDefines",
        "TerritoryDefines",
        "TimescaleDefines",
        "TopologyDefines",
        "VitalityDefines",
        "WorkingDayDefines",
        # 1 assembler facade
        "GameDefines",
    }
)


EXPECTED_ENUMS_PUBLIC: frozenset[str] = frozenset(
    {
        # 45 enum classes
        "ActionType",
        "ApparatusType",
        "BiocapacityType",
        "ClassCharacter",
        "ClassInscription",
        "CommunityType",
        "ConsciousnessTendency",
        "ContradictionCharacter",
        "ContradictionType",
        "DecisionMode",
        "DisplacementPriorityMode",
        "DispossessionType",
        "EdgeMode",
        "EdgeType",
        "EventType",
        "ExploitationMode",
        "FlowCategory",
        "GameOutcome",
        "HyperedgeCategory",
        "InfrastructureType",
        "IntensityLevel",
        "InternetResponseMode",
        "JunctionType",
        "JurisdictionLevel",
        "LegalStanding",
        "LegalStatus",
        "LegitimationClassification",
        "LifecyclePhase",
        "LocalityClass",
        "MembershipRole",
        "OperationalProfile",
        "OrgType",
        "ResolutionType",
        "RulingClassFraction",
        "SectorType",
        "ServiceType",
        "SocialFunction",
        "SocialRole",
        "StateActionType",
        "StateFaction",
        "SurveillanceMethod",
        "TerrainType",
        "TerritoryType",
        "ThreadPhase",
        "TopologyType",
        # 1 helper function
        "resolve_edge_type",
    }
)


# --- Tests -------------------------------------------------------------------


@pytest.mark.unit
class TestEnumsPublicSurface:
    """Spec 058 / FR-001 / SC-006: enums package surface invariance."""

    def test_all_is_declared(self) -> None:
        """The new ``babylon.models.enums`` package MUST declare ``__all__``."""
        from babylon.models import enums

        assert hasattr(enums, "__all__"), (
            "Spec 058 / FR-001 / Q2 clarification: babylon.models.enums "
            "MUST declare __all__ explicitly to codify the public surface "
            "and control `from babylon.models.enums import *` semantics."
        )
        assert isinstance(enums.__all__, (list, tuple)), (
            f"__all__ must be a list or tuple, got {type(enums.__all__).__name__}"
        )

    def test_all_matches_baseline(self) -> None:
        """The set of exported symbols MUST equal the pre-split baseline.

        Per Q2: the bundle commits to preserving ``from <pkg> import X``
        for every historical symbol; ``__all__`` is the authoritative
        declaration of that set.
        """
        from babylon.models import enums

        actual = frozenset(enums.__all__)
        missing = EXPECTED_ENUMS_PUBLIC - actual
        extra = actual - EXPECTED_ENUMS_PUBLIC
        assert not missing and not extra, (
            f"babylon.models.enums.__all__ drifted from baseline:\n"
            f"  missing (in baseline, not in __all__): {sorted(missing)}\n"
            f"  extra (in __all__, not in baseline): {sorted(extra)}"
        )

    def test_each_baseline_symbol_resolves_via_flat_import(self) -> None:
        """Every symbol in the baseline MUST be importable as
        ``from babylon.models.enums import X``.

        Belt-and-suspenders next to ``test_all_matches_baseline`` —
        this exercises the actual import machinery, not just the
        ``__all__`` introspection.
        """
        import babylon.models.enums as enums_pkg

        for name in EXPECTED_ENUMS_PUBLIC:
            assert hasattr(enums_pkg, name), (
                f"Spec 058 / SC-006: babylon.models.enums.{name} does "
                f"not resolve. The bundle's flat-import contract is broken."
            )

    def test_star_import_works(self) -> None:
        """``from babylon.models.enums import *`` MUST expose the same set
        as ``__all__`` (Python star-import contract)."""
        namespace: dict[str, object] = {}
        exec("from babylon.models.enums import *", namespace)
        # Drop builtins added by exec
        namespace.pop("__builtins__", None)
        actual = frozenset(namespace.keys())
        missing = EXPECTED_ENUMS_PUBLIC - actual
        assert not missing, (
            f"`from babylon.models.enums import *` did not expose: {sorted(missing)}"
        )

    def test_module_attribute_access_works(self) -> None:
        """``import babylon.models.enums as e; e.X`` access MUST work."""
        import babylon.models.enums as e

        for name in sorted(EXPECTED_ENUMS_PUBLIC):
            obj = getattr(e, name, None)
            assert obj is not None, f"e.{name} returned None"


@pytest.mark.unit
class TestDefinesPublicSurface:
    """Spec 058 / FR-002 / SC-006: defines package surface invariance."""

    def test_all_is_declared(self) -> None:
        """The new ``babylon.config.defines`` package MUST declare ``__all__``."""
        from babylon.config import defines

        assert hasattr(defines, "__all__"), (
            "Spec 058 / FR-002 / Q2 clarification: babylon.config.defines "
            "MUST declare __all__ explicitly to codify the public surface."
        )
        assert isinstance(defines.__all__, (list, tuple)), (
            f"__all__ must be a list or tuple, got {type(defines.__all__).__name__}"
        )

    def test_all_matches_baseline(self) -> None:
        """The set of exported symbols MUST equal the pre-split baseline."""
        from babylon.config import defines

        actual = frozenset(defines.__all__)
        missing = EXPECTED_DEFINES_PUBLIC - actual
        extra = actual - EXPECTED_DEFINES_PUBLIC
        assert not missing and not extra, (
            f"babylon.config.defines.__all__ drifted from baseline:\n"
            f"  missing (in baseline, not in __all__): {sorted(missing)}\n"
            f"  extra (in __all__, not in baseline): {sorted(extra)}"
        )

    def test_each_baseline_symbol_resolves_via_flat_import(self) -> None:
        """Every baseline symbol MUST be importable as
        ``from babylon.config.defines import X``."""
        import babylon.config.defines as defines_pkg

        for name in EXPECTED_DEFINES_PUBLIC:
            assert hasattr(defines_pkg, name), (
                f"Spec 058 / SC-006: babylon.config.defines.{name} does "
                f"not resolve. The bundle's flat-import contract is broken."
            )

    def test_star_import_works(self) -> None:
        """``from babylon.config.defines import *`` MUST expose ``__all__``."""
        namespace: dict[str, object] = {}
        exec("from babylon.config.defines import *", namespace)
        namespace.pop("__builtins__", None)
        actual = frozenset(namespace.keys())
        missing = EXPECTED_DEFINES_PUBLIC - actual
        assert not missing, (
            f"`from babylon.config.defines import *` did not expose: {sorted(missing)}"
        )

    def test_module_attribute_access_works(self) -> None:
        """``import babylon.config.defines as d; d.X`` access MUST work."""
        import babylon.config.defines as d

        for name in sorted(EXPECTED_DEFINES_PUBLIC):
            obj = getattr(d, name, None)
            assert obj is not None, f"d.{name} returned None"

    def test_game_defines_instantiates_with_expected_field(self) -> None:
        """``GameDefines()`` MUST construct cleanly and expose nested fields.

        SC-001 + the FR-002 acceptance scenario: ``GameDefines()`` instantiates
        with the same shape as the pre-split monolith. The smoke check exercises
        a known-stable nested coefficient (``economy.extraction_efficiency``)
        whose default is 0.8 (per pyproject.toml [tool.babylon]).
        """
        from babylon.config.defines import GameDefines

        gd = GameDefines()
        assert gd.economy.extraction_efficiency == 0.8
