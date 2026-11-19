//! Explain a committed company choice and its next-period authority.
use crate::human_numbers;
use crate::observer::{ObservationContext, ObserverSession};
use crate::observer_io::ObservationCache;
use crate::observer_ui::ObserverFrame;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    CompanyCondition, CompanyId, CompanyPortfolioEvidence, ProcessId, SiteId,
};
use babylon_persistence::money_journal::JournalError;
use babylon_persistence::observer_reader::{CompanyDecisionReport, ObserverEconomyError};
use std::fmt::Write as _;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct ProcessLabel {
    pub(crate) id: ProcessId,
    pub(crate) output_good: String,
    pub(crate) unit: String,
}

#[derive(Clone, Copy)]
pub(crate) enum Subject<'a> {
    Company(CompanyId),
    Site(SiteId, &'a [ProcessLabel]),
}

const ALTERNATIVES: [(&str, &str); 4] = [
    ("DEFER", "Defer investment"),
    ("REPLACEMENT_ONLY", "Replacement only"),
    ("MODEST_EXPANSION", "Modest expansion"),
    ("LARGER_EXPANSION", "Larger expansion"),
];

pub(crate) fn read(
    cache: Option<&ObservationCache>,
    session: &ObserverSession,
    frame: &ObserverFrame,
    context: &ObservationContext,
    foundation: [u8; 32],
    tick_hash: [u8; 32],
    subject: Subject<'_>,
) -> Result<String, JournalError> {
    let cursor = cache
        .ok_or(JournalError::SourceChanged)?
        .full_cursor_for_frame(session, frame, context, foundation, tick_hash)
        .map_err(journal_error)?;
    let response = match subject {
        Subject::Company(company) => cursor
            .company_decision_for_frame(
                context.campaign,
                context.tick,
                company,
                foundation,
                tick_hash,
            )
            .map(Some),
        Subject::Site(site, _) => cursor.site_company_decision_for_frame(
            context.campaign,
            context.tick,
            site,
            foundation,
            tick_hash,
        ),
    };
    let Some(report) = response.map_err(journal_error)? else {
        return Ok("No parent company was recorded for this site.".into());
    };
    committed_reading(&report, context, foundation, tick_hash, subject)
}

fn journal_error(error: ObserverEconomyError) -> JournalError {
    match error {
        ObserverEconomyError::SourceChanged => JournalError::SourceChanged,
        other => JournalError::Observer(other),
    }
}

fn committed_reading(
    report: &CompanyDecisionReport,
    context: &ObservationContext,
    foundation: [u8; 32],
    tick_hash: [u8; 32],
    subject: Subject<'_>,
) -> Result<String, JournalError> {
    if report.campaign != context.campaign
        || report.evidence.period != context.tick
        || report.foundation_sha256 != foundation
        || report.tick_content_hash != tick_hash
        || matches!(subject, Subject::Company(id) if report.evidence.company != id)
    {
        return Err(JournalError::SourceChanged);
    }
    describe(
        &report.company_label,
        &report.evidence,
        &report.selected_outcome,
        subject,
    )
}

