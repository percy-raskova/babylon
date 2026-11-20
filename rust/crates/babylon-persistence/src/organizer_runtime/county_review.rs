//! The county review as the organizer's snapshot and previews show it.
//!
//! Everything here reads the committed register: the county's section, its account in the engine's
//! books and the organizer's journal. The player's figures are earned by contact, so the keys the
//! organizer has made contact in come from the journal's receipts and from nowhere else.

use babylon_material_circuit::{
    AccountId, CircuitAccounting, FinalDemandPrincipalId, PublicAccountId, PublicTransferTreatment,
    SiteId,
};
use babylon_practice_contract::{
    ContactPreview, CountyReviewConfig, CountyReviewGroup, CountyReviewProjection, GroupKind,
    LedgerInput, LedgerLine, LedgerLineKind, OrganizerChoice, OrganizerCommand, OrganizerOutcome,
    OrganizerPeriodJournal, PositionKey, SessionRecord,
};
use babylon_tick::material_world::{CountyReviewRegister, MaterialWorldRegister};

use crate::runtime_session::RuntimeSessionErrorCode;

/// The label of a grant to a site that none of the county's crews works at.
const UNNAMED_WORKPLACE: &str = "County public workplace";
/// The label of the City PD's visit line.
const CITY_PD_VISITS: &str = "City PD visits";

/// Every position the organizer has reached a household in, once each, in key order.
pub(crate) fn contacted(journal: &OrganizerPeriodJournal) -> Vec<PositionKey> {
    let mut keys: Vec<PositionKey> = journal
        .periods
        .iter()
        .flat_map(|entries| &entries.receipts)
        .filter(|receipt| receipt.outcome == OrganizerOutcome::ReviewContactMade)
        .filter_map(|receipt| match receipt.choice {
            OrganizerChoice::ReviewContact(key) => Some(key),
            _ => None,
        })
        .collect();
    keys.sort_unstable();
    keys.dedup();
    keys
}

/// The workplace a site is to the player: the name of a configured crew that works there.
fn workplace_label(config: &CountyReviewConfig, site: SiteId) -> Option<&str> {
    config
        .crews
        .iter()
        .find(|crew| crew.site_id == site.as_bytes())
        .map(|crew| crew.workplace_label.as_str())
}

/// The county's account in the engine's books: its cash, its cap and its lines in pay order, with
/// the City PD's payroll as the City PD's configuration states it.
///
/// # Errors
///
/// `StorageRefused` for a register that is not a monetary one, a county account the books do not
/// hold, a line that cannot be named and a payroll site that no crew works at.
pub(crate) fn ledger_input(
    register: &MaterialWorldRegister,
    county: &CountyReviewRegister,
) -> Result<LedgerInput, RuntimeSessionErrorCode> {
    let refused = RuntimeSessionErrorCode::StorageRefused;
    let config = county.config();
    let CircuitAccounting::Monetary(economy) = &register.state().accounting else {
        return Err(refused);
    };
    let account = PublicAccountId::from_bytes(config.public_account_id);
    let cash = economy
        .book
        .cash(AccountId::Public(account))
        .map_err(|_| refused)?;
    let budget = economy
        .financial
        .public_budgets
        .iter()
        .find(|budget| budget.public_account == account)
        .ok_or(refused)?;
    let mut lines = Vec::new();
    for row in &economy.financial.public_allocations {
        if row.public_account != account {
            continue;
        }
        let amount_micros = row.amount_per_period.micro_units();
        let line = match (row.treatment, row.recipient) {
            (PublicTransferTreatment::HouseholdIncomeSupport, AccountId::Household(principal)) => {
                let group = group_of(config, principal).ok_or(refused)?;
                LedgerLine {
                    kind: match group.kind {
                        GroupKind::Ordinary => LedgerLineKind::HouseholdSupport,
                        GroupKind::CollectiveResidence => LedgerLineKind::CollectiveResidence,
                    },
                    label: group.label.clone(),
                    amount_micros,
                    first_class: false,
                }
            }
            (PublicTransferTreatment::ProviderOperatingGrant, recipient) => LedgerLine {
                kind: LedgerLineKind::PublicWorkplace,
                label: match recipient {
                    AccountId::Site(site) => workplace_label(config, site),
                    _ => None,
                }
                .unwrap_or(UNNAMED_WORKPLACE)
                .to_owned(),
                amount_micros,
                first_class: true,
            },
            (PublicTransferTreatment::AgencyAppropriation, _) => LedgerLine {
                kind: LedgerLineKind::CityPdVisits,
                label: CITY_PD_VISITS.to_owned(),
                amount_micros,
                first_class: true,
            },
            _ => return Err(refused),
        };
        lines.push(line);
    }
    let city_pd_payroll = register
        .city_pd()
        .map(|pd| {
            let site = SiteId::from_bytes(pd.config.payroll_site_account_id);
            workplace_label(config, site)
                .map(|label| {
                    (
                        label.to_owned(),
                        pd.config.payroll_positions,
                        pd.config.payroll_micros,
                    )
                })
                .ok_or(refused)
        })
        .transpose()?;
    Ok(LedgerInput {
        cash_micros: cash.micro_units(),
        spending_limit_micros: budget.period_cap.micro_units(),
        lines,
        city_pd_payroll,
    })
}

