//! One company's material evidence and actual BSL draw from one committed observer snapshot.
use super::{ObserverEconomyError, ObserverEconomyReader, ObserverMaterialCursor};
use crate::economic_catalog::CapturedEconomicCatalog;
use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
use crate::michigan_economy;
use crate::national_economy::companies::CompanyKey;
use crate::observer_material::ObserverFrameClose;
use crate::runtime::RustPersistenceRuntimeError;
use crate::semantic_codec::ChoiceReceiptSemanticRow;
use babylon_bsl::probability::MASS_NANOUNITS_PER_UNIT;
use babylon_graph::stable_element::StableElementKey;
use babylon_material_circuit::{CompanyCondition, CompanyId, CompanyPortfolioEvidence, SiteId};
use babylon_tick::company_graph;
use serde::{Serialize, Serializer};
use serde_json::json;
use std::collections::BTreeMap;

const MEMBERS: [&str; 4] = [
    "DEFER",
    "REPLACEMENT_ONLY",
    "MODEST_EXPANSION",
    "LARGER_EXPANSION",
];

/// An authenticated material close and the kernel receipt for the same company and period.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompanyDecisionReport {
    pub campaign: CampaignId,
    pub foundation_sha256: [u8; 32],
    pub tick_content_hash: [u8; 32],
    pub company_label: String,
    pub evidence: CompanyPortfolioEvidence,
    pub encounter_ordinal: u32,
    pub selected_outcome: String,
    pub draw_ticket: u64,
}

#[derive(Clone, Default)]
pub(crate) struct CompanyDraws(BTreeMap<StableElementKey, CompanyDraw>);
#[derive(Clone, Copy)]
struct CompanyDraw {
    encounter: u32,
    ticket: u64,
    selected: usize,
    masses: [u64; 4],
}
impl CompanyDraws {
    /// Retain the same typed values encoded into the authenticated envelope.
    pub(crate) fn retain(
        &mut self,
        row: &ChoiceReceiptSemanticRow,
    ) -> Result<(), RustPersistenceRuntimeError> {
        if row.rule_id != "company/portfolio-investment" {
            return Ok(());
        }
        let invalid = RustPersistenceRuntimeError::CampaignConflict;
        if row.sample != "company/investment-portfolio"
            || row.slot != 0
            || row.outcome_enum != "CompanyPortfolio"
            || !row
                .branches
                .iter()
                .map(|b| b.outcome_member.as_str())
                .eq(MEMBERS)
        {
            return Err(invalid);
        }
        let selected = MEMBERS
            .iter()
            .position(|&member| member == row.selected_outcome)
            .ok_or(RustPersistenceRuntimeError::CampaignConflict)?;
        let masses = std::array::from_fn(|index| row.branches[index].mass_nanounits);
        let draw = CompanyDraw {
            encounter: row.encounter_ordinal,
            ticket: row.draw_ticket,
            selected,
            masses,
        };
        if masses[selected] == 0 || self.0.insert(row.stable_carrier.clone(), draw).is_some() {
            return Err(invalid);
        }
        Ok(())
    }
}
enum DecisionSubject {
    Company(CompanyId),
    Site(SiteId),
}
impl DecisionSubject {
    fn company_key(
        self,
        catalog: &CapturedEconomicCatalog,
    ) -> Result<Option<CompanyKey>, ObserverEconomyError> {
        let roster = catalog.national_companies();
        match self {
            Self::Company(company) => {
                let key = roster
                    .ok_or(ObserverEconomyError::CompanyPortfoliosNotCaptured)?
                    .companies
                    .iter()
                    .find(|row| row.key.id() == company)
                    .ok_or(ObserverEconomyError::CompanyDecisionAbsent)?
                    .key;
                Ok(Some(key))
            }
            Self::Site(site) => {
                if !catalog
                    .opening()
                    .sites
                    .iter()
                    .any(|row| row.site_id == site)
                {
                    return Err(ObserverEconomyError::SiteAbsent);
                }
                Ok(roster.and_then(|roster| {
                    roster
                        .members
                        .binary_search_by_key(&site, |row| row.site)
                        .ok()
                        .map(|index| roster.members[index].company)
                }))
            }
        }
    }
}

