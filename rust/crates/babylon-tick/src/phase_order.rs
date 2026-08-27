//! Executable BSL phase ordering (PER-17).
//!
//! The frozen Python registry is the transcription oracle for the 34-slot
//! causal spine. BSL rule IDs inherit one governed system home, while an
//! explicit `(anchor :before|:after <system>)` selects a boundary around a
//! governed slot. Rules sharing one resolved position retain D16's ascending
//! rule-ID byte order. Source and file order are never observable.
//!
//! [`schedule_digest`] fingerprints the governed scheduling law, not one
//! content pack. Its version-1 canonical bytes are: the fixed domain string
//! `babylon.phase-schedule\0`; a big-endian `u32` layout version; a
//! big-endian `u32` slot count; then each canonical slot in governed order as
//! `str name | u8 partition | u8 ordinal | u16 default-rank`; then a
//! big-endian `u32` alias count and each alias sorted by alias name as
//! `str alias | str canonical | u16 resolved-default-rank`. Here `str` is a
//! big-endian `u32` UTF-8 byte length followed by the raw UTF-8 bytes.

use babylon_bsl::mod_anchors::{check_anchor, AnchorDecl, AnchorError, AnchorPosition};
use babylon_bsl::reader::SExpr;
use babylon_bsl::same_tick_order::RankedRule;
use babylon_kernel::sha256_of;
use std::collections::TryReserveError;
use std::collections::{BTreeMap, HashSet};

const MATERIAL_BASE_COUNT: usize = 15;
const ACTION_COUNT: usize = 1;
const CONSEQUENCE_COUNT: usize = 18;
const SYSTEM_COUNT: usize = MATERIAL_BASE_COUNT + ACTION_COUNT + CONSEQUENCE_COUNT;
const AFTER_MATERIAL_BASE_RANK: usize = MATERIAL_BASE_COUNT * 2;
const SCHEDULE_DIGEST_LAYOUT_VERSION: u32 = 1;
const SCHEDULE_DIGEST_DOMAIN: &[u8] = b"babylon.phase-schedule\0";

/// The three contiguous causal partitions.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TickPartition {
    MaterialBase,
    Action,
    Consequence,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct SystemSlot {
    name: &'static str,
    partition: TickPartition,
    ordinal: u8,
}

