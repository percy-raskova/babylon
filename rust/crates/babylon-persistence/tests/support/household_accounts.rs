//! Household accounts read period by period: counts, money, income and needs, for the accounts a
//! test names. Reads the engine's own state and receipts; nothing here is a model of them.
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_material_circuit::{
    AccountId, CircuitAccounting, CommodityKind, FinalDemandPrincipalId, GoodId, MonetaryCircuit,
    TaxBasis, UnitId,
};
use babylon_persistence::economic_catalog::CommodityLabel;
use babylon_persistence::runtime_session::Band;
use babylon_tick::material_replay::{MaterialReplaySession, PreparedMaterialTick};
use babylon_tick::material_world::{self, MaterialTickReceipts};

pub type Session = MaterialReplaySession<HypergraphStore>;

/// One account to read: its label, its principal and its households by band, lowest band first.
#[derive(Clone, Debug)]
pub struct AccountSpec {
    pub label: String,
    pub principal: FinalDemandPrincipalId,
    pub bands: Vec<(Band, u64)>,
}

/// The state of one account after a commit, or at the opening.
#[derive(Clone, Debug)]
pub struct AccountReading {
    pub households: u64,
    pub persons: u64,
    pub labor_force: u64,
    pub cash_micros: i128,
    pub pantry_cost_micros: i128,
    /// Freight and claims carried, purchase escrows and wages owed to the account.
    pub other_assets_micros: i128,
    /// The capital row: opening capital, contributed capital and retained earnings.
    pub net_assets_micros: i128,
}

/// One need in one close.
#[derive(Clone, Debug)]
pub struct NeedReading {
    pub key: String,
    pub required: u64,
    pub unmet: u64,
    pub unpaid: u64,
    pub unsupplied: u64,
    pub cost_micros: i128,
}

/// One close, read from the candidate before it commits.
#[derive(Clone, Debug)]
pub struct PeriodReading {
    pub wages_micros: i128,
    pub support_micros: i128,
    pub aid_micros: i128,
    pub company_payouts_micros: i128,
    pub site_distributions_micros: i128,
    pub ownership_income_micros: i128,
    pub wage_tax_assessed_micros: i128,
    pub wage_tax_collected_micros: i128,
    pub needs_cost_micros: i128,
    pub needs: Vec<NeedReading>,
}

/// The sums of the specs whose households are all in the top 1% or the next 9%.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TopTenth {
    pub households: u64,
    pub net_assets_micros: i128,
    pub household_net_assets_micros: i128,
    pub ownership_income_micros: i128,
    pub needs_cost_micros: i128,
}

fn economy(session: &Session) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
        panic!("the national campaign accounts in money")
    };
    economy
}

/// Whether a spec is in the top tenth: it has households in bands, all of them top bands.
fn in_top_tenth(spec: &AccountSpec) -> bool {
    !spec.bands.is_empty()
        && spec
            .bands
            .iter()
            .all(|(band, _)| matches!(band, Band::Top1 | Band::Next9))
}

/// People in the labor force of a group: (at work + seeking) for each household, over its rows.
fn labor_force_of(session: &Session, spec: &AccountSpec) -> u64 {
    let register = session
        .material()
        .county_review()
        .unwrap_or_else(|| panic!("{}: the opening has a county section", spec.label));
    let config = register.config();
    let group = config
        .groups
        .iter()
        .position(|group| group.group_id == spec.principal.as_bytes())
        .unwrap_or_else(|| panic!("{}: a county group holds the principal", spec.label));
    let group = u32::try_from(group).expect("few groups");
    register
        .state()
        .roster
        .rows
        .iter()
        .filter(|row| row.key.group == group)
        .map(|row| (u64::from(row.key.at_work) + u64::from(row.key.seeking)) * row.households)
        .sum()
}

