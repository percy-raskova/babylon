//! Financial statements of the represented company selected on the geographic flow page.
use super::rail;
use super::state::{Action, MoneyView, Scope};
use crate::cli;
use crate::company_investment::{self, Subject};
use crate::human_numbers;
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_performance::RenderMode;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::CompanyId;
use babylon_persistence::company_statements::CompanyBookPeriod;
use babylon_persistence::money_journal::{FlowGroup, JournalError, SelectedCompanyAccounts};
use babylon_persistence::observer_reader::{ObserverEconomyError, ObserverEconomyReader};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};
use bevy::text::LineBreak;
use std::fmt::Write as _;

#[derive(Default)]
pub(super) struct Accounts {
    id: Option<CompanyId>,
    consolidated: bool,
    investment_open: bool,
    investment: Option<Result<String, JournalError>>,
    result: Option<Result<SelectedCompanyAccounts, JournalError>>,
}

impl Accounts {
    pub(super) fn is_open(&self) -> bool {
        self.id.is_some()
    }

    pub(super) fn mode(&self) -> RenderMode {
        if self.investment_open {
            RenderMode::CompanyInvestment
        } else if self.consolidated {
            RenderMode::CompanyConsolidated
        } else {
            RenderMode::CompanyParent
        }
    }

    pub(super) fn key(&self) -> (Option<CompanyId>, RenderMode, bool) {
        // Statements rebuild their rows. The investment text updates in place so a
        // completed read cannot remove a keyboard user's focused control.
        (
            self.id,
            self.mode(),
            !self.investment_open && self.result.is_some(),
        )
    }

    fn loaded(&self) -> bool {
        if self.investment_open {
            self.investment.is_some()
        } else {
            self.result.is_some()
        }
    }

    pub(super) fn show_investment(&mut self, company: CompanyId, open: bool) -> bool {
        if self.id != Some(company) || self.investment_open == open {
            return false;
        }
        self.investment_open = open;
        true
    }

    pub(super) fn set_open(&mut self, id: Option<CompanyId>, open: bool) -> bool {
        if self.is_open() == open || open && id.is_none() {
            return false;
        }
        *self = Self {
            id: if open { id } else { None },
            ..default()
        };
        true
    }

    pub(super) fn show_consolidated(&mut self, next: bool) -> bool {
        if !self.is_open() || self.investment_open || self.consolidated == next {
            return false;
        }
        self.consolidated = next;
        true
    }
}

pub(super) fn selected(view: &MoneyView) -> Option<CompanyId> {
    if !matches!(
        view.scope.as_ref()?.group,
        FlowGroup::Company | FlowGroup::Counterparty
    ) {
        return None;
    }
    let peer = view
        .selected_row()?
        .key
        .peer
        .as_deref()?
        .strip_prefix("company:")?;
    cli::identity_bytes(peer).map(CompanyId::from_bytes)
}

enum Reading {
    Accounts(Box<SelectedCompanyAccounts>),
    Investment(String),
}

struct Pending {
    scope: Scope,
    company: CompanyId,
    investment: bool,
    read: Task<Result<Reading, JournalError>>,
}

impl Pending {
    fn start(scope: &Scope, company: CompanyId, investment: bool) -> Self {
        let requested = scope.clone();
        let read = IoTaskPool::get().spawn(async move {
            let reader =
                ObserverEconomyReader::from_observer_env().map_err(JournalError::Observer)?;
            let hash = requested
                .tick_hash
                .as_deref()
                .ok_or(JournalError::SourceChanged)?;
            if investment {
                let foundation = cli::identity_bytes(&requested.foundation)
                    .ok_or(JournalError::SourceChanged)?;
                let tick_hash = cli::identity_bytes(hash).ok_or(JournalError::SourceChanged)?;
                return company_investment::read(
                    &reader,
                    &requested.context,
                    foundation,
                    tick_hash,
                    Subject::Company(company),
                )
                .map(Reading::Investment);
            }
            reader
                .company_accounts_for_frame(
                    requested.context.campaign,
                    requested.context.tick,
                    company,
                    &requested.foundation,
                    hash,
                )
                .map(|books| Reading::Accounts(Box::new(books)))
        });
        Self {
            scope: scope.clone(),
            company,
            investment,
            read,
        }
    }
}

#[derive(Resource, Default)]
pub(super) struct Worker(Option<Pending>);