const SYSTEM_SLOTS: [SystemSlot; SYSTEM_COUNT] = [
    SystemSlot {
        name: "vitality",
        partition: TickPartition::MaterialBase,
        ordinal: 0,
    },
    SystemSlot {
        name: "territory",
        partition: TickPartition::MaterialBase,
        ordinal: 1,
    },
    SystemSlot {
        name: "substrate",
        partition: TickPartition::MaterialBase,
        ordinal: 2,
    },
    SystemSlot {
        name: "production",
        partition: TickPartition::MaterialBase,
        ordinal: 3,
    },
    SystemSlot {
        name: "tick-dynamics",
        partition: TickPartition::MaterialBase,
        ordinal: 4,
    },
    SystemSlot {
        name: "reserve-army",
        partition: TickPartition::MaterialBase,
        ordinal: 5,
    },
    SystemSlot {
        name: "community",
        partition: TickPartition::MaterialBase,
        ordinal: 6,
    },
    SystemSlot {
        name: "lifecycle",
        partition: TickPartition::MaterialBase,
        ordinal: 7,
    },
    SystemSlot {
        name: "solidarity",
        partition: TickPartition::MaterialBase,
        ordinal: 8,
    },
    SystemSlot {
        name: "imperial-rent",
        partition: TickPartition::MaterialBase,
        ordinal: 9,
    },
    SystemSlot {
        name: "transport",
        partition: TickPartition::MaterialBase,
        ordinal: 10,
    },
    SystemSlot {
        name: "dispossession",
        partition: TickPartition::MaterialBase,
        ordinal: 11,
    },
    SystemSlot {
        name: "decomposition",
        partition: TickPartition::MaterialBase,
        ordinal: 12,
    },
    SystemSlot {
        name: "control-ratio",
        partition: TickPartition::MaterialBase,
        ordinal: 13,
    },
    SystemSlot {
        name: "metabolism",
        partition: TickPartition::MaterialBase,
        ordinal: 14,
    },
    SystemSlot {
        name: "ooda",
        partition: TickPartition::Action,
        ordinal: 15,
    },
    SystemSlot {
        name: "faction-influence",
        partition: TickPartition::Consequence,
        ordinal: 16,
    },
    SystemSlot {
        name: "doctrine",
        partition: TickPartition::Consequence,
        ordinal: 17,
    },
    SystemSlot {
        name: "survival",
        partition: TickPartition::Consequence,
        ordinal: 18,
    },
    SystemSlot {
        name: "struggle",
        partition: TickPartition::Consequence,
        ordinal: 19,
    },
    SystemSlot {
        name: "consciousness",
        partition: TickPartition::Consequence,
        ordinal: 20,
    },
    SystemSlot {
        name: "fascist-faction",
        partition: TickPartition::Consequence,
        ordinal: 21,
    },
    SystemSlot {
        name: "allegiance",
        partition: TickPartition::Consequence,
        ordinal: 22,
    },
    SystemSlot {
        name: "electoral",
        partition: TickPartition::Consequence,
        ordinal: 23,
    },
    SystemSlot {
        name: "policy",
        partition: TickPartition::Consequence,
        ordinal: 24,
    },
    SystemSlot {
        name: "sovereignty",
        partition: TickPartition::Consequence,
        ordinal: 25,
    },
    SystemSlot {
        name: "market-scissors",
        partition: TickPartition::Consequence,
        ordinal: 26,
    },
    SystemSlot {
        name: "contradiction",
        partition: TickPartition::Consequence,
        ordinal: 27,
    },
    SystemSlot {
        name: "contradiction-field",
        partition: TickPartition::Consequence,
        ordinal: 28,
    },
    SystemSlot {
        name: "field-derivative",
        partition: TickPartition::Consequence,
        ordinal: 29,
    },
    SystemSlot {
        name: "collapse-transition",
        partition: TickPartition::Consequence,
        ordinal: 30,
    },
    SystemSlot {
        name: "edge-transition",
        partition: TickPartition::Consequence,
        ordinal: 31,
    },
    SystemSlot {
        name: "wealth-distribution",
        partition: TickPartition::Consequence,
        ordinal: 32,
    },
    SystemSlot {
        name: "epistemic-horizon",
        partition: TickPartition::Consequence,
        ordinal: 33,
    },
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct SystemAlias {
    name: &'static str,
    canonical: &'static str,
}

/// Compatibility homes for already-landed content and conformance fixtures.
const SYSTEM_ALIASES: [SystemAlias; 4] = [
    SystemAlias {
        name: "class-dynamics",
        canonical: "tick-dynamics",
    },
    SystemAlias {
        name: "economics",
        canonical: "contradiction",
    },
    SystemAlias {
        name: "organization",
        canonical: "ooda",
    },
    SystemAlias {
        name: "social-class",
        canonical: "solidarity",
    },
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
struct ExecutionKey(u16);

#[derive(Debug, Clone, PartialEq, Eq)]
struct PlannedRule {
    id: String,
    key: ExecutionKey,
}

/// A validated, deterministic content-set order compiled before hydration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct RuleOrderPlan {
    rules: Vec<PlannedRule>,
}

/// Exact canonical identity of the governed causal schedule.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct PhaseScheduleV1 {
    canonical_bytes: Vec<u8>,
    digest: [u8; 32],
}

impl PhaseScheduleV1 {
    pub(crate) const fn layout_version() -> u32 {
        SCHEDULE_DIGEST_LAYOUT_VERSION
    }

    pub(crate) fn canonical_bytes(&self) -> &[u8] {
        &self.canonical_bytes
    }

    pub(crate) const fn digest(&self) -> [u8; 32] {
        self.digest
    }
}

/// A loud phase-registry or composition failure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum ScheduleError {
    Anchor {
        rule_id: String,
        source: AnchorError,
    },
    MaterialBaseInterleave {
        rule_id: String,
        position: AnchorPosition,
        system: String,
    },
    Registry {
        message: String,
    },
    Allocation {
        requested: usize,
    },
    CapacityOverflow {
        field: &'static str,
    },
    Plan {
        rule_id: Option<String>,
        message: String,
    },
}