/// Reads every spec's account from the session's current state, in spec order.
pub fn read_accounts(session: &Session, specs: &[AccountSpec]) -> Vec<AccountReading> {
    let economy = economy(session);
    let recurring = economy
        .recurring
        .as_ref()
        .expect("the national campaign has a recurring economy");
    let costs = economy.costs.snapshot();
    let book = economy.book.snapshot();
    specs
        .iter()
        .map(|spec| {
            let label = &spec.label;
            let account = AccountId::Household(spec.principal);
            let cohort = recurring
                .households
                .iter()
                .find(|cohort| cohort.principal_id == spec.principal)
                .unwrap_or_else(|| panic!("{label}: a household cohort"));
            let cash = economy
                .book
                .cash(account)
                .unwrap_or_else(|_| panic!("{label}: a cash row"))
                .micro_units();
            let pantry: i128 = costs
                .stocks
                .iter()
                .filter(|row| row.owner == account)
                .map(|row| row.amount.micro_units())
                .sum();
            let carried: i128 = costs
                .freight
                .iter()
                .filter(|row| row.owner == account)
                .map(|row| row.amount.micro_units())
                .chain(
                    costs
                        .equity
                        .iter()
                        .filter(|row| row.owner == account)
                        .map(|row| row.amount.micro_units()),
                )
                .sum();
            let escrowed: i128 = book
                .purchases
                .iter()
                .filter(|row| row.buyer == account)
                .map(|row| row.reserved_amount().expect("a valid escrow").micro_units())
                .sum();
            let owed: i128 = book
                .shifts
                .iter()
                .filter(|row| row.payee == account)
                .map(|row| {
                    row.outstanding_wages()
                        .expect("a valid shift")
                        .micro_units()
                })
                .sum();
            let capital = costs
                .accounts
                .iter()
                .find(|row| row.account == account)
                .unwrap_or_else(|| panic!("{label}: a capital row"));
            AccountReading {
                households: cohort.households,
                persons: cohort.persons,
                labor_force: labor_force_of(session, spec),
                cash_micros: cash,
                pantry_cost_micros: pantry,
                other_assets_micros: carried + escrowed + owed,
                net_assets_micros: capital.opening_capital.micro_units()
                    + capital.contributed_capital.micro_units()
                    + capital.retained_earnings.micro_units(),
            }
        })
        .collect()
}

/// Whether the commodity is a service the period performs, from the catalog's definitions.
fn is_service(session: &Session, good: GoodId, unit: UnitId) -> bool {
    session
        .catalog()
        .commodities
        .iter()
        .find(|row| row.good_id == good && row.unit_id == unit)
        .is_some_and(|row| matches!(row.kind, CommodityKind::PeriodService { .. }))
}

/// The period's price of a good for an account: its purchase policy's retailer's offer.
fn price_of(session: &Session, spec: &AccountSpec, good: GoodId, unit: UnitId) -> i128 {
    let recurring = economy(session)
        .recurring
        .as_ref()
        .expect("a recurring economy");
    let policy = recurring
        .household_purchases
        .iter()
        .find(|row| {
            row.principal_id == spec.principal && row.good_id == good && row.unit_id == unit
        })
        .unwrap_or_else(|| panic!("{}: a purchase policy for each need", spec.label));
    recurring
        .offers
        .iter()
        .find(|row| {
            row.site_id == policy.retailer_site_id && row.good_id == good && row.unit_id == unit
        })
        .unwrap_or_else(|| panic!("{}: an offer at the policy's retailer", spec.label))
        .unit_price
        .micro_units()
}

/// The key a commodity is labelled with.
fn key_of(labels: &[CommodityLabel], good: GoodId, unit: UnitId, label: &str) -> String {
    labels
        .iter()
        .find(|row| row.good_id == good && row.unit_id == unit)
        .unwrap_or_else(|| panic!("{label}: a commodity label for each need"))
        .key
        .clone()
}

/// The need rows of one account that are goods: demand and consumption receipts.
fn goods_need(
    receipts: &MaterialTickReceipts,
    spec: &AccountSpec,
    good: GoodId,
    unit: UnitId,
    price: i128,
    key: String,
) -> NeedReading {
    let label = &spec.label;
    let demand = receipts
        .household_demand
        .iter()
        .find(|row| {
            row.principal_id == spec.principal && row.good_id == good && row.unit_id == unit
        })
        .unwrap_or_else(|| panic!("{label}: a demand receipt for {key}"));
    let consumption = receipts
        .household_consumption
        .iter()
        .find(|row| {
            row.principal_id == spec.principal && row.good_id == good && row.unit_id == unit
        })
        .unwrap_or_else(|| panic!("{label}: a consumption receipt for {key}"));
    assert_eq!(
        demand.unit_price.micro_units(),
        price,
        "{label}: admission prices {key} at the retailer's offer"
    );
    NeedReading {
        required: consumption.required_quantity,
        unmet: consumption.unmet_quantity,
        unpaid: demand.requested_quantity - demand.admitted_quantity,
        unsupplied: demand.admitted_quantity - demand.fulfilled_quantity,
        cost_micros: i128::from(consumption.required_quantity) * price,
        key,
    }
}

