"""State Apparatus AI decision system (Feature 039).

Implements the state as a strategic adversary with three factional coalitions
(Finance-Capital, Security-State, Settler-Populist) that compete to shape
state behavior through a weighted objective function.

The state selects from six top-level verbs (ADMINISTER, DEVELOP, RESEARCH,
CO_OPT, REPRESS, WITHDRAW) and ~24 sub-verbs, constrained by budget and
attention thread resources.

See Also:
    ``specs/039-state-apparatus-ai/spec.md``: Full specification.
    :mod:`babylon.ooda.attention`: Attention thread intelligence system.
"""

from babylon.ooda.state_ai.administer_effects import (
    resolve_audit,
    resolve_fund,
    resolve_staff,
)
from babylon.ooda.state_ai.co_opt_effects import (
    compute_incorporate_probability,
    resolve_bribe,
    resolve_divide,
    resolve_propagandize,
)
from babylon.ooda.state_ai.decision import RuleBasedStateAI
from babylon.ooda.state_ai.faction_dynamics import (
    apply_fascist_overrides,
    apply_material_condition_shift,
    apply_player_action_shift,
    apply_repression_failure_shift,
    compute_stability,
    renormalize_faction_balance,
)
from babylon.ooda.state_ai.legislate_effects import (
    consume_legal_framework_effects,
)
from babylon.ooda.state_ai.observability import (
    create_observable_action,
    create_territory_observables,
    resolve_counter_intel,
)
from babylon.ooda.state_ai.repress_effects import (
    compute_raid_consciousness_effect,
    resolve_infiltrate,
    resolve_liquidate,
    resolve_prosecute,
    resolve_raid,
)
from babylon.ooda.state_ai.territory_effects import (
    assess_territory_threat,
    check_recruit_effectiveness,
    compute_heat_accumulation,
    compute_heat_decay,
    compute_propagandize_effect,
    compute_scorched_earth_legitimacy,
    resolve_displace,
    resolve_eviction_cascade,
    resolve_invest,
    resolve_neglect,
    resolve_scorched_earth,
    resolve_strategic_withdrawal,
)

__all__ = [
    "RuleBasedStateAI",
    "apply_fascist_overrides",
    "apply_material_condition_shift",
    "apply_player_action_shift",
    "apply_repression_failure_shift",
    "assess_territory_threat",
    "check_recruit_effectiveness",
    "compute_heat_accumulation",
    "compute_heat_decay",
    "compute_incorporate_probability",
    "compute_propagandize_effect",
    "compute_raid_consciousness_effect",
    "compute_scorched_earth_legitimacy",
    "compute_stability",
    "consume_legal_framework_effects",
    "create_observable_action",
    "create_territory_observables",
    "renormalize_faction_balance",
    "resolve_audit",
    "resolve_bribe",
    "resolve_counter_intel",
    "resolve_displace",
    "resolve_divide",
    "resolve_eviction_cascade",
    "resolve_fund",
    "resolve_infiltrate",
    "resolve_invest",
    "resolve_liquidate",
    "resolve_neglect",
    "resolve_propagandize",
    "resolve_prosecute",
    "resolve_raid",
    "resolve_scorched_earth",
    "resolve_staff",
    "resolve_strategic_withdrawal",
]