impl std::fmt::Display for ScheduleError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Anchor { source, .. } => write!(f, "{source}"),
            Self::MaterialBaseInterleave {
                rule_id,
                position,
                system,
            } => write!(
                f,
                "E-LOAD-003: rule {rule_id}'s explicit anchor :{} {system} cuts through the \
                 interior of the Material Base partition — mods may target the boundary \
                 before vitality or after metabolism, but cannot splice incidental order \
                 into the governed material causal spine (§2.3)",
                match position {
                    AnchorPosition::Before => "before",
                    AnchorPosition::After => "after",
                }
            ),
            Self::Registry { message } => write!(f, "invalid phase registry: {message}"),
            Self::Allocation { requested } => {
                write!(f, "phase schedule allocation of {requested} bytes failed")
            }
            Self::CapacityOverflow { field } => {
                write!(f, "phase schedule capacity overflowed while sizing {field}")
            }
            Self::Plan { message, .. } => write!(f, "invalid phase-order plan: {message}"),
        }
    }
}

impl std::error::Error for ScheduleError {}

/// Every canonical and compatibility system name accepted by BSL loading.
pub(crate) fn registered_systems() -> HashSet<String> {
    SYSTEM_SLOTS
        .iter()
        .map(|slot| slot.name.to_owned())
        .chain(SYSTEM_ALIASES.iter().map(|alias| alias.name.to_owned()))
        .collect()
}

/// SHA-256 of the versioned, canonical 34-slot scheduling law.
pub(crate) fn schedule_digest() -> Result<[u8; 32], ScheduleError> {
    Ok(phase_schedule_v1()?.digest())
}

/// Exact versioned bytes of the governed 34-slot scheduling law.
pub(crate) fn phase_schedule_v1() -> Result<PhaseScheduleV1, ScheduleError> {
    validate_registry()?;
    let capacity = phase_schedule_capacity()?;
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(capacity)
        .map_err(|_: TryReserveError| ScheduleError::Allocation {
            requested: capacity,
        })?;
    bytes.extend_from_slice(SCHEDULE_DIGEST_DOMAIN);
    bytes.extend_from_slice(&SCHEDULE_DIGEST_LAYOUT_VERSION.to_be_bytes());
    push_schedule_count(&mut bytes, SYSTEM_SLOTS.len(), "canonical slots")?;
    for slot in SYSTEM_SLOTS {
        push_schedule_str(&mut bytes, slot.name)?;
        bytes.push(partition_tag(slot.partition));
        bytes.push(slot.ordinal);
        bytes.extend_from_slice(&default_rank(slot)?.to_be_bytes());
    }

    let mut aliases: Vec<&SystemAlias> = SYSTEM_ALIASES.iter().collect();
    aliases.sort_unstable_by(|a, b| a.name.as_bytes().cmp(b.name.as_bytes()));
    push_schedule_count(&mut bytes, aliases.len(), "system aliases")?;
    for alias in aliases {
        push_schedule_str(&mut bytes, alias.name)?;
        push_schedule_str(&mut bytes, alias.canonical)?;
        let slot = SYSTEM_SLOTS
            .iter()
            .find(|slot| slot.name == alias.canonical)
            .ok_or_else(|| ScheduleError::Registry {
                message: format!("system alias {} has no canonical slot", alias.name),
            })?;
        bytes.extend_from_slice(&default_rank(*slot)?.to_be_bytes());
    }
    debug_assert_eq!(bytes.len(), capacity);
    let digest = sha256_of(&bytes);
    Ok(PhaseScheduleV1 {
        canonical_bytes: bytes,
        digest,
    })
}

fn phase_schedule_capacity() -> Result<usize, ScheduleError> {
    let mut total =
        SCHEDULE_DIGEST_DOMAIN
            .len()
            .checked_add(8)
            .ok_or(ScheduleError::CapacityOverflow {
                field: "schedule header",
            })?;
    for slot in SYSTEM_SLOTS {
        let row = slot
            .name
            .len()
            .checked_add(8)
            .ok_or(ScheduleError::CapacityOverflow {
                field: "schedule slot",
            })?;
        total = total
            .checked_add(row)
            .ok_or(ScheduleError::CapacityOverflow {
                field: "schedule slots",
            })?;
    }
    total = total
        .checked_add(4)
        .ok_or(ScheduleError::CapacityOverflow {
            field: "schedule alias count",
        })?;
    for alias in SYSTEM_ALIASES {
        let row = alias
            .name
            .len()
            .checked_add(alias.canonical.len())
            .and_then(|value| value.checked_add(10))
            .ok_or(ScheduleError::CapacityOverflow {
                field: "schedule alias",
            })?;
        total = total
            .checked_add(row)
            .ok_or(ScheduleError::CapacityOverflow {
                field: "schedule aliases",
            })?;
    }
    Ok(total)
}

