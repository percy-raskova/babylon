//! Closed-period household receipts for the account selected on the full-observer flow page.
use super::rail;
use super::state::{Action, Measure, MoneyView, Scope};
use crate::atlas::CountyAtlas;
use crate::cli;
use crate::human_numbers;
use crate::observer::{ObservationContext, Perspective};
use crate::observer_io::ObservationCache;
use crate::observer_theme as theme;
use crate::observer_ui::{self, ObserverFontRole};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_persistence::money_journal::{FlowGroup, JournalError};
use babylon_persistence::observer_reader::{
    HouseholdPeriodReport, ObserverEconomyError, ObserverEconomyReader,
};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};
use bevy::text::LineBreak;

pub(crate) type Reading = Result<HouseholdPeriodReport, JournalError>;

#[derive(Clone, PartialEq, Eq)]
pub(crate) struct HouseholdRead {
    pub context: ObservationContext,
    pub foundation: String,
    pub tick_hash: String,
    pub principal: FinalDemandPrincipalId,
}

impl HouseholdRead {
    pub(crate) fn read(&self, reader: Option<ObserverEconomyReader>) -> Reading {
        let reader = reader
            .map_or_else(ObserverEconomyReader::from_observer_env, Ok)
            .map_err(JournalError::Observer)?;
        let report = reader
            .household_period(self.context.campaign, self.context.tick, self.principal)
            .map_err(JournalError::Observer)?;
        if report.version != HouseholdPeriodReport::VERSION
            || report.period != self.context.tick
            || report.campaign != self.context.campaign.as_uuid().to_string()
            || cli::identity_bytes(&report.household) != Some(self.principal.as_bytes())
            || report.foundation_sha256 != self.foundation
            || report.tick_content_sha256 != self.tick_hash
        {
            return Err(JournalError::SourceChanged);
        }
        Ok(report)
    }
}

#[derive(Default)]
pub(super) struct Receipt {
    pub(super) open: bool,
    result: Option<Reading>,
}
impl Receipt {
    pub(super) fn key(&self) -> (bool, bool) {
        (self.open, self.result.is_some())
    }
}

pub(super) fn selected(view: &MoneyView) -> Option<FinalDemandPrincipalId> {
    let scope = view.scope.as_ref()?;
    if scope.context.perspective != Perspective::FullObserver
        || scope.context.tick == 0
        || scope.tick_hash.is_none()
        || scope.measure != Measure::Money
        || !matches!(scope.group, FlowGroup::Account | FlowGroup::Counterparty)
    {
        return None;
    }
    let key = view
        .selected_row()?
        .key
        .peer
        .as_deref()?
        .strip_prefix("household_cash:")?;
    cli::identity_bytes(key).map(FinalDemandPrincipalId::from_bytes)
}

pub(super) fn set_open(view: &mut MoneyView, open: bool) -> bool {
    if view.household.open == open || (open && selected(view).is_none()) {
        return false;
    }
    view.household = Receipt { open, result: None };
    true
}

pub(super) fn accepts(view: &MoneyView, scope: &Scope, id: FinalDemandPrincipalId) -> bool {
    view.household.open && view.scope.as_ref() == Some(scope) && selected(view) == Some(id)
}

struct Pending {
    scope: Scope,
    principal: FinalDemandPrincipalId,
    read: Task<Reading>,
}

#[derive(Resource, Default)]
pub(super) struct Worker(Option<Pending>);

pub(super) fn update(
    mut view: ResMut<MoneyView>,
    mut worker: ResMut<Worker>,
    cache: Option<Res<ObservationCache>>,
) {
    if let Some(job) = &mut worker.0 {
        let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(&mut job.read))
        else {
            return;
        };
        if accepts(&view, &job.scope, job.principal) {
            view.household.result = Some(result);
        }
        worker.0 = None;
    }
    if !view.household.open || view.household.result.is_some() || view.freight.enabled {
        return;
    }
    let (Some(scope), Some(principal)) = (&view.scope, selected(&view)) else {
        return;
    };
    let Some(tick_hash) = scope.tick_hash.clone() else {
        return;
    };
    let requested = HouseholdRead {
        context: scope.context.clone(),
        foundation: scope.foundation.clone(),
        tick_hash,
        principal,
    };
    let reader = cache.as_deref().and_then(ObservationCache::full_reader);
    worker.0 = Some(Pending {
        scope: scope.clone(),
        principal,
        read: IoTaskPool::get().spawn(async move { requested.read(reader) }),
    });
}