fn group_of(
    config: &CountyReviewConfig,
    principal: FinalDemandPrincipalId,
) -> Option<&CountyReviewGroup> {
    config
        .groups
        .iter()
        .find(|group| group.group_id == principal.as_bytes())
}

/// The county as the player sees it at the register's close, or nothing for a campaign with no
/// county review.
///
/// # Errors
///
/// `StorageRefused` for a register the section cannot be projected from.
pub(crate) fn projection(
    register: &MaterialWorldRegister,
    journal: &OrganizerPeriodJournal,
) -> Result<Option<CountyReviewProjection>, RuntimeSessionErrorCode> {
    let Some(county) = register.county_review() else {
        return Ok(None);
    };
    let ledger = ledger_input(register, county)?;
    babylon_practice_contract::project(
        county.config(),
        county.state(),
        &ledger,
        &contacted(journal),
    )
    .map(Some)
    .map_err(|_| RuntimeSessionErrorCode::StorageRefused)
}

/// What a review contact in the named position would do to the county's next session. Only a
/// `ReviewContact` on a register with a county section has one; before any close has been seen
/// there is nothing to preview.
///
/// # Errors
///
/// `OrganizerRefused` when the county's own preview refuses the position or the stored state.
pub(crate) fn review_preview(
    register: &MaterialWorldRegister,
    command: &OrganizerCommand,
) -> Result<Option<ContactPreview>, RuntimeSessionErrorCode> {
    let OrganizerChoice::ReviewContact(key) = command.choice else {
        return Ok(None);
    };
    let Some(county) = register.county_review() else {
        return Ok(None);
    };
    babylon_practice_contract::preview_contact(county.config(), county.state(), key)
        .map_err(|_| RuntimeSessionErrorCode::OrganizerRefused)
}

/// The largest text the archive holds for one signal, in bytes.
const ARCHIVE_TEXT_LIMIT: usize = 4_096;

/// Millionths of a dollar as dollars, with at least two decimals and no trailing zeros past them.
fn dollars(micros: i128) -> String {
    let sign = if micros < 0 { "-" } else { "" };
    let magnitude = micros.unsigned_abs();
    let whole = magnitude / 1_000_000;
    let fraction = format!("{:06}", magnitude % 1_000_000);
    let trimmed = fraction.trim_end_matches('0');
    let cents = if trimmed.len() < 2 {
        &fraction[..2]
    } else {
        trimmed
    };
    format!("{sign}${whole}.{cents}")
}

/// The public record of one session, as the archive keeps it: the money for relief, the units
/// payable and kept back, how many positions were paid in full, in part and not at all, and the
/// ranks and units of the first positions on the list, as many as fit the archive's text limit.
/// Nothing earned by contact is in it.
pub(crate) fn session_signal_text(record: &SessionRecord) -> String {
    let (mut full, mut partly, mut none) = (0_u64, 0_u64, 0_u64);
    for row in &record.rows {
        match (row.units_paid, row.units_unpaid) {
            (0, 0) => {}
            (_, 0) => full += 1,
            (0, _) => none += 1,
            _ => partly += 1,
        }
    }
    let mut text = format!(
        "The county had {} for relief after {} of lines paid first, against a roll of {}. It could \
         pay {} of {} household units and kept back {} to an exact tie. Positions paid in full: \
         {full}. Paid in part: {partly}. Not paid: {none}. Highest on the list:",
        dollars(record.relief_micros),
        dollars(record.first_class_micros),
        dollars(record.roll_total_micros),
        record.household_units_payable,
        record.household_units_listed,
        record.kept_back_units,
    );
    let mut ranked: Vec<_> = record.rows.iter().collect();
    ranked.sort_by_key(|row| (row.rank, row.key));
    let mut shown = 0_usize;
    for row in &ranked {
        let entry = format!(
            " rank {}: {} listed, {} paid, {} unpaid;",
            row.rank, row.units_listed, row.units_paid, row.units_unpaid
        );
        let more = ranked.len() - shown - 1;
        // Leave room for the closing words, whichever way the list ends.
        let closing = format!(" and {more} more positions.");
        if text.len() + entry.len() + closing.len() > ARCHIVE_TEXT_LIMIT {
            break;
        }
        text.push_str(&entry);
        shown += 1;
    }
    if shown == ranked.len() {
        if text.ends_with(';') {
            text.pop();
            text.push('.');
        }
    } else {
        text = format!("{text} and {} more positions.", ranked.len() - shown);
    }
    text
}
