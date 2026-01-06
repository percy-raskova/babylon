"""Fixtures for scenario tests (long-trajectory simulation validation).

Scenario tests validate canonical outcomes from theoretical documents:
- ai-docs/carceral-equilibrium.md: The 70-Year Arc (null hypothesis)
- ai-docs/theory.md: Core MLM-TW theoretical framework

These fixtures provide pre-configured WorldState instances for
testing long-term simulation trajectories.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.observers import MetricsCollector
from babylon.models import SimulationConfig, WorldState
from babylon.models.entities.economy import GlobalEconomy
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import IdeologicalProfile, SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import EdgeType, SectorType, SocialRole


@pytest.fixture
def config() -> SimulationConfig:
    """Create default simulation configuration."""
    return SimulationConfig()


@pytest.fixture
def batch_metrics_collector() -> MetricsCollector:
    """Create MetricsCollector in batch mode for long-running scenarios."""
    return MetricsCollector(mode="batch")


def create_imperial_circuit_state() -> WorldState:
    """Create WorldState representing the full imperial circuit.

    This is the "null hypothesis" initial state: a functioning imperial
    system with NO player organization and NO solidarity edges.
    Without intervention, this state will progress through:

    Phase 1: Imperial Extraction (hollow stability)
    Phase 2: Metabolic Rift Opens (overshoot > 1.0)
    Phase 3: SUPERWAGE_CRISIS (rent pool exhausted)
    Phase 4: CLASS_DECOMPOSITION (LA -> Enforcers + Prisoners)
    Phase 5: CONTROL_RATIO_CRISIS (prisoners exceed capacity)
    Phase 6/7: TERMINAL_DECISION(genocide) -> Stable Necropolis

    Entities:
        C001: Core Bourgeoisie - owns rent pool, pays wages
        C002: Labor Aristocracy - receives super-wages (will decompose)
        C003: Periphery Proletariat - exploited, source of value
        C004: Comprador Bourgeoisie - intermediary, passes tribute
        C005: Carceral Enforcer - dormant, activates on CLASS_DECOMPOSITION
        C006: Internal Proletariat - dormant, activates on CLASS_DECOMPOSITION

    Edges:
        EXPLOITATION: C001 -> C003 (Core extracts from Periphery)
        WAGES: C001 -> C002 (Super-wages to LA)
        TRIBUTE: C004 -> C001 (Comprador tribute to Core)
        TENANCY: All classes -> T001 (all live on same territory)

    Key constraints for null hypothesis:
        - organization = 0.0 for all classes (no player intervention)
        - No SOLIDARITY edges (ensures fascist/genocide path)
        - Moderate biocapacity that will deplete over time

    Returns:
        WorldState configured for the 70-year arc test.
    """
    # Core Bourgeoisie - owns the system, starts wealthy
    core_bourgeoisie = SocialClass(
        id="C001",
        name="Core Bourgeoisie",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=1000.0,
        ideology=IdeologicalProfile(
            class_consciousness=0.1,  # Low class consciousness
            national_identity=0.7,  # High nationalism
            agitation=0.0,
        ),
        organization=0.8,  # Highly organized (class solidarity of owners)
        repression_faced=0.05,  # Protected by state
        subsistence_threshold=1.0,
        s_bio=5.0,  # High consumption
        s_class=10.0,
    )

    # Labor Aristocracy - bribed workers, will decompose
    # High starting wealth ensures LA survives until SUPERWAGE_CRISIS
    # triggers decomposition (rent pool must exhaust first)
    labor_aristocracy = SocialClass(
        id="C002",
        name="Labor Aristocracy",
        role=SocialRole.LABOR_ARISTOCRACY,
        wealth=50000.0,  # High wealth to survive until rent pool exhausts
        ideology=IdeologicalProfile(
            class_consciousness=0.2,  # Low (sedated by super-wages)
            national_identity=0.6,  # Moderate nationalism
            agitation=0.0,
        ),
        organization=0.0,  # KEY: No organization (null hypothesis)
        repression_faced=0.2,  # Low repression (privileged)
        subsistence_threshold=5.0,
        population=700,  # 70% will become prisoners after decomposition
        s_bio=3.0,
        s_class=5.0,
    )

    # Periphery Proletariat - exploited, source of imperial rent
    periphery_proletariat = SocialClass(
        id="C003",
        name="Periphery Proletariat",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=10.0,
        ideology=IdeologicalProfile(
            class_consciousness=0.6,  # Higher consciousness (exploitation visible)
            national_identity=0.3,  # Lower nationalism
            agitation=0.0,
        ),
        organization=0.0,  # KEY: No organization (null hypothesis)
        repression_faced=0.8,  # Heavy repression
        subsistence_threshold=0.5,
        population=1000,
        s_bio=0.5,  # Minimal consumption
        s_class=0.5,
    )

    # Comprador Bourgeoisie - intermediary, passes tribute
    comprador = SocialClass(
        id="C004",
        name="Comprador Bourgeoisie",
        role=SocialRole.COMPRADOR_BOURGEOISIE,
        wealth=50.0,
        ideology=IdeologicalProfile(
            class_consciousness=0.1,
            national_identity=0.5,
            agitation=0.0,
        ),
        organization=0.5,  # Moderate organization
        repression_faced=0.3,
        subsistence_threshold=2.0,
        s_bio=2.0,
        s_class=3.0,
    )

    # Dormant Carceral Enforcer - activated during CLASS_DECOMPOSITION
    # Receives portion of LA population when super-wages collapse
    carceral_enforcer = SocialClass(
        id="C005",
        name="Carceral Enforcer",
        role=SocialRole.CARCERAL_ENFORCER,
        wealth=0.0,
        ideology=IdeologicalProfile(
            class_consciousness=0.1,
            national_identity=0.8,  # High nationalism (guard mentality)
            agitation=0.0,
        ),
        organization=0.0,
        repression_faced=0.1,
        subsistence_threshold=1.0,
        population=0,  # Dormant - no population until decomposition
        active=False,  # Dormant
        s_bio=2.0,
        s_class=3.0,
    )

    # Dormant Internal Proletariat - activated during CLASS_DECOMPOSITION
    # Receives majority of LA population when super-wages collapse
    internal_proletariat = SocialClass(
        id="C006",
        name="Internal Proletariat",
        role=SocialRole.INTERNAL_PROLETARIAT,
        wealth=0.0,
        ideology=IdeologicalProfile(
            class_consciousness=0.3,
            national_identity=0.2,  # Low nationalism
            agitation=0.0,
        ),
        organization=0.0,  # KEY: No organization (null hypothesis)
        repression_faced=0.9,  # Heavy repression
        subsistence_threshold=0.5,
        population=0,  # Dormant - no population until decomposition
        active=False,  # Dormant
        s_bio=0.5,
        s_class=0.5,
    )

    entities = {
        "C001": core_bourgeoisie,
        "C002": labor_aristocracy,
        "C003": periphery_proletariat,
        "C004": comprador,
        "C005": carceral_enforcer,
        "C006": internal_proletariat,
    }

    # Territory with depletable biocapacity
    territory = Territory(
        id="T001",
        name="Imperial Zone",
        sector_type=SectorType.INDUSTRIAL,
        biocapacity=50.0,  # Moderate - will deplete to cause metabolic rift
        max_biocapacity=100.0,
        regeneration_rate=0.01,  # Slow regeneration
        extraction_intensity=0.3,  # Moderate extraction
    )

    territories = {"T001": territory}

    # Relationships: The Imperial Circuit
    relationships = [
        # EXPLOITATION: Core Bourgeoisie extracts from Periphery
        Relationship(
            source_id="C001",
            target_id="C003",
            edge_type=EdgeType.EXPLOITATION,
            value_flow=20.0,  # Significant extraction
            tension=0.3,  # Initial tension
        ),
        # WAGES: Core Bourgeoisie pays Labor Aristocracy (super-wages)
        Relationship(
            source_id="C001",
            target_id="C002",
            edge_type=EdgeType.WAGES,
            value_flow=15.0,  # Super-wages from rent pool
        ),
        # TRIBUTE: Comprador sends tribute to Core (after keeping cut)
        Relationship(
            source_id="C004",
            target_id="C001",
            edge_type=EdgeType.TRIBUTE,
            value_flow=10.0,  # Tribute flow
        ),
        # TENANCY: All classes connected to territory
        Relationship(
            source_id="C001",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        ),
        Relationship(
            source_id="C002",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        ),
        Relationship(
            source_id="C003",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        ),
        Relationship(
            source_id="C004",
            target_id="T001",
            edge_type=EdgeType.TENANCY,
        ),
    ]

    # Global economy with rent pool
    # Pool size calibrated to exhaust within 5200 ticks (100 years) given:
    # - TRPF decay rate (defines.economy.rent_pool_decay) per tick (multiplicative)
    # - Wages bonus outflow depleting pool
    # Pool must drain below negligible (defines.economy.negligible_rent) for SUPERWAGE_CRISIS
    defines = GameDefines()
    economy = GlobalEconomy(
        imperial_rent_pool=defines.economy.initial_rent_pool,  # From defines.yaml
        current_super_wage_rate=defines.economy.super_wage_rate,  # From defines.yaml
        current_repression_level=defines.survival.default_repression,  # From defines.yaml
    )

    return WorldState(
        tick=0,
        entities=entities,
        territories=territories,
        relationships=relationships,
        economy=economy,
    )


@pytest.fixture
def imperial_circuit_state() -> WorldState:
    """Pre-built WorldState for carceral equilibrium tests."""
    return create_imperial_circuit_state()