fn push_schedule_count(bytes: &mut Vec<u8>, count: usize, what: &str) -> Result<(), ScheduleError> {
    let count = u32::try_from(count).map_err(|_| ScheduleError::Registry {
        message: format!("{what} count {count} exceeds u32"),
    })?;
    bytes.extend_from_slice(&count.to_be_bytes());
    Ok(())
}

fn push_schedule_str(bytes: &mut Vec<u8>, value: &str) -> Result<(), ScheduleError> {
    push_schedule_count(bytes, value.len(), "schedule string bytes")?;
    bytes.extend_from_slice(value.as_bytes());
    Ok(())
}

fn partition_tag(partition: TickPartition) -> u8 {
    match partition {
        TickPartition::MaterialBase => 0,
        TickPartition::Action => 1,
        TickPartition::Consequence => 2,
    }
}

fn default_rank(slot: SystemSlot) -> Result<u16, ScheduleError> {
    u16::from(slot.ordinal)
        .checked_mul(2)
        .and_then(|rank| rank.checked_add(1))
        .ok_or_else(|| ScheduleError::Registry {
            message: format!("default execution rank overflow for system {}", slot.name),
        })
}

/// Compile raw rule forms into their total execution order.
pub(crate) fn compile(rule_forms: &[(String, SExpr)]) -> Result<RuleOrderPlan, ScheduleError> {
    validate_registry()?;
    let systems = registered_systems();
    let mut planned = Vec::with_capacity(rule_forms.len());
    let mut validation_order: Vec<_> = rule_forms.iter().collect();
    validation_order.sort_by(|(a, _), (b, _)| a.as_bytes().cmp(b.as_bytes()));
    for (id, form) in validation_order {
        let anchor = check_anchor(form, &systems).map_err(|source| ScheduleError::Anchor {
            rule_id: id.clone(),
            source,
        })?;
        let key = execution_key(id, anchor.as_ref())?;
        if let Some(anchor) = anchor {
            if is_material_base_interior(key) {
                return Err(ScheduleError::MaterialBaseInterleave {
                    rule_id: id.clone(),
                    position: anchor.position,
                    system: anchor.system,
                });
            }
        }
        planned.push(PlannedRule {
            id: id.clone(),
            key,
        });
    }
    planned.sort_by(|a, b| {
        a.key
            .cmp(&b.key)
            .then_with(|| a.id.as_bytes().cmp(b.id.as_bytes()))
    });
    Ok(RuleOrderPlan { rules: planned })
}

impl RuleOrderPlan {
    /// Pair each source form with this plan's resolved execution rank without
    /// consuming the plan.
    ///
    /// The same identity and cardinality checks [`Self::apply`] performs keep
    /// the analyzer view total: every returned rule has exactly one compiled
    /// rank and no source form can be silently dropped or substituted.
    pub(crate) fn ranked_rules<'a>(
        &self,
        rules: &'a [(String, SExpr)],
    ) -> Result<Vec<RankedRule<'a>>, ScheduleError> {
        if self.rules.len() != rules.len() {
            return Err(ScheduleError::Plan {
                rule_id: None,
                message: format!(
                    "compiled {} rule ids but rank analysis received {} rule forms",
                    self.rules.len(),
                    rules.len()
                ),
            });
        }
        let mut by_id = BTreeMap::new();
        for (id, form) in rules {
            if by_id.insert(id.as_str(), (id.as_str(), form)).is_some() {
                return Err(ScheduleError::Plan {
                    rule_id: Some(id.clone()),
                    message: "one rank-analysis rule id appeared twice".to_owned(),
                });
            }
        }
        let mut ranked = Vec::with_capacity(self.rules.len());
        for row in &self.rules {
            let Some((input_id, form)) = by_id.remove(row.id.as_str()) else {
                return Err(ScheduleError::Plan {
                    rule_id: Some(row.id.clone()),
                    message: "a compiled rule id was absent from rank analysis".to_owned(),
                });
            };
            ranked.push(RankedRule {
                rule_id: input_id,
                execution_rank: row.key.0,
                form,
            });
        }
        if let Some((id, _)) = by_id.into_iter().next() {
            return Err(ScheduleError::Plan {
                rule_id: Some(id.to_owned()),
                message: "a rank-analysis rule id was absent from the compiled order".to_owned(),
            });
        }
        Ok(ranked)
    }

    /// Apply this already-validated order to the corresponding loaded rules.
    pub(crate) fn apply<T>(
        self,
        rules: Vec<(String, T)>,
    ) -> Result<Vec<(String, T)>, ScheduleError> {
        if self.rules.len() != rules.len() {
            return Err(ScheduleError::Plan {
                rule_id: None,
                message: format!(
                    "compiled {} rule ids but loading produced {} rules",
                    self.rules.len(),
                    rules.len()
                ),
            });
        }
        let mut by_id = BTreeMap::new();
        for (id, loaded) in rules {
            if by_id.insert(id.clone(), loaded).is_some() {
                return Err(ScheduleError::Plan {
                    rule_id: Some(id),
                    message: "one loaded rule id appeared twice".to_owned(),
                });
            }
        }
        let mut ordered = Vec::with_capacity(self.rules.len());
        for row in self.rules {
            let Some(loaded) = by_id.remove(&row.id) else {
                return Err(ScheduleError::Plan {
                    rule_id: Some(row.id),
                    message: "a compiled rule id was absent after loading".to_owned(),
                });
            };
            ordered.push((row.id, loaded));
        }
        if let Some((id, _)) = by_id.into_iter().next() {
            return Err(ScheduleError::Plan {
                rule_id: Some(id),
                message: "a loaded rule id was absent from the compiled order".to_owned(),
            });
        }
        Ok(ordered)
    }
}