fn describe(
    company: &str,
    evidence: &CompanyPortfolioEvidence,
    selected: &str,
    subject: Subject<'_>,
) -> Result<String, JournalError> {
    let index = ALTERNATIVES
        .iter()
        .position(|(key, _)| *key == selected)
        .ok_or(JournalError::Projection)?;
    let period = evidence.period;
    let next = period.checked_add(1).ok_or(JournalError::Projection)?;
    let condition = match evidence.condition {
        CompanyCondition::Loss => "Operating losses",
        CompanyCondition::Replacement => "Profitable with equipment to replace",
        CompanyCondition::Spare => "Profitable with spare capacity",
        CompanyCondition::UnmetDemand => "High utilization with unmet demand",
        CompanyCondition::NoMatchingRow => "No investment condition matched",
    };
    let mut text = format!(
        "{company}\nP{period} decision · {}\nCompany condition · {condition}\n",
        ALTERNATIVES[index].1
    );
    if let Subject::Site(site, labels) = subject {
        site_processes(&mut text, evidence, site, labels);
    }
    limits(&mut text, evidence, index, next, subject)?;
    text.push_str("\nCompany operating income");
    for (i, income) in evidence.history.iter().enumerate() {
        // The captured history is consecutive, oldest first and ending at this close.
        let before =
            u64::try_from(evidence.history.len() - 1 - i).map_err(|_| JournalError::Projection)?;
        let p = period.checked_sub(before).ok_or(JournalError::Projection)?;
        write!(
            text,
            "\nP{p}  {}",
            human_numbers::currency(income.micro_units())
        )
        .expect("String write");
    }
    write!(
        text,
        "\nAvailable treasury  {}\n\nChance of each decision",
        human_numbers::currency(evidence.treasury_available.micro_units())
    )
    .expect("String write");
    let total: u32 = evidence.weights.iter().copied().map(u32::from).sum();
    if total == 0 {
        return Err(JournalError::Projection);
    }
    for (i, (_, label)) in ALTERNATIVES.iter().enumerate() {
        let note = if !evidence.feasible[i] {
            " · infeasible"
        } else if evidence.original_weights[i] == 0 {
            " · no policy weight"
        } else if i == index {
            " · chosen"
        } else {
            ""
        };
        write!(
            text,
            "\n{label}  {}{note}",
            percent(evidence.weights[i], total)
        )
        .expect("String write");
    }
    Ok(text)
}

fn limits(
    text: &mut String,
    evidence: &CompanyPortfolioEvidence,
    index: usize,
    next: u64,
    subject: Subject<'_>,
) -> Result<(), JournalError> {
    let mut replacement = 0_u128;
    let mut expansion = 0_u128;
    let mut funding = Currency::from_micro_units(0);
    for row in &evidence.plans[index] {
        if matches!(subject, Subject::Site(site, _) if site != row.site) {
            continue;
        }
        replacement += u128::from(row.replacement);
        expansion += u128::from(row.expansion);
        funding = funding
            .checked_add(row.funding)
            .map_err(|_| JournalError::Projection)?;
    }
    let scope = match subject {
        Subject::Site(_, _) => "this site",
        Subject::Company(_) => "all company sites",
    };
    write!(text, "\nP{next} limits · {scope}\nUp to {} replacement units\nUp to {} expansion units\nTreasury funding limit  {}\nLater accounts show what was paid.\n",
        human_numbers::grouped(replacement), human_numbers::grouped(expansion), human_numbers::currency(funding.micro_units())).expect("String write");
    Ok(())
}

fn site_processes(
    text: &mut String,
    evidence: &CompanyPortfolioEvidence,
    site: SiteId,
    labels: &[ProcessLabel],
) {
    let mut rows = evidence
        .processes
        .iter()
        .filter(|row| row.site == site)
        .peekable();
    if rows.peek().is_none() {
        text.push_str("No process evidence was recorded for this site.\n");
        return;
    }
    for (i, row) in rows.by_ref().take(3).enumerate() {
        let label = labels.iter().find(|label| label.id == row.process);
        let name = label.map_or_else(
            || format!("Process {}", i + 1),
            |label| label.output_good.clone(),
        );
        let unit = label.map_or("units", |label| label.unit.as_str());
        writeln!(
            text,
            "{name} · {} of {} batches\nAccepted demand unfilled · {} ({unit})",
            human_numbers::grouped(u128::from(row.produced_batches)),
            human_numbers::grouped(u128::from(row.capacity_batches)),
            human_numbers::grouped(u128::from(row.unmet_accepted_units))
        )
        .expect("String write");
    }
    let others = rows.count();
    if others > 0 {
        writeln!(text, "{others} more processes at this site").expect("String write");
    }
}