fn population(report: &HouseholdPeriodReport) -> String {
    let Some(p) = &report.population else {
        return "Static population cohort · age transitions were not modeled for this period."
            .into();
    };
    let source = match report.residence {
        EconomicLocation::County(_) => {
            "Opening ages allocated from 2020–2024 ACS county estimates. Births, deaths and age crossings are modeled."
        }
        EconomicLocation::Foreign(_) | EconomicLocation::Dependency(_) => {
            "Opening age mix from Designed scenario shares. Births, deaths and age crossings are modeled."
        }
    };
    let opening = &p.opening;
    let closing = &p.closing;
    let loss = &p.deaths;
    let under_18 =
        |young: u64, teen: u64| human_numbers::grouped(u128::from(young) + u128::from(teen));
    let deaths = [
        loss.under_16,
        loss.age_16_17,
        loss.age_18_64,
        loss.age_65_plus,
    ]
    .into_iter()
    .map(u128::from)
    .sum();
    format!("Residents · opening → closing\nD · under 18: {} → {}\nP · ages 18–64: {} → {}\nD′ · age 65+: {} → {}\nOccupied households: {} → {}\n{} births · {} deaths\nTurned 16: {} · 18: {} · 65: {}\n{source}",
        under_18(opening.under_16, opening.age_16_17), under_18(closing.under_16, closing.age_16_17),
        observer_ui::grouped(opening.age_18_64), observer_ui::grouped(closing.age_18_64), observer_ui::grouped(opening.age_65_plus), observer_ui::grouped(closing.age_65_plus),
        observer_ui::grouped(p.opening_households), observer_ui::grouped(p.closing_households), observer_ui::grouped(p.births), human_numbers::grouped(deaths),
        observer_ui::grouped(p.reached_16), observer_ui::grouped(p.reached_18), observer_ui::grouped(p.reached_65))
}

fn provisioning(report: &HouseholdPeriodReport) -> String {
    use std::fmt::Write as _;
    let mut text = String::new();
    for g in &report.goods {
        writeln!(
            text,
            "{} ({})\nRetailer · {}\n{}\nPantry · {} opening · {} closing\nOrder · {} requested · {} affordable · {} bought · {} expired\nNeed · {} required · {} consumed · {} unmet",
            g.good.replace('_', " "),
            g.unit,
            crate::production::retailer_name(&g.retailer_name),
            g.retailer_site_id,
            observer_ui::grouped(g.opening_stock),
            observer_ui::grouped(g.closing_stock),
            observer_ui::grouped(g.requested),
            observer_ui::grouped(g.admitted),
            observer_ui::grouped(g.purchased),
            observer_ui::grouped(g.expired),
            observer_ui::grouped(g.required),
            observer_ui::grouped(g.consumed),
            observer_ui::grouped(g.unmet)
        )
        .expect("String write");
    }
    for s in &report.services {
        writeln!(
            text,
            "{} ({})\n{} required · {} delivered · {} satisfied · {} unmet",
            s.good.replace('_', " "),
            s.unit,
            observer_ui::grouped(s.required),
            observer_ui::grouped(s.delivered),
            observer_ui::grouped(s.satisfied),
            observer_ui::grouped(s.unmet)
        )
        .expect("String write");
    }
    if text.is_empty() {
        text.push_str("No household goods or service needs were recorded.");
    }
    text.trim_end().to_owned()
}

