"""The electoral fixture — the ambient machine's producer layer (P25 U5, ADR131).

Seeds the American terrain the-electoral-question.md §2.1 names at minimum:
the two duopoly machines (LIBERAL_IMPERIAL- and RESTORATIONIST-aligned, in
spec-070 faction terms) plus two latent currents (social-democratic, fascist)
that exist as parties-in-waiting until crystallization or player entry; a
finance donor whose TRANSACTIONAL flows carry the donor-dependence
differential (the duopoly is funded, the socdem current is not); and weighted
MEMBERSHIP edges from each party into its class base.

Built ON the two_node substrate (worker + owner + territory + the
exploitation/wages/tenancy triangle) so every downstream system sees a
complete material base. NOT one of the six qa:regression scenarios —
byte-safety by disjointness; the engine derivation of political-labor flows
(GraphInputs.political_labor_share) is U8's work, not this builder's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.engine.scenarios.base import Scenario
from babylon.models.entities.organization import Business, PoliticalFaction
from babylon.models.entities.relationship import Relationship
from babylon.models.enums import ClassCharacter, EdgeType

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.models.config import SimulationConfig
    from babylon.models.world_state import WorldState

_WORKER = "C001"
_OWNER = "C002"


def _party(
    org_id: str, name: str, ideology: str, class_character: ClassCharacter
) -> PoliticalFaction:
    return PoliticalFaction(
        id=org_id,
        name=name,
        ideology=ideology,
        class_character=class_character,
        territory_ids=["T001"],
    )


def _membership(party_id: str, class_id: str) -> Relationship:
    return Relationship(
        source_id=party_id,
        target_id=class_id,
        edge_type=EdgeType.MEMBERSHIP,
        description=f"{party_id} base among {class_id}",
    )


def _funding(donor_id: str, party_id: str, amount: float) -> Relationship:
    return Relationship(
        source_id=donor_id,
        target_id=party_id,
        edge_type=EdgeType.TRANSACTIONAL,
        value_flow=amount,
        description=f"{donor_id} funds {party_id}",
    )


def create_electoral_fixture_scenario() -> tuple[WorldState, SimulationConfig, GameDefines]:
    """Build the electoral terrain on the two_node material substrate."""
    from babylon.engine.scenarios._legacy import create_two_node_scenario

    state, config, defines = create_two_node_scenario()

    parties = {
        "org/party-liberal": _party(
            "org/party-liberal",
            "Liberal-Imperial Machine",
            "liberal_imperial",
            ClassCharacter.BOURGEOIS,
        ),
        "org/party-restorationist": _party(
            "org/party-restorationist",
            "Restorationist Machine",
            "restorationist",
            ClassCharacter.PETTY_BOURGEOIS,
        ),
        "org/party-socdem": _party(
            "org/party-socdem",
            "Social-Democratic Current",
            "social_democratic",
            ClassCharacter.PROLETARIAN,
        ),
        "org/party-fascist": _party(
            "org/party-fascist",
            "Fascist Current",
            "fascist",
            ClassCharacter.PETTY_BOURGEOIS,
        ),
    }
    donor = Business(
        id="org/donor-finance",
        name="Finance Capital Donor Bloc",
        class_character=ClassCharacter.BOURGEOIS,
        sector="finance",
        territory_ids=["T001"],
    )

    relationships = [
        *state.relationships,
        # Each party's class base: the duopoly reaches across classes; the
        # currents are class-concentrated (the L-PRZ terrain in miniature).
        _membership("org/party-liberal", _WORKER),
        _membership("org/party-liberal", _OWNER),
        _membership("org/party-restorationist", _OWNER),
        _membership("org/party-socdem", _WORKER),
        _membership("org/party-fascist", _OWNER),
        # Donor dependence: the duopoly is funded; the socdem current is not
        # (its platform derives from base composition alone); the fascist
        # current draws a trickle (the reactionary financier hedge).
        _funding("org/donor-finance", "org/party-liberal", 100.0),
        _funding("org/donor-finance", "org/party-restorationist", 100.0),
        _funding("org/donor-finance", "org/party-fascist", 10.0),
    ]

    state = state.model_copy(
        update={
            "organizations": {**state.organizations, **parties, donor.id: donor},
            "relationships": relationships,
        }
    )
    return state, config, defines


class ElectoralFixtureScenario(Scenario):
    """Scenario wrapper for the electoral terrain fixture."""

    name: ClassVar[str] = "electoral_fixture"
    description: ClassVar[str] = (
        "Two duopoly machines + two latent currents + a finance donor on the "
        "two_node material substrate (P25 U5)."
    )

    def build(
        self, *_args: Any, **_kwargs: Any
    ) -> tuple[WorldState, SimulationConfig, GameDefines]:
        """Build the electoral terrain (ignores args; the substrate takes none)."""
        return create_electoral_fixture_scenario()