fn execution_key(
    rule_id: &str,
    anchor: Option<&AnchorDecl>,
) -> Result<ExecutionKey, ScheduleError> {
    let (system, offset) = match anchor {
        Some(anchor) => (
            anchor.system.as_str(),
            match anchor.position {
                AnchorPosition::Before => 0_u16,
                AnchorPosition::After => 2_u16,
            },
        ),
        None => (rule_id.split('/').next().unwrap_or_default(), 1_u16),
    };
    let index = system_index(system).ok_or_else(|| ScheduleError::Plan {
        rule_id: Some(rule_id.to_owned()),
        message: format!("registered system {system:?} has no governed slot"),
    })?;
    let ordinal = u16::try_from(index).map_err(|_| ScheduleError::Registry {
        message: format!("system index {index} exceeds u16"),
    })?;
    let rank = ordinal
        .checked_mul(2)
        .and_then(|base| base.checked_add(offset))
        .ok_or_else(|| ScheduleError::Registry {
            message: format!("execution rank overflow for system {system}"),
        })?;
    Ok(ExecutionKey(rank))
}

fn system_index(name: &str) -> Option<usize> {
    if let Some(index) = SYSTEM_SLOTS.iter().position(|slot| slot.name == name) {
        return Some(index);
    }
    let canonical = SYSTEM_ALIASES
        .iter()
        .find(|alias| alias.name == name)?
        .canonical;
    SYSTEM_SLOTS.iter().position(|slot| slot.name == canonical)
}

fn is_material_base_interior(key: ExecutionKey) -> bool {
    let rank = usize::from(key.0);
    rank > 0 && rank < AFTER_MATERIAL_BASE_RANK
}

fn validate_registry() -> Result<(), ScheduleError> {
    let mut names = HashSet::with_capacity(SYSTEM_COUNT + SYSTEM_ALIASES.len());
    for (index, slot) in SYSTEM_SLOTS.iter().enumerate() {
        let expected_ordinal = u8::try_from(index).map_err(|_| ScheduleError::Registry {
            message: format!("system index {index} exceeds u8"),
        })?;
        if slot.ordinal != expected_ordinal {
            return Err(ScheduleError::Registry {
                message: format!(
                    "system {} declares ordinal {} at index {index}",
                    slot.name, slot.ordinal
                ),
            });
        }
        let expected_partition = partition_at(index);
        if slot.partition != expected_partition {
            return Err(ScheduleError::Registry {
                message: format!("system {} breaks the 15/1/18 partition blocks", slot.name),
            });
        }
        if !names.insert(slot.name) {
            return Err(ScheduleError::Registry {
                message: format!("duplicate canonical system name {}", slot.name),
            });
        }
    }
    for alias in SYSTEM_ALIASES {
        if !names.insert(alias.name) {
            return Err(ScheduleError::Registry {
                message: format!("duplicate or colliding system alias {}", alias.name),
            });
        }
        if !SYSTEM_SLOTS.iter().any(|slot| slot.name == alias.canonical) {
            return Err(ScheduleError::Registry {
                message: format!(
                    "system alias {} names missing canonical target {}",
                    alias.name, alias.canonical
                ),
            });
        }
    }
    Ok(())
}