impl ObserverMaterialCursor {
    /// Inspect an owned site and its parent from the authenticated observer frame already on screen.
    /// # Errors
    /// Refuses unknown sites, a missing full-observer close, or a different campaign, period or source.
    pub fn site_company_decision_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        site: SiteId,
        foundation: [u8; 32],
        tick_hash: [u8; 32],
    ) -> Result<Option<CompanyDecisionReport>, ObserverEconomyError> {
        self.decision_for_frame(
            campaign,
            tick,
            DecisionSubject::Site(site),
            foundation,
            tick_hash,
        )
    }
    /// Borrow the exact governed outcome of this company's decision in the displayed frame.
    /// # Errors
    /// Refuses unavailable company policies or choices, and any mismatch in the supplied frame.
    pub fn company_decision_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        company: CompanyId,
        foundation: [u8; 32],
        tick_hash: [u8; 32],
    ) -> Result<CompanyDecisionReport, ObserverEconomyError> {
        self.decision_for_frame(
            campaign,
            tick,
            DecisionSubject::Company(company),
            foundation,
            tick_hash,
        )?
        .ok_or(ObserverEconomyError::CompanyDecisionAbsent)
    }

    fn decision_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        subject: DecisionSubject,
        foundation: [u8; 32],
        tick_hash: [u8; 32],
    ) -> Result<Option<CompanyDecisionReport>, ObserverEconomyError> {
        let (expected, close) = self.displayed_frame(campaign, tick, foundation, tick_hash)?;
        close.decision(campaign, &expected, subject)
    }
}
impl ObserverFrameClose {
    fn decision(
        &self,
        campaign: CampaignId,
        expected: &EconomicContentAdmission,
        subject: DecisionSubject,
    ) -> Result<Option<CompanyDecisionReport>, ObserverEconomyError> {
        let catalog = expected
            .foundation()
            .graph_foundation()
            .content_bundle()
            .economic_catalog()
            .ok_or(ObserverEconomyError::ScenarioMismatch)?;
        if catalog.national_companies().is_some()
            != expected.material_catalog().company_portfolios.is_some()
        {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        let Some(key) = subject.company_key(catalog)? else {
            return Ok(None);
        };
        let rows = &self
            .register
            .company_portfolios()
            .ok_or(ObserverEconomyError::InvalidProjection)?
            .companies;
        let company = key.id();
        let evidence = rows
            .binary_search_by_key(&company, |row| row.company)
            .ok()
            .map(|index| &rows[index])
            .filter(|row| row.period == self.register.completed_tick())
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        let carrier =
            company_graph::company_key(expected.foundation_graph().scenario_scope(), company);
        let draw = self
            .draws
            .0
            .get(&carrier)
            .ok_or(ObserverEconomyError::InvalidProjection)?;
        if draw.masses
            != evidence
                .weights
                .map(|weight| u64::from(weight) * MASS_NANOUNITS_PER_UNIT)
        {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        Ok(Some(CompanyDecisionReport {
            campaign,
            foundation_sha256: expected.digest(),
            tick_content_hash: *self.identity.tick_content_hash().as_bytes(),
            company_label: key.label(),
            evidence: evidence.clone(),
            encounter_ordinal: draw.encounter,
            selected_outcome: MEMBERS[draw.selected].into(),
            draw_ticket: draw.ticket,
        }))
    }
}

impl ObserverEconomyReader {
    /// Read all four investment alternatives, their evidence and the realized draw.
    /// # Errors
    /// Refuses restricted credentials, missing captures, unknown companies and inconsistent receipts.
    pub fn company_decision_receipt(
        &self,
        campaign: CampaignId,
        tick: u64,
        company: CompanyId,
    ) -> Result<CompanyDecisionReport, ObserverEconomyError> {
        self.decision_for(campaign, tick, DecisionSubject::Company(company), None)?
            .ok_or(ObserverEconomyError::CompanyDecisionAbsent)
    }

    /// Inspect the investment draw of the captured parent of a selected site at this close.
    /// A known site without captured membership has no company decision.
    /// # Errors
    /// Refuses restricted credentials, unknown sites, missing periods, a changed frame or inconsistent evidence.
    pub fn site_company_decision_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        site: SiteId,
        foundation: [u8; 32],
        tick_hash: [u8; 32],
    ) -> Result<Option<CompanyDecisionReport>, ObserverEconomyError> {
        self.decision_for(
            campaign,
            tick,
            DecisionSubject::Site(site),
            Some((foundation, tick_hash)),
        )
    }
    fn decision_for(
        &self,
        campaign: CampaignId,
        tick: u64,
        subject: DecisionSubject,
        frame: Option<([u8; 32], [u8; 32])>,
    ) -> Result<Option<CompanyDecisionReport>, ObserverEconomyError> {
        self.with_statement_source(campaign, tick, |tx, expected| {
            if tick == 0 {
                return Err(ObserverEconomyError::TickAbsent);
            }
            let mut cursor = None;
            let source = crate::observer_material::committed_receipts(
                tx,
                campaign,
                tick,
                expected,
                &mut cursor,
                None,
            )?;
            let hash = *source.identity.tick_content_hash().as_bytes();
            let (foundation, tick_hash) = frame.unwrap_or((expected.digest(), hash));
            let result = cursor
                .as_ref()
                .ok_or(ObserverEconomyError::InvalidProjection)?
                .decision_for_frame(campaign, tick, subject, foundation, tick_hash)?;
            Ok((result, Some(hash)))
        })
    }
}

impl Serialize for CompanyDecisionReport {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let evidence = &self.evidence;
        let condition = match evidence.condition {
            CompanyCondition::Loss => "loss",
            CompanyCondition::Replacement => "replacement",
            CompanyCondition::Spare => "spare",
            CompanyCondition::UnmetDemand => "unmet_demand",
            CompanyCondition::NoMatchingRow => "no_matching_row",
        };
        let processes: Vec<_> = evidence
            .processes
            .iter()
            .map(|process| {
                json!({
                    "site": michigan_economy::digest_hex(&process.site.as_bytes()),
                    "process": michigan_economy::digest_hex(&process.process.as_bytes()),
                    "produced_batches": process.produced_batches,
                    "capacity_batches": process.capacity_batches,
                    "unmet_accepted_units": process.unmet_accepted_units,
                    "used_service_batches": process.used_service_batches,
                    "replacement_units": process.replacement,
                    "expansion_units": process.expansion,
                    "unit_price_micros": process.unit_price.micro_units().to_string(),
                    "free_cash_micros": process.free_cash.micro_units().to_string(),
                    "earnings_budget_micros": process.earnings_budget.micro_units().to_string(),
                })
            })
            .collect();
        let alternatives: Vec<_> = MEMBERS
            .iter()
            .enumerate()
            .map(|(index, member)| {
                let plan: Vec<_> = evidence.plans[index]
                    .iter()
                    .map(|limit| {
                        json!({
                            "site": michigan_economy::digest_hex(&limit.site.as_bytes()),
                            "process": michigan_economy::digest_hex(&limit.process.as_bytes()),
                            "replacement_units": limit.replacement,
                            "expansion_units": limit.expansion,
                            "treasury_funding_micros": limit.funding.micro_units().to_string(),
                        })
                    })
                    .collect();
                json!({
                    "member": member,
                    "feasible": evidence.feasible[index],
                    "original_weight": evidence.original_weights[index],
                    "eligible_weight": evidence.weights[index],
                    "plan": plan,
                })
            })
            .collect();
        let history: Vec<_> = evidence
            .history
            .iter()
            .map(|income| income.micro_units().to_string())
            .collect();
        json!({
            "version": 1,
            "campaign": self.campaign.as_uuid().to_string(),
            "resolve_tick": evidence.period,
            "foundation_sha256": michigan_economy::digest_hex(&self.foundation_sha256),
            "tick_content_hash": michigan_economy::digest_hex(&self.tick_content_hash),
            "company": michigan_economy::digest_hex(&evidence.company.as_bytes()),
            "encounter_ordinal": self.encounter_ordinal,
            "draw_ticket": self.draw_ticket.to_string(),
            "selected_outcome": self.selected_outcome,
            "alternatives": alternatives,
            "evidence": {
                "condition": condition,
                "operating_income_micros": history,
                "treasury_available_micros": evidence.treasury_available.micro_units().to_string(),
                "processes": processes,
            }
        })
        .serialize(serializer)
    }
}