pub(super) fn update(mut view: ResMut<MoneyView>, mut worker: ResMut<Worker>) {
    if let Some(job) = &mut worker.0 {
        let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(&mut job.read))
        else {
            return;
        };
        if view.scope.as_ref() == Some(&job.scope)
            && view.company.id == Some(job.company)
            && selected(&view) == Some(job.company)
        {
            match result {
                Ok(Reading::Accounts(books)) => view.company.result = Some(Ok(*books)),
                Ok(Reading::Investment(reading)) => view.company.investment = Some(Ok(reading)),
                Err(error) if job.investment => view.company.investment = Some(Err(error)),
                Err(error) => view.company.result = Some(Err(error)),
            }
        }
        worker.0 = None;
    }
    let (Some(scope), Some(company)) = (&view.scope, view.company.id) else {
        return;
    };
    if !view.company.loaded() && selected(&view) == Some(company) {
        worker.0 = Some(Pending::start(scope, company, view.company.investment_open));
    }
}

fn section(rail: &mut ChildSpawnerCommands, title: &str, values: &[(&str, Currency)]) {
    rail.spawn(rail::label(
        title,
        17.0,
        theme::PAPER,
        ObserverFontRole::Display,
    ));
    let mut text = String::new();
    for (label, amount) in values {
        if !text.is_empty() {
            text.push('\n');
        }
        write!(
            text,
            "{label}\n{}",
            human_numbers::currency(amount.micro_units())
        )
        .expect("String write");
    }
    rail.spawn(rail::label(
        text,
        15.0,
        theme::PAPER,
        ObserverFontRole::Exact,
    ));
}

fn statements(rail: &mut ChildSpawnerCommands, books: &CompanyBookPeriod) {
    let i = &books.income;
    section(
        rail,
        "Income statement",
        &[
            ("Sales", i.sales),
            ("Cost of goods sold", i.cost_of_goods_sold),
            ("Operating expenses", i.operating_expenses),
            ("Taxes", i.taxes),
            ("Other income", i.other_income),
            ("Other expenses", i.other_expenses),
            ("Net profit or loss", i.profit),
            ("Distributions", i.distributions),
            ("Capital contributions", i.contributions),
        ],
    );
    let c = &books.closing;
    section(
        rail,
        "Closing balance sheet",
        &[
            ("Spendable cash", c.cash),
            ("Restricted funds", c.reserves),
            ("Inventory", c.inventory),
            ("Freight", c.freight),
            ("Equipment", c.equipment),
            ("Receivables", c.receivables),
            ("Investments", c.investments),
            ("Total assets", c.assets),
            ("Liabilities", c.liabilities),
            ("Equity", c.equity),
            ("Retained earnings", c.retained_earnings),
        ],
    );
    let f = &books.cash_flow;
    section(
        rail,
        "Cash flow",
        &[
            ("Opening spendable cash", books.opening.cash),
            ("Operating", f.operating),
            ("Investing", f.investing),
            ("Financing", f.financing),
            ("Reserve reclassification", f.reserve_reclassification),
            ("Closing spendable cash", c.cash),
        ],
    );
}

#[derive(Component)]
pub(super) struct InvestmentText;

pub(super) fn paint_investment(
    view: Res<MoneyView>,
    mut readings: Query<&mut Text, With<InvestmentText>>,
) {
    for mut text in &mut readings {
        if !view.is_changed() && !text.is_added() {
            continue;
        }
        let reading = match &view.company.investment {
            Some(Ok(reading)) => reading.clone(),
            Some(Err(JournalError::Observer(
                ObserverEconomyError::CompanyDecisionAbsent
                | ObserverEconomyError::CompanyPortfoliosNotCaptured,
            ))) => "Company investment evidence is unavailable for the selected period.".into(),
            Some(Err(error)) => format!("Company investment decision unavailable ({error})."),
            None => "Reading the company’s investment decision…".into(),
        };
        text.set_if_neq(Text::new(reading));
    }
}

fn investment_panel(
    rail: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    id: CompanyId,
) {
    rail::control(
        rail,
        view,
        scope,
        Action::CompanyInvestment {
            company: id,
            open: false,
        },
        "Back to accounts".into(),
    );
    rail.spawn(rail::label(
        "Investment decision",
        20.0,
        theme::PAPER,
        ObserverFontRole::Display,
    ));
    let mut focus = ObserverFocusTarget::reading(Some(scope.context.clone()));
    focus.available = true;
    rail.spawn((
        rail::label("", 15.0, theme::PAPER, ObserverFontRole::Body),
        InvestmentText,
        focus,
        TextLayout::linebreak(LineBreak::WordOrCharacter),
        Node {
            min_width: px(0),
            max_width: percent(100),
            flex_shrink: 0.0,
            ..default()
        },
    ));
}