// The receipt authenticates a common nanounit multiplier for all four weights.
// Display relative branch mass to the nearest tenth of a percent.
fn percent(weight: u16, total: u32) -> String {
    let weight = u32::from(weight);
    let tenths = (weight * 1000 + total / 2) / total;
    match tenths {
        0 if weight > 0 => "<0.1%".into(),
        1000 if weight < total => ">99.9%".into(),
        value if value.is_multiple_of(10) => format!("{}%", value / 10),
        value => format!("{}.{}%", value / 10, value % 10),
    }
}

#[cfg(test)]
mod tests {
    use super::{ProcessLabel, Subject};
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{
        CompanyCondition, CompanyId, CompanyPortfolioEvidence, CompanyProcessEvidence,
        CompanyProcessPlan, ProcessId, SiteId,
    };

    #[test]
    fn investment_decision_renormalizes_after_feasibility_and_limits_each_site() {
        let kodiak = SiteId::from_bytes([1; 32]);
        let other = SiteId::from_bytes([2; 32]);
        let company = CompanyId::from_bytes([3; 32]);
        let plan = |site, expansion, dollars| CompanyProcessPlan {
            site,
            process: ProcessId::from_bytes([4; 32]),
            replacement: 0,
            expansion,
            funding: Currency::from_micro_units(dollars * 1_000_000_i128),
        };
        let process = ProcessId::from_bytes([4; 32]);
        let zero = Currency::from_micro_units(0);
        let observed = CompanyProcessEvidence {
            site: kodiak,
            process,
            produced_batches: 400,
            capacity_batches: 400,
            unmet_accepted_units: 20_812,
            used_service_batches: 0,
            replacement: 0,
            expansion: 22,
            unit_price: Currency::from_micro_units(16_000_000_000),
            free_cash: zero,
            earnings_budget: zero,
        };
        let unused_capacity = CompanyProcessEvidence {
            site: other,
            produced_batches: 100,
            unmet_accepted_units: 0,
            expansion: 10,
            ..observed.clone()
        };
        let evidence = CompanyPortfolioEvidence {
            company,
            period: 4,
            condition: CompanyCondition::Spare,
            history: vec![
                Currency::from_micro_units(-1_000_000),
                Currency::from_micro_units(2_000_000),
                Currency::from_micro_units(3_000_000),
            ],
            treasury_available: Currency::from_micro_units(4_000_000_000_000),
            processes: vec![observed, unused_capacity],
            feasible: [true, false, true, true],
            original_weights: [60, 25, 15, 0],
            weights: [60, 0, 15, 0],
            plans: [
                vec![],
                vec![],
                vec![plan(kodiak, 22, 352_000), plan(other, 10, 160_000)],
                vec![],
            ],
        };
        let reading = |subject| {
            super::describe("National 1", &evidence, "MODEST_EXPANSION", subject)
                .expect("authenticated choice")
        };
        let labels = [ProcessLabel {
            id: process,
            output_good: "Supplies".into(),
            unit: "supplies bundle".into(),
        }];
        let site = reading(Subject::Site(kodiak, &labels));
        for line in [
            "P4 decision · Modest expansion",
            "P2  -$1.00",
            "P4  $3.00",
            "Defer investment  80%",
            "Replacement only  0% · infeasible",
            "Modest expansion  20% · chosen",
            "Larger expansion  0% · no policy weight",
            "Supplies · 400 of 400 batches",
            "Accepted demand unfilled · 20,812 (supplies bundle)",
            "P5 limits · this site",
            "Up to 22 expansion units",
            "Treasury funding limit  $352,000.00",
        ] {
            assert!(site.lines().any(|s| s == line), "{line}");
        }
        let shop = SiteId::from_bytes([5; 32]);
        let no_process = reading(Subject::Site(shop, &[]));
        assert!(no_process.contains("No process evidence was recorded for this site."));
        assert!(!no_process.contains("20,812"));
        let all = reading(Subject::Company(company));
        assert!(all.contains("P5 limits · all company sites"));
        assert!(all.contains("Up to 32 expansion units"));
        assert!(all.contains("Treasury funding limit  $512,000.00"));
    }
}