/// The need rows of one account that are services: service and performance receipts.
fn services_need(
    receipts: &MaterialTickReceipts,
    spec: &AccountSpec,
    good: GoodId,
    unit: UnitId,
    price: i128,
    key: String,
) -> NeedReading {
    let account = AccountId::Household(spec.principal);
    let service = receipts
        .household_services
        .iter()
        .find(|row| {
            row.principal_id == spec.principal && row.good_id == good && row.unit_id == unit
        })
        .unwrap_or_else(|| panic!("{}: a service receipt for {key}", spec.label));
    let rows = || {
        receipts
            .service_performance
            .iter()
            .filter(move |row| row.buyer == account && row.good_id == good && row.unit_id == unit)
    };
    NeedReading {
        required: service.required_quantity,
        unmet: service.unmet_quantity,
        unpaid: rows()
            .map(|row| row.requested_quantity - row.admitted_quantity)
            .sum(),
        unsupplied: rows()
            .map(|row| row.admitted_quantity - row.performed_quantity)
            .sum(),
        cost_micros: i128::from(service.required_quantity) * price,
        key,
    }
}

/// The needs of one account in the catalog's order.
fn needs_of(
    session: &Session,
    receipts: &MaterialTickReceipts,
    labels: &[CommodityLabel],
    spec: &AccountSpec,
) -> Vec<NeedReading> {
    session
        .catalog()
        .household_needs
        .iter()
        .filter(|need| need.principal_id == spec.principal)
        .map(|need| {
            let (good, unit) = (need.good_id, need.unit_id);
            let price = price_of(session, spec, good, unit);
            let key = key_of(labels, good, unit, &spec.label);
            if is_service(session, good, unit) {
                services_need(receipts, spec, good, unit, price, key)
            } else {
                goods_need(receipts, spec, good, unit, price, key)
            }
        })
        .collect()
}

/// Reads one close for every spec from the candidate, before it commits. Prices are read from the
/// session, which is still at the opening of the period.
pub fn read_period(
    session: &Session,
    candidate: &PreparedMaterialTick<HypergraphStore>,
    labels: &[CommodityLabel],
    specs: &[AccountSpec],
) -> Vec<PeriodReading> {
    let receipts = material_world::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("canonical material receipts");
    specs
        .iter()
        .map(|spec| period_of(session, &receipts, labels, spec))
        .collect()
}

fn period_of(
    session: &Session,
    receipts: &MaterialTickReceipts,
    labels: &[CommodityLabel],
    spec: &AccountSpec,
) -> PeriodReading {
    let account = AccountId::Household(spec.principal);
    let income = receipts
        .income
        .iter()
        .find(|row| row.account == account)
        .unwrap_or_else(|| panic!("{}: an income receipt", spec.label));
    let company: i128 = receipts
        .company_distributions
        .iter()
        .filter(|row| row.beneficiary == account)
        .map(|row| row.paid.micro_units())
        .sum();
    let site: i128 = receipts
        .distributions
        .iter()
        .filter(|row| row.beneficiary == account)
        .map(|row| row.paid.micro_units())
        .sum();
    assert_eq!(
        company + site,
        income.statement.distribution_income.micro_units(),
        "{}: the two routes of ownership income add to the statement",
        spec.label
    );
    let taxes = || {
        receipts
            .taxes
            .iter()
            .filter(|row| row.payer == account && row.basis == TaxBasis::WageIncome)
    };
    let needs = needs_of(session, receipts, labels, spec);
    PeriodReading {
        wages_micros: income.statement.wage_income.micro_units(),
        support_micros: income.statement.public_transfer_income.micro_units(),
        aid_micros: income.statement.gift_income.micro_units(),
        company_payouts_micros: company,
        site_distributions_micros: site,
        ownership_income_micros: company + site,
        wage_tax_assessed_micros: taxes().map(|row| row.assessed.micro_units()).sum(),
        wage_tax_collected_micros: taxes().map(|row| row.collected.micro_units()).sum(),
        needs_cost_micros: needs.iter().map(|need| need.cost_micros).sum(),
        needs,
    }
}

/// The top tenth's sums. `period` is `None` at the opening, which leaves the two flow sums at 0.
pub fn top_tenth(
    specs: &[AccountSpec],
    accounts: &[AccountReading],
    period: Option<&[PeriodReading]>,
) -> TopTenth {
    let mut sums = TopTenth {
        households: 0,
        net_assets_micros: 0,
        household_net_assets_micros: 0,
        ownership_income_micros: 0,
        needs_cost_micros: 0,
    };
    for (at, (spec, account)) in specs.iter().zip(accounts).enumerate() {
        if account.households > 0 {
            sums.household_net_assets_micros += account.net_assets_micros;
        }
        if !in_top_tenth(spec) {
            continue;
        }
        sums.households += account.households;
        sums.net_assets_micros += account.net_assets_micros;
        if let Some(period) = period {
            sums.ownership_income_micros += period[at].ownership_income_micros;
            sums.needs_cost_micros += period[at].needs_cost_micros;
        }
    }
    sums
}

/// Whether a spec is one of the top tenth, for the tests that name the set.
pub fn is_top_tenth(spec: &AccountSpec) -> bool {
    in_top_tenth(spec)
}