pub(super) fn panel(rail: &mut ChildSpawnerCommands, view: &MoneyView, scope: &Scope) -> bool {
    let Some(id) = view.company.id else {
        return false;
    };
    if view.company.investment_open {
        investment_panel(rail, view, scope, id);
        return true;
    }
    let name = view
        .selected_row()
        .and_then(|r| r.label.as_deref())
        .unwrap_or("Represented company");
    let consolidated = view.company.consolidated;
    let basis = if consolidated {
        "Consolidated company"
    } else {
        "Legal parent"
    };
    rail.spawn(rail::label(
        format!("{name}\n{basis} accounts"),
        20.0,
        theme::PAPER,
        ObserverFontRole::Display,
    ));
    rail.spawn(rail::label(
        format!("Period {}", scope.context.tick),
        15.0,
        theme::GRAY,
        ObserverFontRole::Body,
    ));
    rail::control(
        rail,
        view,
        scope,
        Action::CompanyAccounts(false),
        "Back to flows".into(),
    );
    rail::control(
        rail,
        view,
        scope,
        Action::CompanyInvestment {
            company: id,
            open: true,
        },
        "Investment decision".into(),
    );
    let switch = if consolidated {
        "Show legal parent"
    } else {
        "Show consolidated company"
    };
    rail::control(
        rail,
        view,
        scope,
        Action::CompanyConsolidated(!consolidated),
        switch.into(),
    );
    let result = match &view.company.result {
        Some(Ok(result)) => result,
        other => {
            let text = match other.as_ref().and_then(|r| r.as_ref().err()) {
                None => "Reading company statements…".into(),
                Some(JournalError::CoverageAbsent) => {
                    "Company statements have not been published for this period.".into()
                }
                Some(error) => format!("Company statements are unavailable ({error})."),
            };
            rail.spawn(rail::label(text, 15.0, theme::GRAY, ObserverFontRole::Body));
            return true;
        }
    };
    statements(
        rail,
        if consolidated {
            &result.consolidated
        } else {
            &result.parent
        },
    );
    if consolidated {
        let e = &result.eliminations;
        section(
            rail,
            "Consolidation adjustments",
            &[
                ("Closing member investments", e.closing_investments),
                ("Closing intercompany claims", e.closing_intercompany_claims),
                ("Internal contributions", e.contributions),
                ("Internal distributions", e.distributions),
                ("Internal sales", e.sales),
                ("Internal seller cost", e.seller_cost),
                ("Margin created", e.margin_created),
                ("Margin realized", e.margin_realized),
                ("Closing unrealized margin", e.closing_unrealized_margin),
            ],
        );
    }
    true
}

#[cfg(test)]
mod tests {
    use super::super::state::{MoneyRail, MoneyView};
    use super::super::{rail, tests};
    use babylon_material_circuit::CompanyId;
    use bevy::input_focus::{FocusCause, InputFocus};
    use bevy::prelude::*;

    #[test]
    fn investment_reading_keeps_keyboard_focus_when_the_receipt_arrives() {
        let (mut app, _, _, _) = tests::interaction_fixture();
        let company = CompanyId::from_bytes([1; 32]);
        let mut view = app.world_mut().resource_mut::<MoneyView>();
        assert!(view.company.set_open(Some(company), true));
        assert!(view.company.show_investment(company, true));
        app.world_mut().spawn((MoneyRail, Node::default()));
        app.init_resource::<InputFocus>()
            .add_systems(Update, (rail::paint, super::paint_investment).chain());
        app.update();
        let world = app.world_mut();
        let loading = world
            .query::<(Entity, &Text)>()
            .iter(world)
            .find_map(|(entity, text)| {
                (text.0 == "Reading the company’s investment decision…").then_some(entity)
            })
            .expect("the reading is visible while the query runs");
        world
            .resource_mut::<InputFocus>()
            .set(loading, FocusCause::Navigated);
        world.resource_mut::<MoneyView>().company.investment =
            Some(Ok("P4 committed decision".into()));
        app.update();
        let world = app.world();
        assert_eq!(world.resource::<InputFocus>().get(), Some(loading));
        assert_eq!(
            world
                .get::<Text>(loading)
                .expect("the focused reading survives")
                .0,
            "P4 committed decision"
        );
    }
}
