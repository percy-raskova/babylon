//! Exact captured sharing permissions and dated household reports.
use super::{
    OrganizerConfig, OrganizerError, OrganizerObservation, OrganizerPeriodJournalEntries,
    OrganizerReport, OrganizerState,
};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerReportCommodity {
    pub good_id: [u8; 32],
    pub unit_id: [u8; 32],
    pub label: String,
    pub unit_label: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrganizerSharingBasis {
    Designed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrganizerReportBasis {
    Derived,
}

/// An empty scope withholds that topic. No permission derives from receiving or practice.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerReportSharing {
    pub evidence_class: OrganizerSharingBasis,
    pub food: Vec<OrganizerReportCommodity>,
    pub essential_services: Vec<OrganizerReportCommodity>,
    pub participation_time: Vec<[u8; 32]>,
}

impl OrganizerReportSharing {
    #[must_use]
    pub const fn withheld() -> Self {
        Self {
            evidence_class: OrganizerSharingBasis::Designed,
            food: vec![],
            essential_services: vec![],
            participation_time: vec![],
        }
    }

    pub(super) fn valid(&self) -> bool {
        let valid = |c: &OrganizerReportCommodity| {
            c.good_id != [0; 32]
                && c.unit_id != [0; 32]
                && super::contract::label_valid(&c.label)
                && super::contract::label_valid(&c.unit_label)
                && !c.label.trim().is_empty()
                && !c.unit_label.trim().is_empty()
        };
        self.essential_services.len() <= super::contract::MAX_ORGANIZER_ROWS
            && self.food.len() <= 1
            && self.participation_time.len() <= 1
            && self.participation_time.iter().all(|id| *id != [0; 32])
            && self.food.iter().chain(&self.essential_services).all(valid)
            && self
                .essential_services
                .windows(2)
                .all(|w| w[0].good_id < w[1].good_id)
            && !self.food.iter().any(|f| {
                self.essential_services
                    .iter()
                    .any(|s| f.good_id == s.good_id)
            })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerServiceReport {
    pub commodity: OrganizerReportCommodity,
    pub required: u64,
    pub performed: u64,
    pub satisfied: u64,
    pub unmet: u64,
    pub unused: u64,
    pub expired: u64,
    #[serde(with = "super::nonnegative_decimal_i128")]
    pub settled_micros: i128,
    #[serde(with = "super::nonnegative_decimal_i128")]
    pub refunded_micros: i128,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "basis", rename_all = "snake_case", deny_unknown_fields)]
pub enum OrganizerPartnerFacts {
    OpeningAssessment {
        commodity: OrganizerReportCommodity,
        required: u64,
        opening_stock: u64,
    },
    FoodProvision {
        commodity: OrganizerReportCommodity,
        required: u64,
        consumed: u64,
        unmet: u64,
        closing: u64,
        purchased: u64,
        #[serde(with = "super::nonnegative_decimal_i128")]
        settled_micros: i128,
    },
    EssentialServices {
        services: Vec<OrganizerServiceReport>,
    },
    ParticipationTime {
        labor_unit: [u8; 32],
        attended: u64,
        protected: u64,
        unpaid: u64,
        contributed: u64,
        remaining: u64,
    },
}

impl OrganizerPartnerFacts {
    pub(super) const fn report_kind(&self) -> u8 {
        match self {
            Self::OpeningAssessment { .. } | Self::FoodProvision { .. } => 3,
            Self::EssentialServices { .. } => 4,
            Self::ParticipationTime { .. } => 5,
        }
    }

    #[must_use]
    pub const fn title(&self) -> &'static str {
        match self {
            Self::OpeningAssessment { .. } => "Opening food assessment",
            Self::FoodProvision { .. } => "Food provision",
            Self::EssentialServices { .. } => "Essential services",
            Self::ParticipationTime { .. } => "Completed participation time",
        }
    }

    #[must_use]
    pub fn detail(&self) -> String {
        match self {
            Self::OpeningAssessment { commodity, required, opening_stock } => format!("Opening food assessment. {opening_stock} {} on hand. Current requirement {required}.", commodity.unit_label),
            Self::FoodProvision { commodity, required, consumed, unmet, closing, purchased, settled_micros } => format!("{} required {required} {}, consumed {consumed}, unmet {unmet}, closing stock {closing}. Ordinary purchases {purchased}, settled {settled_micros} currency micros.", commodity.label, commodity.unit_label),
            Self::EssentialServices { services } => services.iter().map(|s| format!("{} ({}). Required {}, performed {}, satisfied {}, unmet {}, unused {}, expired {}. Settled {} currency micros, refunded {}.",s.commodity.label,s.commodity.unit_label,s.required,s.performed,s.satisfied,s.unmet,s.unused,s.expired,s.settled_micros,s.refunded_micros)).collect::<Vec<_>>().join(" "),
            Self::ParticipationTime { attended, protected, unpaid, contributed, remaining, .. } => format!("Completed labor-hours. Attended {attended}, protected {protected}, unpaid work {unpaid}, contributions {contributed}, remaining {remaining}."),
        }
    }

    fn permitted(&self, scope: &OrganizerReportSharing, period: u64) -> bool {
        match self {
            Self::OpeningAssessment { commodity, .. } => {
                period == 0 && scope.food.contains(commodity)
            }
            Self::FoodProvision {
                commodity,
                required,
                consumed,
                unmet,
                settled_micros,
                ..
            } => {
                period > 0
                    && scope.food.contains(commodity)
                    && *settled_micros >= 0
                    && consumed.checked_add(*unmet) == Some(*required)
            }
            Self::EssentialServices { services } => {
                period > 0
                    && !services.is_empty()
                    && services
                        .iter()
                        .map(|s| &s.commodity)
                        .eq(&scope.essential_services)
                    && services.iter().all(|s| {
                        s.settled_micros >= 0
                            && s.refunded_micros >= 0
                            && s.satisfied.checked_add(s.unmet) == Some(s.required)
                            && s.satisfied.checked_add(s.unused) == Some(s.performed)
                    })
            }
            Self::ParticipationTime { labor_unit, .. } => {
                period > 0 && scope.participation_time.contains(labor_unit)
            }
        }
    }
}

/// Identify a report separately from gift dispatch or practice. The captured source is
/// authenticated here without exposing private household IDs to the reader.
/// # Errors
/// Refuses topics outside the partner's explicit grant or dates outside causal order.
pub fn partner_observation(
    config: &OrganizerConfig,
    subject: u64,
    observed: u64,
    acquired: u64,
    facts: OrganizerPartnerFacts,
) -> Result<OrganizerObservation, OrganizerError> {
    let binding = config
        .aid_bindings
        .iter()
        .find(|r| r.partner.actor_id == subject)
        .ok_or(OrganizerError::InvalidConfig)?;
    if observed > acquired || !facts.permitted(&binding.report_sharing, observed) {
        return Err(OrganizerError::InvalidState);
    }
    let report = OrganizerReport::Partner {
        evidence_class: OrganizerReportBasis::Derived,
        facts,
    };
    let observation_id = super::contract::identity(
        b"babylon.organizer-partner-report.v1",
        &(
            config.campaign_id,
            config.controlled_actor_id,
            subject,
            binding.source_hash,
            observed,
            acquired,
            &report,
        ),
    )?;
    Ok(OrganizerObservation {
        observation_id,
        actor_id: config.controlled_actor_id,
        subject_id: subject,
        source_actor_id: subject,
        observed_period: observed,
        acquired_period: acquired,
        receipt_id: None,
        report,
    })
}

pub(super) fn allowed(config: &OrganizerConfig, row: &OrganizerObservation) -> bool {
    if let OrganizerReport::Partner { facts, .. } = &row.report {
        return partner_observation(
            config,
            row.subject_id,
            row.observed_period,
            row.acquired_period,
            facts.clone(),
        )
        .as_ref()
            == Ok(row);
    }
    row.subject_id == config.workplace_id
        && row.source_actor_id == config.workplace_partner.actor_id
}

/// Publish only actual permitted facts to the same compact index and period journal.
/// # Errors
/// Refuses a duplicate or mismatched dated report.
pub fn record_partner_report(
    config: &OrganizerConfig,
    state: &mut OrganizerState,
    entries: &mut OrganizerPeriodJournalEntries,
    subject: u64,
    facts: OrganizerPartnerFacts,
) -> Result<(), OrganizerError> {
    if state.period != entries.period {
        return Err(OrganizerError::PeriodMismatch);
    }
    let observation = partner_observation(config, subject, entries.period, entries.period, facts)?;
    if entries.observations.iter().any(|r| {
        r.subject_id == subject && r.report.kind_index() == observation.report.kind_index()
    }) {
        return Err(OrganizerError::InvalidState);
    }
    let row = super::contract::learned_authority_index(std::slice::from_ref(&observation))
        .pop()
        .ok_or(OrganizerError::InvalidState)?;
    super::contract::upsert_learned_authority(&mut state.learned_authority_index, row);
    entries.observations.push(observation);
    Ok(())
}
