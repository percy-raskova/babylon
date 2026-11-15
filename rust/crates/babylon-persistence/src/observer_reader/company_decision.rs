//! One company's material evidence and actual BSL draw from one committed observer snapshot.
use super::{ObserverEconomyError, ObserverEconomyReader};
use crate::identity::CampaignId;
use crate::michigan_economy::digest_hex;
use babylon_bsl::probability::MASS_NANOUNITS_PER_UNIT;
use babylon_material_circuit::{CompanyCondition, CompanyId, CompanyPortfolioEvidence};
use babylon_tick::company_graph::company_key;
use serde::{Serialize, Serializer};
use serde_json::json;

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
    pub evidence: CompanyPortfolioEvidence,
    pub encounter_ordinal: u32,
    pub selected_outcome: String,
    pub draw_ticket: u64,
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
        self.with_statement_source(campaign, tick, |tx, expected| {
            if tick == 0 {
                return Err(ObserverEconomyError::TickAbsent);
            }
            if expected.material_catalog().company_portfolios.is_none() {
                return Err(ObserverEconomyError::CompanyPortfoliosNotCaptured);
            }
            let mut cursor = None;
            let source = crate::observer_material::committed_receipts(
                tx, campaign, tick, expected, &mut cursor, None,
            )?;
            let evidence = cursor
                .as_ref()
                .and_then(super::ObserverMaterialCursor::current_register)
                .and_then(babylon_tick::material_world::MaterialWorldRegister::company_portfolios)
                .ok_or(ObserverEconomyError::InvalidProjection)?
                .companies
                .iter()
                .find(|row| row.company == company)
                .ok_or(ObserverEconomyError::CompanyDecisionAbsent)?;
            let carrier = company_key(expected.foundation_graph().scenario_scope(), company)
                .canonical_bytes()
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            let sql_tick = i64::try_from(tick).map_err(|_| ObserverEconomyError::TickAbsent)?;
            // The complete envelope just authenticated these choice rows in this transaction.
            let row = tx.query_opt(
                "SELECT r.encounter_ordinal, r.selected_outcome, r.draw_ticket::text,
                        array_agg(b.outcome_member ORDER BY b.position),
                        array_agg(b.mass_nanounits::text ORDER BY b.position)
                   FROM public.v_observer_tick_choice_receipt_v1 AS r
                   JOIN public.v_observer_tick_choice_receipt_branch_v1 AS b
                     USING (campaign_id, resolve_tick, encounter_ordinal)
                  WHERE r.campaign_id=$1 AND r.resolve_tick=$2 AND r.stable_carrier=$3
                    AND r.rule_id='company/portfolio-investment' AND r.sample='company/investment-portfolio'
                    AND r.slot=0 AND r.outcome_enum='CompanyPortfolio'
                  GROUP BY r.encounter_ordinal, r.selected_outcome, r.draw_ticket",
                &[campaign.as_uuid(), &sql_tick, &carrier],
            )
            .map_err(|_| ObserverEconomyError::Database)?
            .ok_or(ObserverEconomyError::InvalidProjection)?;

            let invalid = |_| ObserverEconomyError::InvalidProjection;
            let members: Vec<String> = row.try_get(3).map_err(invalid)?;
            let masses: Vec<String> = row.try_get(4).map_err(invalid)?;
            let selected: String = row.try_get(1).map_err(invalid)?;
            let expected_masses = evidence.weights.map(|weight| {
                (u64::from(weight) * MASS_NANOUNITS_PER_UNIT).to_string()
            });
            let winner_eligible = MEMBERS.iter().zip(evidence.weights)
                .any(|(member, weight)| *member == selected && weight > 0);
            if members != MEMBERS || masses != expected_masses || !winner_eligible {
                return Err(ObserverEconomyError::InvalidProjection);
            }
            let ordinal: i64 = row.try_get(0).map_err(invalid)?;
            let ticket: &str = row.try_get(2).map_err(invalid)?;
            let hash = *source.identity.tick_content_hash().as_bytes();
            let report = CompanyDecisionReport {
                campaign,
                foundation_sha256: expected.digest(),
                tick_content_hash: hash,
                evidence: evidence.clone(),
                encounter_ordinal: u32::try_from(ordinal)
                    .map_err(|_| ObserverEconomyError::InvalidProjection)?,
                selected_outcome: selected,
                draw_ticket: ticket.parse().map_err(|_| ObserverEconomyError::InvalidProjection)?,
            };
            Ok((report, Some(hash)))
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
                    "site": digest_hex(&process.site.as_bytes()),
                    "process": digest_hex(&process.process.as_bytes()),
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
                            "site": digest_hex(&limit.site.as_bytes()),
                            "process": digest_hex(&limit.process.as_bytes()),
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
            "foundation_sha256": digest_hex(&self.foundation_sha256),
            "tick_content_hash": digest_hex(&self.tick_content_hash),
            "company": digest_hex(&evidence.company.as_bytes()),
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