fn partition_at(index: usize) -> TickPartition {
    if index < MATERIAL_BASE_COUNT {
        TickPartition::MaterialBase
    } else if index < MATERIAL_BASE_COUNT + ACTION_COUNT {
        TickPartition::Action
    } else {
        TickPartition::Consequence
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_bsl::reader::read;

    fn form(source: &str) -> SExpr {
        read(source).expect("phase-order fixture parses").0
    }

    fn rule(id: &str, anchor: &str) -> (String, SExpr) {
        let source = format!(
            "(rule {id} :material-basis \"x\" :fuel 8 {anchor} \
             (bindings) (effects (emit EventType/RUPTURE)))"
        );
        (id.to_owned(), form(&source))
    }

    fn ids(plan: &RuleOrderPlan) -> Vec<&str> {
        plan.rules.iter().map(|row| row.id.as_str()).collect()
    }

    #[test]
    fn registry_matches_the_frozen_34_slot_spine() {
        let names: Vec<&str> = SYSTEM_SLOTS.iter().map(|slot| slot.name).collect();
        assert_eq!(
            names,
            [
                "vitality",
                "territory",
                "substrate",
                "production",
                "tick-dynamics",
                "reserve-army",
                "community",
                "lifecycle",
                "solidarity",
                "imperial-rent",
                "transport",
                "dispossession",
                "decomposition",
                "control-ratio",
                "metabolism",
                "ooda",
                "faction-influence",
                "doctrine",
                "survival",
                "struggle",
                "consciousness",
                "fascist-faction",
                "allegiance",
                "electoral",
                "policy",
                "sovereignty",
                "market-scissors",
                "contradiction",
                "contradiction-field",
                "field-derivative",
                "collapse-transition",
                "edge-transition",
                "wealth-distribution",
                "epistemic-horizon",
            ]
        );
        validate_registry().expect("the governed registry is internally valid");
    }

    #[test]
    fn schedule_law_digest_pins_slots_partitions_ranks_and_sorted_aliases() {
        let schedule = phase_schedule_v1().expect("the governed schedule encodes");
        assert_eq!(PhaseScheduleV1::layout_version(), 1);
        assert!(schedule
            .canonical_bytes()
            .starts_with(b"babylon.phase-schedule\0"));
        assert_eq!(
            crate::hex(&schedule.digest()),
            "3cb992b960112948023e5fcfa1335f2a6e6270628f27fe758186bc9c4d6b2487"
        );
        assert_eq!(schedule_digest().unwrap(), schedule.digest());
    }

    #[test]
    fn partitions_are_contiguous_fifteen_one_eighteen() {
        let base = SYSTEM_SLOTS
            .iter()
            .filter(|slot| slot.partition == TickPartition::MaterialBase)
            .count();
        let action = SYSTEM_SLOTS
            .iter()
            .filter(|slot| slot.partition == TickPartition::Action)
            .count();
        let consequence = SYSTEM_SLOTS
            .iter()
            .filter(|slot| slot.partition == TickPartition::Consequence)
            .count();
        assert_eq!((base, action, consequence), (15, 1, 18));
    }

    #[test]
    fn default_homes_put_decomposition_before_control_ratio() {
        let input = vec![rule("control-ratio/z", ""), rule("decomposition/a", "")];
        assert_eq!(
            ids(&compile(&input).unwrap()),
            ["decomposition/a", "control-ratio/z"]
        );
    }

    #[test]
    fn an_explicit_anchor_overrides_the_rule_id_namespace() {
        let input = vec![
            rule("vitality/z", ""),
            rule("mods/a", "(anchor :before survival)"),
        ];
        assert_eq!(ids(&compile(&input).unwrap()), ["vitality/z", "mods/a"]);
    }

    #[test]
    fn one_position_ties_by_rule_id_bytes() {
        let input = vec![rule("vitality/z", ""), rule("vitality/a", "")];
        assert_eq!(ids(&compile(&input).unwrap()), ["vitality/a", "vitality/z"]);
    }

    #[test]
    fn ranked_rules_pair_each_form_with_its_resolved_rank_in_plan_order() {
        let input = vec![
            rule("mods/z-after-ooda", "(anchor :after ooda)"),
            rule(
                "mods/a-before-faction",
                "(anchor :before faction-influence)",
            ),
        ];
        let plan = compile(&input).expect("the shared boundary compiles");
        let ranked = plan
            .ranked_rules(&input)
            .expect("every compiled id has one source form");

        assert_eq!(ranked.len(), 2);
        assert_eq!(ranked[0].rule_id, "mods/a-before-faction");
        assert_eq!(ranked[1].rule_id, "mods/z-after-ooda");
        assert_eq!(ranked[0].execution_rank, ranked[1].execution_rank);
        assert!(std::ptr::eq(ranked[0].form, &input[1].1));
        assert!(std::ptr::eq(ranked[1].form, &input[0].1));
    }

    #[test]
    fn ranked_rules_refuse_cardinality_duplicate_and_identity_disagreement() {
        let input = vec![rule("vitality/a", ""), rule("vitality/z", "")];
        let plan = compile(&input).expect("the source plan compiles");

        let short = plan.ranked_rules(&input[..1]).unwrap_err();
        assert!(matches!(short, ScheduleError::Plan { rule_id: None, .. }));

        let duplicate = vec![input[0].clone(), input[0].clone()];
        let duplicate_error = plan.ranked_rules(&duplicate).unwrap_err();
        assert!(matches!(
            duplicate_error,
            ScheduleError::Plan {
                rule_id: Some(ref id),
                ..
            } if id == "vitality/a"
        ));

        let replacement = vec![input[0].clone(), rule("vitality/x", "")];
        let identity_error = plan.ranked_rules(&replacement).unwrap_err();
        assert!(matches!(
            identity_error,
            ScheduleError::Plan {
                rule_id: Some(ref id),
                ..
            } if id == "vitality/z"
        ));
    }

    #[test]
    fn after_previous_and_before_next_share_one_boundary() {
        let after = execution_key(
            "mods/z",
            Some(&AnchorDecl {
                position: AnchorPosition::After,
                system: "ooda".to_owned(),
            }),
        )
        .unwrap();
        let before = execution_key(
            "mods/a",
            Some(&AnchorDecl {
                position: AnchorPosition::Before,
                system: "faction-influence".to_owned(),
            }),
        )
        .unwrap();
        assert_eq!(after, before);
    }

    #[test]
    fn source_permutations_compile_to_the_same_order() {
        let a = rule("vitality/z", "");
        let b = rule("mods/a", "(anchor :before survival)");
        let forward = compile(&[a.clone(), b.clone()]).unwrap();
        let reversed = compile(&[b, a]).unwrap();
        assert_eq!(forward, reversed);
    }

    #[test]
    fn invalid_source_permutations_name_the_same_byte_least_rule() {
        let a = rule("mods/a-illegal", "(anchor :after vitality)");
        let z = rule("mods/z-illegal", "(anchor :before metabolism)");
        let forward = compile(&[z.clone(), a.clone()]).unwrap_err();
        let reversed = compile(&[a, z]).unwrap_err();

        assert_eq!(forward, reversed);
        assert!(matches!(
            forward,
            ScheduleError::MaterialBaseInterleave { ref rule_id, .. }
                if rule_id == "mods/a-illegal"
        ));
    }

    #[test]
    fn compatibility_names_have_governed_canonical_homes() {
        for (alias, canonical) in [
            ("class-dynamics", "tick-dynamics"),
            ("economics", "contradiction"),
            ("organization", "ooda"),
            ("social-class", "solidarity"),
        ] {
            assert_eq!(system_index(alias), system_index(canonical));
        }
    }

    #[test]
    fn material_base_boundary_anchors_are_legal_but_interior_anchors_are_not() {
        let post_base = execution_key(
            "mods/after-base",
            Some(&AnchorDecl {
                position: AnchorPosition::After,
                system: "metabolism".to_owned(),
            }),
        )
        .expect("the post-base boundary has a rank");
        assert_eq!(usize::from(post_base.0), AFTER_MATERIAL_BASE_RANK);
        compile(&[rule("mods/before-base", "(anchor :before vitality)")])
            .expect("the pre-base boundary is legal");
        compile(&[rule("mods/after-base", "(anchor :after metabolism)")])
            .expect("the post-base boundary is legal");
        let error = compile(&[rule("mods/interior", "(anchor :after vitality)")]).unwrap_err();
        assert!(matches!(
            error,
            ScheduleError::MaterialBaseInterleave { .. }
        ));
    }
}