fn support_and_time(report: &HouseholdPeriodReport) -> String {
    use std::fmt::Write as _;
    let mut text = String::new();
    for grant in &report.income_support {
        let payer: String = grant.public_payer.chars().take(8).collect();
        writeln!(
            text,
            "Public income support · {payer}\n{} requested · {} paid · {} unfunded",
            rail::amount(&grant.requested_micros),
            rail::amount(&grant.paid_micros),
            rail::amount(&grant.unfunded_micros)
        )
        .expect("String write");
    }
    if report.income_support.is_empty() {
        text.push_str("No public income support was recorded.\n");
    }
    if let Some(t) = &report.time {
        write!(text, "Work attended: {} h\nUnpaid household provisioning: {} h needed · {} h allocated · {} h unresolved",
            observer_ui::grouped(t.attended), observer_ui::grouped(t.unpaid_requested), observer_ui::grouped(t.unpaid_allocated), observer_ui::grouped(t.unpaid_unresolved)).expect("String write");
    } else {
        text.push_str("Household time was not recorded in this period.");
    }
    if !report.workforce_attrition.is_empty() {
        let (employed, reserve) =
            report
                .workforce_attrition
                .iter()
                .fold((0_u128, 0_u128), |(e, r), row| {
                    (
                        e + u128::from(row.employed_removed),
                        r + u128::from(row.reserve_removed),
                    )
                });
        write!(text, "\nWorkforce members removed to stay within the living 16+ population: {} employed · {} reserve.",
            human_numbers::grouped(employed), human_numbers::grouped(reserve)).expect("String write");
    }
    text
}

pub(super) fn panel(
    parent: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    atlas: &CountyAtlas,
) -> bool {
    if !view.household.open {
        return false;
    }
    parent.spawn(rail::label(
        "Household period receipt",
        20.0,
        theme::PAPER,
        ObserverFontRole::Display,
    ));
    rail::control(
        parent,
        view,
        scope,
        Action::HouseholdReceipt(false),
        "Back to flows".into(),
    );
    for text in sections(view.household.result.as_ref(), atlas) {
        parent.spawn((
            rail::label(text, 15.0, theme::PAPER, ObserverFontRole::Body),
            TextLayout::linebreak(LineBreak::WordOrCharacter),
            Node {
                width: percent(100),
                min_width: px(0),
                flex_shrink: 0.0,
                ..default()
            },
        ));
    }
    true
}

pub(crate) fn sections(result: Option<&Reading>, atlas: &CountyAtlas) -> Vec<String> {
    let report = match result {
        Some(Ok(report)) => report,
        Some(Err(JournalError::Observer(ObserverEconomyError::HouseholdAbsent))) => {
            return vec!["This account has no captured household.".into()];
        }
        Some(Err(error)) => {
            return vec![format!(
                "Household receipt unavailable ({error}). Reopen to retry."
            )]
        }
        None => return vec!["Reading the household receipt…".into()],
    };
    let location = rail::location(Some(&report.residence.to_string()), atlas);
    let short: String = report.household.chars().take(8).collect();
    vec![
        format!(
            "{location} · Household {short}\nPeriod {} · four weeks",
            report.period
        ),
        population(report),
        provisioning(report),
        format!(
            "Wages accrued {} · wages paid {}\nPurchases settled: goods {} · services {}",
            rail::amount(&report.cash.wages_accrued),
            rail::amount(&report.cash.wages_paid),
            rail::amount(&report.cash.goods_purchases_settled),
            rail::amount(&report.cash.service_purchases_settled)
        ),
        support_and_time(report),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn household_receipt_explains_a_zero_delivery_with_pantry_stock() {
        let report: HouseholdPeriodReport = serde_json::from_value(serde_json::json!({
            "version": HouseholdPeriodReport::VERSION, "campaign": "example", "period": 4, "household": "example",
            "residence": "county:26163", "foundation_sha256": "", "world_sha256": "",
            "tick_content_sha256": "", "receipts_sha256": "", "population": null,
            "cash": {"wages_accrued_micros":"0","wages_paid_micros":"0",
                    "goods_purchases_settled_micros":"0","service_purchases_settled_micros":"0"},
            "income_support": [], "services": [], "time": null, "workforce_attrition": [],
            "goods": [{"good": "food", "unit":"parcels", "retailer_site_id":"17".repeat(32),
                        "retailer_name":"Wayne County: distribution_transport (5)", "opening_stock":4,
                        "requested":12, "admitted":7, "expired":7, "closing_stock":0,
                        "required":10, "purchased":0, "consumed":4, "unmet":6}]
        }))
        .expect("one food order and its consumption receipt");
        let text = provisioning(&report);
        for detail in [
            "Wayne County: Distribution/transport (5)",
            &"17".repeat(32),
            "4 opening",
            "12 requested",
            "7 affordable",
            "0 bought",
            "7 expired",
            "4 consumed",
            "6 unmet",
            "0 closing",
        ] {
            assert!(text.contains(detail), "missing {detail} in {text}");
        }
    }
}
