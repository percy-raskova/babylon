//! A small world that opens in balance: a utility, a farm, a clinic and a shop in one place, one
//! household account for each site's workforce, one owner account that holds every share, and as
//! a variant one public account. The engine runs it period after period, staffed by its own
//! staffing rule, and each period is reduced to a `Snapshot` of what the record measures.
//!
//! The numbers and how they balance are written out in
//! `reports/economy-repair-2026-11-20/small-world.md`.

use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::PublicSpendingRule;
use babylon_material_circuit::{
    AccountId, AidBook, AttendancePlan, CapacityReservations, CapacityRow, CapacitySupply,
    CashAccount, CircuitAccounting, CommodityDefinition, CommodityKind, CorridorCapacity,
    CorridorId, DistributionPolicy, EmploymentTerms, EquityCarryingValue, FinalDemandPrincipal,
    FinalDemandPrincipalId, FinancialInstitutions, GoodId, HistoricalCostBook, HouseholdCohort,
    HouseholdKind, HouseholdNeed, HouseholdNeedBasis, HouseholdPurchasePolicy, HouseholdStandard,
    HouseholdStock, HouseholdTimeAccounting, HouseholdWant, InputOutputCoefficient,
    InstitutionLocation, InventoryRow, LaborCapacityRow, LaborCoefficient, LaborCompensation,
    LogisticsNodeId, MarketClearingPolicy, MaterialCatalog, MaterialCatalogDefinition,
    MaterialCircuitState, MaterialCircuitTransition, MemberLaborCapacityRow, MerchantHandling,
    MerchantHandlingCoefficient, MerchantRole, MonetaryBook, MonetaryCircuit, OwnershipClaim,
    PricePolicy, ProcessId, ProcessOutput, ProductionCommitment, ProductionDemandPolicy,
    PublicAccountId, PublicAllocation, PublicBudget, PublicProgram, PublicProgramKey,
    PublicProgramTerms, PublicTransferTreatment, RecurringEconomy, ReplenishmentPolicy, RouteId,
    SellerOffer, ServiceConnection, ServiceInputPolicy, ServiceStage, SiteId, SiteLogisticsNode,
    StaffingMemberBinding, StaffingMemberId, StaffingMemberReceipt, StaffingMemberState,
    StaffingPolicy, StaffingPoolBinding, StaffingPoolId, StaffingPoolState, StaffingState,
    StaffingWorkSource, StockCarryingValue, SupplierRoute, SupplierTransport, TaxBasis, TaxPolicy,
    UnitId, WantTier,
};
use std::collections::BTreeMap;

/// The key of the fund's benefit for each person.
pub(crate) const NO_EARNER: &str = "no_earner";
/// The key of the fund's half pay after a layoff.
pub(crate) const LAID_OFF: &str = "laid_off";

/// The number of periods of every run.
pub(crate) const PERIODS: u64 = 34;

/// The sites, in the order of every per-site array.
pub(crate) const UTILITY: usize = 0;
pub(crate) const FARM: usize = 1;
pub(crate) const CLINIC: usize = 2;
pub(crate) const SHOP: usize = 3;

/// The goods, in the order of every per-need array.
pub(crate) const FOOD: usize = 0;
pub(crate) const POWER: usize = 1;
pub(crate) const CARE: usize = 2;

/// Units of utility a farm batch takes, and the farm's hours per batch.
const FARM_BATCH_INPUT: u64 = 10;

/// Food per farm batch in the balanced opening. P2 lowers the catalog's yield, not the opening.
const OPENING_FARM_YIELD: u64 = 10;

pub(crate) fn dollars(value: i128) -> Currency {
    Currency::from_micro_units(value * 1_000_000)
}

pub(crate) fn site(index: usize) -> SiteId {
    SiteId::from_bytes([u8::try_from(index + 1).expect("four sites"); 32])
}

fn process(index: usize) -> ProcessId {
    ProcessId::from_bytes([u8::try_from(index + 1).expect("three processes"); 32])
}

fn good(index: usize) -> GoodId {
    GoodId::from_bytes([u8::try_from(index + 1).expect("three goods"); 32])
}

fn units() -> UnitId {
    UnitId::from_bytes([1; 32])
}

fn hours() -> UnitId {
    UnitId::from_bytes([2; 32])
}

pub(crate) fn worker(index: usize) -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([u8::try_from(index + 11).expect("four sites"); 32])
}

fn owner() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([20; 32])
}

pub(crate) fn supported() -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes([21; 32])
}

pub(crate) fn treasury() -> PublicAccountId {
    PublicAccountId::from_bytes([30; 32])
}

pub(crate) fn fund_account() -> PublicAccountId {
    PublicAccountId::from_bytes([31; 32])
}

pub(crate) fn clinic_process() -> ProcessId {
    process(CLINIC)
}

pub(crate) fn member(index: usize) -> StaffingMemberId {
    StaffingMemberId::from_bytes(site(index).as_bytes())
}

fn place() -> EconomicLocation {
    "county:26163"
        .parse()
        .expect("the authored literal parses as a county")
}

/// The public account of the taxed variant.
#[derive(Clone, Debug)]
pub(crate) struct Taxes {
    pub wage_bps: u16,
    pub operating_bps: u16,
    /// Persons of the household account that the public account supports.
    pub supported_persons: u64,
}

/// The fund: a second public account beside the treasury. It taxes the same payers, holds cash,
/// and spends by its own budget.
#[derive(Clone, Debug)]
pub(crate) struct Fund {
    pub wage_bps: u16,
    pub operating_bps: u16,
    pub opening_cash: Currency,
    /// The benefit for each person of the account that does not work.
    pub per_person: Option<Currency>,
    /// The share of a laid-off worker's pay and its length in half periods, paid to the four
    /// worker accounts at rank 0.
    pub after_layoff: Option<(u16, u16)>,
}

/// One change to an opening: the four pushes of the record and one to the fund's taxes.
#[derive(Clone, Copy, Debug)]
pub(crate) enum Push {
    LessDemand,
    LessSupply,
    LessMoney,
    HigherPay,
    LowerFundTaxes,
}

/// Everything that sets one world. `World::plain()` and `World::taxed()` are the two openings.
#[derive(Clone, Debug)]
#[allow(
    clippy::struct_excessive_bools,
    reason = "each switch is one independent rule a run asks for"
)]
pub(crate) struct World {
    pub hours_per_person: u64,
    /// The hourly wage at each site.
    pub wage: [Currency; 4],
    /// The persons of each site's workforce, all employed and all in its household account.
    pub workers: [u64; 4],
    pub owner_persons: u64,
    /// P1: the owner account's cohort counts half its persons, so it needs half as much. Its
    /// opening stock, cash and purchase policy stay those of the balanced opening.
    pub owner_needs_half: bool,
    /// The posted prices of utility, farm food, clinic service and shop food.
    pub price: [Currency; 4],
    pub cash: [Currency; 4],
    pub owner_cash: Currency,
    pub farm_output_per_batch: u64,
    pub taxes: Option<Taxes>,
    /// A second public account, the fund. Set with `with_fund`.
    pub fund: Option<Fund>,
    /// The market policy on the catalog, in the order food, utility, household services.
    pub market: bool,
    /// Every household account wants, per person, one household service in tier 2 and one food
    /// and one utility in tier 3. Set with `with_tiers`, which also sets `market`.
    pub tiers: bool,
    /// Rule A6 on the market policy: a workplace with spare money plans for what was asked of it.
    /// Set with `with_spare_money`, which also sets `market`.
    pub spare_money: bool,
    /// How many periods a run lasts: `PERIODS` unless a test asks for a longer look.
    pub periods: u64,
}

impl World {
    /// No public account. Eight hours a person at ten dollars an hour.
    pub(crate) fn plain() -> Self {
        Self {
            hours_per_person: 8,
            wage: [dollars(10); 4],
            workers: [15, 5, 5, 5],
            owner_persons: 10,
            owner_needs_half: false,
            price: [dollars(12), dollars(25), dollars(30), dollars(38)],
            cash: [dollars(1_200), dollars(880), dollars(880), dollars(1_400)],
            owner_cash: dollars(800),
            farm_output_per_batch: 10,
            taxes: None,
            fund: None,
            market: false,
            tiers: false,
            spare_money: false,
            periods: PERIODS,
        }
    }

    /// A wage tax and an operating-income tax pay one support payment. Ten hours a person.
    pub(crate) fn taxed() -> Self {
        Self {
            hours_per_person: 10,
            workers: [12, 4, 4, 4],
            owner_persons: 8,
            owner_cash: dollars(640),
            taxes: Some(Taxes {
                wage_bps: 2_000,
                operating_bps: 2_000,
                supported_persons: 8,
            }),
            ..Self::plain()
        }
    }

    /// The taxed world with its tax shared between the treasury and a fund: the treasury at 500
    /// points and the fund at 1,500. The fund opens with two periods of payments and pays `no_earner`,
    /// $60 a person, to the account that does not work; the treasury pays the rest of the support.
    pub(crate) fn benefits() -> Self {
        let mut world = Self::taxed();
        let taxes = world
            .taxes
            .as_mut()
            .expect("the taxed world has a treasury");
        taxes.wage_bps = 500;
        taxes.operating_bps = 500;
        world.with_fund(Fund {
            wage_bps: 1_500,
            operating_bps: 1_500,
            opening_cash: dollars(960),
            per_person: Some(dollars(60)),
            after_layoff: Some((5_000, 13)),
        })
    }

    /// P1, less demand: the owner account needs half as much.
    pub(crate) fn less_demand() -> Self {
        Self::plain().pushed(Push::LessDemand)
    }

    /// P2, less supply: the farm's output per batch is a tenth lower.
    pub(crate) fn less_supply() -> Self {
        Self::plain().pushed(Push::LessSupply)
    }

    /// P3, less money: the shop opens with half its cash.
    pub(crate) fn less_money() -> Self {
        Self::plain().pushed(Push::LessMoney)
    }

    /// P4, higher pay: the clinic's wage is a tenth higher.
    pub(crate) fn higher_pay() -> Self {
        Self::plain().pushed(Push::HigherPay)
    }

    /// One push applied to this world, whatever its opening is.
    pub(crate) fn pushed(mut self, push: Push) -> Self {
        match push {
            Push::LessDemand => self.owner_needs_half = true,
            Push::LessSupply => self.farm_output_per_batch = 9,
            Push::LessMoney => self.cash[SHOP] = dollars(700),
            Push::HigherPay => self.wage[CLINIC] = dollars(11),
            Push::LowerFundTaxes => {
                let fund = self
                    .fund
                    .as_mut()
                    .expect("only a world with a fund has fund taxes to lower");
                fund.wage_bps = fund.wage_bps / 4 * 3;
                fund.operating_bps = fund.operating_bps / 4 * 3;
            }
        }
        self
    }

    pub(crate) fn with_market(mut self) -> Self {
        self.market = true;
        self
    }

    /// The market policy with the household wants: comforts and luxuries bought in tiers.
    pub(crate) fn with_tiers(mut self) -> Self {
        self.market = true;
        self.tiers = true;
        self
    }

    /// Rule A6 on the market policy: a workplace holding more money than one period of what it pays
    /// out plans for what was asked of it, as far as that money carries.
    pub(crate) fn with_spare_money(mut self) -> Self {
        self.market = true;
        self.spare_money = true;
        self
    }

    /// The same world, run for `periods` periods. The catalog's horizon follows it.
    pub(crate) fn for_periods(mut self, periods: u64) -> Self {
        self.periods = periods;
        self
    }

    /// A fund beside the treasury: it taxes the same payers at its own rates, holds its cash, and
    /// spends by a budget that is capped at nothing until a program gives it something to pay.
    pub(crate) fn with_fund(mut self, fund: Fund) -> Self {
        self.fund = Some(fund);
        self
    }

    fn supported_persons(&self) -> u64 {
        self.taxes.as_ref().map_or(0, |t| t.supported_persons)
    }

    /// Every consuming person; each needs one food, one utility and one household service.
    fn persons(&self) -> u64 {
        self.workers.iter().sum::<u64>() + self.owner_persons + self.supported_persons()
    }

    /// The opening need of each good: one a person.
    fn need(&self) -> u64 {
        self.workers.iter().sum::<u64>() + self.owner_persons + self.supported_persons()
    }

    /// Opening batches: utility for households, the farm and the clinic; food; services.
    fn batches(&self) -> [u64; 3] {
        let need = self.need();
        let farm = need / 10;
        [need + farm * FARM_BATCH_INPUT + need, farm, need]
    }

    /// The hours each site works at the opening.
    fn site_hours(&self) -> [u64; 4] {
        let [utility, farm, clinic] = self.batches();
        [utility, farm * FARM_BATCH_INPUT, clinic, self.need()]
    }

    /// Every household account with its persons, need rate and opening cash.
    fn households(&self) -> Vec<(FinalDemandPrincipalId, u64, u64, Currency)> {
        let mut rows: Vec<_> = (0..4)
            .map(|i| (worker(i), self.workers[i], 1, dollars(0)))
            .collect();
        rows.push((owner(), self.owner_persons, 1, self.owner_cash));
        if self.taxes.is_some() {
            rows.push((supported(), self.supported_persons(), 1, dollars(0)));
        }
        rows.sort_by_key(|row| row.0);
        rows
    }

    pub(crate) fn build(&self) -> (MaterialCatalog, MaterialCircuitState) {
        assert_eq!(self.persons(), 40, "the world is sized for forty persons");
        (
            MaterialCatalog::try_new(self.definition()).expect("the small-world catalog is valid"),
            self.state(),
        )
    }

    #[allow(clippy::too_many_lines, reason = "a fixture builds its whole catalog")]
    fn definition(&self) -> MaterialCatalogDefinition {
        let mut commodities = vec![
            CommodityDefinition {
                good_id: good(FOOD),
                unit_id: units(),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
            },
            CommodityDefinition {
                good_id: good(POWER),
                unit_id: units(),
                kind: CommodityKind::PeriodService {
                    stage: ServiceStage::UtilityProvision,
                },
            },
            CommodityDefinition {
                good_id: good(CARE),
                unit_id: units(),
                kind: CommodityKind::PeriodService {
                    stage: ServiceStage::LocalServiceProvision,
                },
            },
        ];
        commodities.sort_by_key(|row| (row.good_id, row.unit_id));
        let outputs = [
            (UTILITY, POWER, 1),
            (FARM, FOOD, self.farm_output_per_batch),
            (CLINIC, CARE, 1),
        ];
        let [_, farm, clinic] = self.batches();
        let mut household_needs = vec![];
        for (principal, _, rate, _) in self.households() {
            for g in [FOOD, POWER, CARE] {
                household_needs.push(HouseholdNeed {
                    principal_id: principal,
                    good_id: good(g),
                    unit_id: units(),
                    basis: HouseholdNeedBasis::Persons,
                    units_per_basis: rate,
                });
            }
        }
        household_needs.sort_by_key(|row| (row.principal_id, row.good_id, row.unit_id));
        let farm_utility = farm * FARM_BATCH_INPUT;
        let mut household_wants = vec![];
        if self.tiers {
            for (principal, _, _, _) in self.households() {
                for (tier, g) in [
                    (WantTier::Comfort, CARE),
                    (WantTier::Luxury, FOOD),
                    (WantTier::Luxury, POWER),
                ] {
                    household_wants.push(HouseholdWant {
                        principal_id: principal,
                        tier,
                        good_id: good(g),
                        unit_id: units(),
                        basis: HouseholdNeedBasis::Persons,
                        units_per_basis: 1,
                    });
                }
            }
            household_wants
                .sort_by_key(|row| (row.principal_id, row.tier, row.good_id, row.unit_id));
        }
        MaterialCatalogDefinition {
            market_clearing: self.market.then(|| MarketClearingPolicy {
                plans_from_spare_money: self.spare_money,
                paying_order: [FOOD, POWER, CARE]
                    .into_iter()
                    .map(|g| (good(g), units()))
                    .collect(),
                household_wants,
            }),
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: (0..4)
                .map(|i| SiteLogisticsNode {
                    site_id: site(i),
                    node_id: LogisticsNodeId::from_bytes(site(i).as_bytes()),
                })
                .collect(),
            process_outputs: outputs
                .iter()
                .map(|&(s, g, quantity_per_batch)| ProcessOutput {
                    process_id: process(s),
                    site_id: site(s),
                    good_id: good(g),
                    unit_id: units(),
                    quantity_per_batch,
                })
                .collect(),
            input_coefficients: [(FARM, FARM_BATCH_INPUT), (CLINIC, 1)]
                .into_iter()
                .map(|(s, quantity_per_batch)| InputOutputCoefficient {
                    process_id: process(s),
                    good_id: good(POWER),
                    unit_id: units(),
                    quantity_per_batch,
                })
                .collect(),
            labor_coefficients: [(UTILITY, 1), (FARM, FARM_BATCH_INPUT), (CLINIC, 1)]
                .into_iter()
                .map(|(s, quantity_per_batch)| LaborCoefficient {
                    process_id: process(s),
                    unit_id: hours(),
                    quantity_per_batch,
                })
                .collect(),
            commodities,
            supplier_routes: vec![SupplierRoute {
                buyer_site_id: site(SHOP),
                supplier_site_id: site(FARM),
                good_id: good(FOOD),
                unit_id: units(),
                route_id: RouteId::from_bytes([2; 32]),
                transport_kind: SupplierTransport::Local,
            }],
            route_stages: vec![],
            merchants: vec![MerchantHandling {
                site_id: site(SHOP),
                location: place(),
                role: MerchantRole::Retail,
                capacity_id: CorridorId::from_bytes([4; 32]),
                labor_unit_id: hours(),
            }],
            handling_coefficients: vec![MerchantHandlingCoefficient {
                site_id: site(SHOP),
                good_id: good(FOOD),
                unit_id: units(),
                hours_per_unit: 1,
            }],
            company_portfolios: None,
            company_payouts: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            // The caps are twice the opening requirement, so they never bind in these runs.
            service_inputs: [(FARM, farm_utility), (CLINIC, clinic)]
                .into_iter()
                .map(|(s, quantity)| ServiceInputPolicy {
                    buyer_site_id: site(s),
                    provider_site_id: site(UTILITY),
                    good_id: good(POWER),
                    unit_id: units(),
                    quantity_per_period: 2 * quantity,
                    maximum_purchase: 2 * quantity,
                    cash_floor: dollars(0),
                })
                .collect(),
            household_needs,
        }
    }

    #[allow(
        clippy::too_many_lines,
        reason = "a fixture builds its whole recurring economy"
    )]
    fn recurring(&self) -> RecurringEconomy {
        let need = self.need();
        let [utility, farm, clinic] = self.batches();
        let mut households = vec![];
        let mut stocks = vec![];
        let mut purchases = vec![];
        for (principal, persons, rate, _) in self.households() {
            let required = persons * rate;
            households.push(HouseholdCohort {
                kind: HouseholdKind::Ordinary,
                principal_id: principal,
                households: 1,
                persons: if principal == owner() && self.owner_needs_half {
                    persons / 2
                } else {
                    persons
                },
            });
            // Food is stored: a household keeps one period's need, as the national opening does.
            stocks.push(HouseholdStock {
                principal_id: principal,
                good_id: good(FOOD),
                unit_id: units(),
                quantity: required,
            });
            for (g, seller, target) in [
                (FOOD, SHOP, required),
                (POWER, UTILITY, 0),
                (CARE, CLINIC, 0),
            ] {
                purchases.push(HouseholdPurchasePolicy {
                    principal_id: principal,
                    retailer_site_id: site(seller),
                    good_id: good(g),
                    unit_id: units(),
                    target_closing_stock: target,
                    maximum_purchase: required,
                    enabled: true,
                });
            }
        }
        let step = dollars(1);
        let goods = |target_stock: u64| PricePolicy::Responsive {
            minimum: step,
            maximum: dollars(1_000),
            step,
            target_stock,
        };
        let service = PricePolicy::ServiceResponsive {
            minimum: step,
            maximum: dollars(1_000),
            step,
        };
        let farm_output = farm * OPENING_FARM_YIELD;
        let mut offers = vec![
            SellerOffer {
                site_id: site(UTILITY),
                good_id: good(POWER),
                unit_id: units(),
                unit_price: self.price[UTILITY],
                pricing: service.clone(),
            },
            SellerOffer {
                site_id: site(FARM),
                good_id: good(FOOD),
                unit_id: units(),
                unit_price: self.price[FARM],
                pricing: goods(farm_output),
            },
            SellerOffer {
                site_id: site(CLINIC),
                good_id: good(CARE),
                unit_id: units(),
                unit_price: self.price[CLINIC],
                pricing: service,
            },
            SellerOffer {
                site_id: site(SHOP),
                good_id: good(FOOD),
                unit_id: units(),
                unit_price: self.price[SHOP],
                pricing: goods(need),
            },
        ];
        offers.sort_by_key(|row| (row.site_id, row.good_id, row.unit_id));
        let hours = self.site_hours();
        RecurringEconomy {
            households,
            household_stocks: stocks,
            household_purchases: purchases,
            offers,
            replenishment: vec![ReplenishmentPolicy {
                buyer_site_id: site(SHOP),
                supplier_site_id: site(FARM),
                good_id: good(FOOD),
                unit_id: units(),
                target_stock: need,
                maximum_purchase: need,
                cash_floor: dollars(0),
            }],
            production: [
                (UTILITY, 0, utility),
                (FARM, farm_output, farm),
                (CLINIC, 0, clinic),
            ]
            .into_iter()
            .map(
                |(s, output_buffer, planned_batches)| ProductionDemandPolicy {
                    process_id: process(s),
                    site_id: site(s),
                    output_buffer,
                    planned_batches,
                },
            )
            .collect(),
            attendance: (0..4)
                .map(|i| AttendancePlan {
                    site_id: site(i),
                    unit_id: self::hours(),
                    period: 1,
                    planned_hours: hours[i],
                })
                .collect(),
            last_household_admission_period: 0,
            last_household_consumption_period: 0,
        }
    }

    fn financial(&self) -> FinancialInstitutions {
        let mut f = FinancialInstitutions::empty();
        for i in 0..4 {
            f.ownership.push(OwnershipClaim {
                issuer_site_id: site(i),
                beneficiary: AccountId::Household(owner()),
                shares: 1,
            });
            f.distributions.push(DistributionPolicy {
                issuer_site_id: site(i),
                earnings_fraction_bps: 10_000,
                period_cap: dollars(1_000_000),
                cash_floor: dollars(0),
            });
        }
        if let Some(taxes) = &self.taxes {
            let public = AccountId::Public(treasury());
            f.locations.push(InstitutionLocation {
                account: public,
                location: place(),
            });
            for i in 0..4 {
                f.taxes.push(TaxPolicy {
                    payer: AccountId::Household(worker(i)),
                    public_recipient: treasury(),
                    basis: TaxBasis::WageIncome,
                    rate_bps: taxes.wage_bps,
                    cash_floor: dollars(0),
                });
                f.taxes.push(TaxPolicy {
                    payer: AccountId::Site(site(i)),
                    public_recipient: treasury(),
                    basis: TaxBasis::PositiveOperatingIncome,
                    rate_bps: taxes.operating_bps,
                    cash_floor: dollars(0),
                });
            }
            let support = self.support_payment();
            f.public_budgets.push(PublicBudget {
                public_account: treasury(),
                period_cap: support,
                cash_floor: dollars(0),
                rule: PublicSpendingRule::CappedInOrder,
            });
            f.public_allocations.push(PublicAllocation {
                public_account: treasury(),
                recipient: AccountId::Household(supported()),
                treatment: PublicTransferTreatment::HouseholdIncomeSupport,
                priority: 0,
                amount_per_period: support,
            });
        }
        if let Some(fund) = &self.fund {
            Self::add_fund(&mut f, fund);
        }
        f
    }

    /// The fund's location, its tax rows on every worker household and site, and its budget.
    fn add_fund(f: &mut FinancialInstitutions, fund: &Fund) {
        f.locations.push(InstitutionLocation {
            account: AccountId::Public(fund_account()),
            location: place(),
        });
        for i in 0..4 {
            f.taxes.push(TaxPolicy {
                payer: AccountId::Household(worker(i)),
                public_recipient: fund_account(),
                basis: TaxBasis::WageIncome,
                rate_bps: fund.wage_bps,
                cash_floor: dollars(0),
            });
            f.taxes.push(TaxPolicy {
                payer: AccountId::Site(site(i)),
                public_recipient: fund_account(),
                basis: TaxBasis::PositiveOperatingIncome,
                rate_bps: fund.operating_bps,
                cash_floor: dollars(0),
            });
        }
        f.public_budgets.push(PublicBudget {
            public_account: fund_account(),
            period_cap: dollars(0),
            cash_floor: dollars(0),
            rule: PublicSpendingRule::CashInProportion,
        });
        if let Some(amount_per_person) = fund.per_person {
            f.programs.push(PublicProgram {
                key: PublicProgramKey::new(NO_EARNER).expect("a well-formed key"),
                payer: fund_account(),
                rank: 0,
                terms: PublicProgramTerms::PerPerson { amount_per_person },
                recipients: vec![supported()],
            });
        }
        if let Some((wage_share_bps, half_periods)) = fund.after_layoff {
            let mut recipients: Vec<_> = (0..4).map(worker).collect();
            recipients.sort();
            f.programs.push(PublicProgram {
                key: PublicProgramKey::new(LAID_OFF).expect("a well-formed key"),
                payer: fund_account(),
                rank: 0,
                terms: PublicProgramTerms::AfterLayoff {
                    wage_share_bps,
                    half_periods,
                },
                recipients,
            });
            f.programs.sort_by(|a, b| a.key.cmp(&b.key));
        }
    }

    /// The basket of one person at the opening prices.
    fn basket(&self) -> Currency {
        Currency::from_micro_units(
            self.price[SHOP].micro_units()
                + self.price[UTILITY].micro_units()
                + self.price[CLINIC].micro_units(),
        )
    }

    /// What the treasury pays the supported account: its basket, less the fund's benefit.
    fn support_payment(&self) -> Currency {
        let benefit = self
            .fund
            .as_ref()
            .and_then(|fund| fund.per_person)
            .map_or(0, Currency::micro_units);
        Currency::from_micro_units(
            (self.basket().micro_units() - benefit) * i128::from(self.supported_persons()),
        )
    }

    #[allow(clippy::too_many_lines, reason = "a fixture builds its whole state")]
    fn state(&self) -> MaterialCircuitState {
        let need = self.need();
        let [utility, farm, clinic] = self.batches();
        let farm_output = farm * OPENING_FARM_YIELD;
        let mut accounts: Vec<_> = (0..4)
            .map(|i| CashAccount {
                id: AccountId::Site(site(i)),
                cash: self.cash[i],
            })
            .collect();
        for (principal, _, _, cash) in self.households() {
            accounts.push(CashAccount {
                id: AccountId::Household(principal),
                cash,
            });
        }
        if self.taxes.is_some() {
            accounts.push(CashAccount {
                id: AccountId::Public(treasury()),
                cash: self.support_payment(),
            });
        }
        if let Some(fund) = &self.fund {
            accounts.push(CashAccount {
                id: AccountId::Public(fund_account()),
                cash: fund.opening_cash,
            });
        }
        let book = MonetaryBook::open(accounts).expect("the small world opens its accounts");
        let unit_cost = |price: Currency, quantity: u64| {
            Currency::from_micro_units(price.micro_units() * i128::from(quantity))
        };
        // Opening stock is carried at what it cost: the farm's direct cost per unit, the shop's
        // purchase price, and the shop's price for what households hold.
        let farm_unit = Currency::from_micro_units(
            (self.wage[FARM].micro_units() * i128::from(FARM_BATCH_INPUT)
                + self.price[UTILITY].micro_units() * i128::from(FARM_BATCH_INPUT))
                / i128::from(OPENING_FARM_YIELD),
        );
        let mut carrying = vec![
            StockCarryingValue {
                owner: AccountId::Site(site(FARM)),
                good_id: good(FOOD),
                unit_id: units(),
                amount: unit_cost(farm_unit, farm_output),
            },
            StockCarryingValue {
                owner: AccountId::Site(site(SHOP)),
                good_id: good(FOOD),
                unit_id: units(),
                amount: unit_cost(self.price[FARM], need),
            },
        ];
        for (principal, persons, rate, _) in self.households() {
            carrying.push(StockCarryingValue {
                owner: AccountId::Household(principal),
                good_id: good(FOOD),
                unit_id: units(),
                amount: unit_cost(self.price[SHOP], persons * rate),
            });
        }
        let equity = (0..4)
            .map(|i| EquityCarryingValue {
                owner: AccountId::Household(owner()),
                issuer_site_id: site(i),
                amount: dollars(0),
            })
            .collect();
        let costs = HistoricalCostBook::open(&book, carrying, vec![], equity, vec![])
            .expect("the small world opens its historical costs");
        let hours = self.site_hours();
        let horizon = self.periods + 2;
        let capacity = [utility, 2 * farm, clinic];
        MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                aid: AidBook::default(),
                household_time: HouseholdTimeAccounting::NotModeled,
                financial: self.financial(),
                member_labor: (0..4)
                    .map(|i| MemberLaborCapacityRow {
                        member_id: member(i),
                        period: 1,
                        available_hours: hours[i],
                    })
                    .collect(),
                costs,
                book,
                recurring: Some(Box::new(self.recurring())),
                employment: (0..4)
                    .map(|i| EmploymentTerms {
                        member_id: member(i),
                        site_id: site(i),
                        unit_id: self::hours(),
                        payee: worker(i),
                        compensation: LaborCompensation::Wage(self.wage[i]),
                    })
                    .collect(),
            })),
            service_connections: self.connections(),
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: vec![
                InventoryRow {
                    site_id: site(FARM),
                    good_id: good(FOOD),
                    unit_id: units(),
                    quantity: farm_output,
                },
                InventoryRow {
                    site_id: site(SHOP),
                    good_id: good(FOOD),
                    unit_id: units(),
                    quantity: need,
                },
            ],
            orders: vec![],
            freight: vec![],
            corridor_capacities: (1..=horizon)
                .map(|period| CorridorCapacity {
                    corridor_id: CorridorId::from_bytes([4; 32]),
                    period,
                    available_grams: 1_000_000,
                })
                .collect(),
            capacities: (1..=horizon)
                .flat_map(|period| {
                    (0..3).map(move |i| CapacityRow {
                        process_id: process(i),
                        site_id: site(i),
                        period,
                        available_batches: capacity[i],
                    })
                })
                .collect(),
            labor: (0..4)
                .map(|i| LaborCapacityRow {
                    site_id: site(i),
                    unit_id: self::hours(),
                    period: 1,
                    available: hours[i],
                })
                .collect(),
            production_commitments: [utility, farm, clinic]
                .into_iter()
                .enumerate()
                .map(|(i, planned_batches)| ProductionCommitment {
                    process_id: process(i),
                    site_id: site(i),
                    period: 1,
                    planned_batches,
                })
                .collect(),
            final_demand_principals: self
                .households()
                .into_iter()
                .map(|(id, _, _, _)| FinalDemandPrincipal {
                    id,
                    location: place(),
                })
                .collect(),
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        }
    }

    fn connections(&self) -> Vec<ServiceConnection> {
        let mut rows = vec![];
        for (principal, _, _, _) in self.households() {
            for (g, provider) in [(POWER, UTILITY), (CARE, CLINIC)] {
                rows.push(ServiceConnection {
                    provider_site_id: site(provider),
                    buyer: AccountId::Household(principal),
                    good_id: good(g),
                    unit_id: units(),
                });
            }
        }
        for buyer in [FARM, CLINIC] {
            rows.push(ServiceConnection {
                provider_site_id: site(UTILITY),
                buyer: AccountId::Site(site(buyer)),
                good_id: good(POWER),
                unit_id: units(),
            });
        }
        rows.sort();
        rows
    }

    /// One staffing pool per site, its whole workforce employed, its last request the opening's.
    fn staffing(&self) -> (Vec<StaffingPoolBinding>, StaffingState) {
        let hours = self.site_hours();
        let bindings: Vec<_> = (0..4)
            .map(|i| {
                let source = if i == SHOP {
                    StaffingWorkSource::MerchantHandling(site(i))
                } else {
                    StaffingWorkSource::Production(process(i))
                };
                StaffingPoolBinding::try_new(
                    StaffingPoolId::from_bytes(site(i).as_bytes()),
                    site(i),
                    self::hours(),
                    self.workers[i],
                    StaffingPolicy::one_period(self.hours_per_person).expect("a positive schedule"),
                    vec![source],
                )
                .expect("one work source per pool")
            })
            .collect();
        let pools = bindings
            .iter()
            .enumerate()
            .map(|(i, binding)| {
                StaffingPoolState::try_new(binding.clone(), self.workers[i], 0, hours[i])
                    .expect("the whole workforce is employed")
            })
            .collect();
        (
            bindings,
            StaffingState::try_new(1, pools).expect("the pools are distinct"),
        )
    }
}

/// What the record measures of one closed period.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Snapshot {
    pub period: u64,
    /// Closing cash in whole dollars (exact micro-units are kept in `micro_cash`).
    pub cash: BTreeMap<&'static str, i128>,
    pub micro_cash: BTreeMap<&'static str, i128>,
    /// By site: the batches (shop: handling hours) planned for the next period.
    pub planned: [u64; 4],
    /// By site: the hours asked of staffing for the next period.
    pub asked: [u64; 4],
    /// By site: hours planned, attended and used in this period.
    pub hours_planned: [u64; 4],
    pub hours_attended: [u64; 4],
    pub hours_used: [u64; 4],
    /// By site: persons employed for the next period.
    pub employed: [u64; 4],
    /// Utility, farm and clinic output in units; the shop's is what it received.
    pub output: [u64; 4],
    /// Closing stock of food at the farm and the shop (zero for the services).
    pub stock: [u64; 4],
    /// The posted price for the next period, in whole cents.
    pub price_cents: [i128; 4],
    /// Units sold: utility and clinic performed, farm to the shop, shop to households.
    pub sales: [u64; 4],
    /// By need, summed over household accounts: requirement, purchase, consumption, unmet.
    pub required: [u64; 3],
    pub bought: [u64; 3],
    pub consumed: [u64; 3],
    pub unmet: [u64; 3],
    /// Unmet need of each good by account name.
    pub unmet_by_account: BTreeMap<&'static str, [u64; 3]>,
    /// By site: the price at which a short market cleared this period, in cents; 0 if none.
    pub cleared_cents: [i128; 4],
    /// Units bought for wants, by good.
    pub want_bought: [u64; 3],
    /// By account, in whole dollars at posted prices, (wanted, bought) in tiers 2 and 3.
    pub tier_values: BTreeMap<&'static str, [(i128, i128); 2]>,
    /// By account, how well it lived this period. Empty without wants.
    pub standards: BTreeMap<&'static str, HouseholdStandard>,
    /// By program key and account name, in micro-units, what each program owed and paid.
    pub program_due: BTreeMap<(String, &'static str), i128>,
    pub program_paid: BTreeMap<(String, &'static str), i128>,
    /// By account name, the persons the programs counted for it.
    pub covered: BTreeMap<&'static str, u64>,
    pub public_receipts: i128,
    pub public_payments: i128,
    pub total_money: i128,
}

fn account_name(id: AccountId) -> &'static str {
    match id {
        AccountId::Site(s) if s == site(UTILITY) => "utility",
        AccountId::Site(s) if s == site(FARM) => "farm",
        AccountId::Site(s) if s == site(CLINIC) => "clinic",
        AccountId::Site(s) if s == site(SHOP) => "shop",
        AccountId::Household(h) if h == worker(UTILITY) => "w_utility",
        AccountId::Household(h) if h == worker(FARM) => "w_farm",
        AccountId::Household(h) if h == worker(CLINIC) => "w_clinic",
        AccountId::Household(h) if h == worker(SHOP) => "w_shop",
        AccountId::Household(h) if h == owner() => "owner",
        AccountId::Household(h) if h == supported() => "supported",
        AccountId::Public(p) if p == fund_account() => "fund",
        AccountId::Public(_) => "public",
        other => panic!("an account outside the small world: {other:?}"),
    }
}

fn site_index(id: SiteId) -> usize {
    (0..4)
        .find(|&i| site(i) == id)
        .expect("a site of the small world")
}

fn good_index(id: GoodId) -> usize {
    (0..3)
        .find(|&i| good(i) == id)
        .expect("a good of the small world")
}

fn economy(state: &MaterialCircuitState) -> &MonetaryCircuit {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        panic!("the small world is monetary")
    };
    e
}

type TierMeasures = (
    [u64; 3],
    BTreeMap<&'static str, [(i128, i128); 2]>,
    BTreeMap<&'static str, HouseholdStandard>,
);

/// What the period's want and tier records say: units bought for wants, each account's values by
/// tier, and each account's standard.
fn tier_measures(closed: &MaterialCircuitTransition) -> TierMeasures {
    let mut want_bought = [0; 3];
    for row in &closed.household_wants {
        want_bought[good_index(row.good_id)] += row.bought_quantity;
    }
    let mut tier_values = BTreeMap::new();
    let mut standards = BTreeMap::new();
    for row in &closed.household_tiers {
        let name = account_name(AccountId::Household(row.principal_id));
        let slot = match row.tier {
            WantTier::Comfort => 0,
            WantTier::Luxury => 1,
        };
        tier_values.entry(name).or_insert([(0, 0); 2])[slot] = (
            row.wanted_value.micro_units() / 1_000_000,
            row.bought_value.micro_units() / 1_000_000,
        );
        standards.entry(name).or_insert_with(|| {
            babylon_material_circuit::household_standard(
                row.principal_id,
                &closed.household_consumption,
                &closed.household_services,
                &closed.household_tiers,
            )
            .expect("every account has both tier rows")
        });
    }
    (want_bought, tier_values, standards)
}

#[allow(clippy::too_many_lines, reason = "one reduction of every measured row")]
fn snapshot(
    catalog: &MaterialCatalog,
    closed: &MaterialCircuitTransition,
    asked: [u64; 4],
    employed: [u64; 4],
) -> Snapshot {
    let state = &closed.state;
    let e = economy(state);
    let mut cash = BTreeMap::new();
    let mut micro_cash = BTreeMap::new();
    for row in e.book.snapshot().accounts {
        let name = account_name(row.id);
        micro_cash.insert(name, row.cash.micro_units());
        cash.insert(name, row.cash.micro_units() / 1_000_000);
    }
    let recurring = e.recurring.as_ref().expect("the world is recurring");
    let mut planned = [0; 4];
    for row in &recurring.production {
        planned[site_index(row.site_id)] = row.planned_batches;
    }
    for row in &recurring.attendance {
        if row.site_id == site(SHOP) {
            planned[SHOP] = row.planned_hours;
        }
    }
    let mut hours_planned = [0; 4];
    let mut hours_attended = [0; 4];
    let mut hours_used = [0; 4];
    for row in &closed.labor_use {
        let i = site_index(row.site_id);
        hours_planned[i] = row.planned_hours;
        hours_attended[i] = row.funded_hours + row.non_wage_hours;
        hours_used[i] = row.used_hours;
    }
    let mut output = [0; 4];
    for row in &closed.production {
        let i = site_index(row.site_id);
        let per_batch = catalog
            .process_outputs
            .iter()
            .find(|o| o.process_id == row.process_id)
            .expect("a process of the catalog")
            .quantity_per_batch;
        output[i] = row.produced_batches * per_batch;
    }
    let mut sales = [0; 4];
    for row in &closed.local_transfers {
        sales[site_index(row.supplier_site_id)] += row.quantity;
        output[site_index(row.buyer_site_id)] += row.quantity;
    }
    for row in &closed.local_fulfillments {
        sales[site_index(row.retailer_site_id)] += row.quantity;
    }
    for row in &closed.service_markets {
        sales[site_index(row.site_id)] += row.performed_quantity;
    }
    let mut stock = [0; 4];
    for row in &state.inventory {
        stock[site_index(row.site_id)] += row.quantity;
    }
    let mut price_cents = [0; 4];
    for row in &recurring.offers {
        price_cents[site_index(row.site_id)] = row.unit_price.micro_units() / 10_000;
    }
    let mut required = [0; 3];
    let mut bought = [0; 3];
    let mut consumed = [0; 3];
    let mut unmet = [0; 3];
    let mut unmet_by_account = BTreeMap::new();
    for row in &closed.household_demand {
        bought[good_index(row.good_id)] += row.fulfilled_quantity;
    }
    for row in &closed.household_consumption {
        let g = good_index(row.good_id);
        required[g] += row.required_quantity;
        consumed[g] += row.consumed_quantity;
        unmet[g] += row.unmet_quantity;
        unmet_by_account
            .entry(account_name(AccountId::Household(row.principal_id)))
            .or_insert([0; 3])[g] += row.unmet_quantity;
    }
    for row in &closed.household_services {
        let g = good_index(row.good_id);
        required[g] += row.required_quantity;
        bought[g] += row.performed_quantity;
        consumed[g] += row.satisfied_quantity;
        unmet[g] += row.unmet_quantity;
        unmet_by_account
            .entry(account_name(AccountId::Household(row.principal_id)))
            .or_insert([0; 3])[g] += row.unmet_quantity;
    }
    let mut cleared_cents = [0; 4];
    for row in &closed.market_clearings {
        let i = site_index(row.site_id);
        cleared_cents[i] = cleared_cents[i].max(row.clearing_price.micro_units() / 10_000);
    }
    let (want_bought, tier_values, standards) = tier_measures(closed);
    let mut program_due = BTreeMap::new();
    let mut program_paid = BTreeMap::new();
    let mut covered = BTreeMap::new();
    for row in &closed.public_programs {
        let name = account_name(AccountId::Household(row.recipient));
        let key = (row.program.as_str().to_owned(), name);
        program_due.insert(key.clone(), row.due.micro_units());
        program_paid.insert(key, row.paid.micro_units());
        *covered.entry(name).or_insert(0) += row.covered_persons;
    }
    Snapshot {
        program_due,
        program_paid,
        covered,
        period: state.period - 1,
        cleared_cents,
        want_bought,
        tier_values,
        standards,
        cash,
        micro_cash,
        planned,
        asked,
        hours_planned,
        hours_attended,
        hours_used,
        employed,
        output,
        stock,
        price_cents,
        sales,
        required,
        bought,
        consumed,
        unmet,
        unmet_by_account,
        public_receipts: closed
            .taxes
            .iter()
            .map(|r| r.collected.micro_units())
            .sum::<i128>()
            / 1_000_000,
        public_payments: (closed
            .public_budgets
            .iter()
            .map(|r| r.paid.micro_units())
            .chain(closed.public_programs.iter().map(|r| r.paid.micro_units()))
            .sum::<i128>())
            / 1_000_000,
        total_money: e
            .book
            .total_cash_and_reserves()
            .expect("the book totals")
            .micro_units(),
    }
}

/// The opening as a snapshot of period zero, for the comparisons of the quiet run.
pub(crate) fn opening_cash(world: &World) -> BTreeMap<&'static str, i128> {
    let (_, state) = world.build();
    economy(&state)
        .book
        .snapshot()
        .accounts
        .into_iter()
        .map(|row| (account_name(row.id), row.cash.micro_units() / 1_000_000))
        .collect()
}

/// Run a world for `PERIODS` periods: close, staff from the engine's own requests, finish.
pub(crate) fn run(world: &World) -> Vec<Snapshot> {
    run_observed(world, &mut |_, _| {})
}

/// `run`, showing each finished period's transition to `observe`.
pub(crate) fn run_observed(
    world: &World,
    observe: &mut dyn FnMut(u64, &MaterialCircuitTransition),
) -> Vec<Snapshot> {
    run_staffed(world, None, observe)
}

/// A run in which staffing is done by hand: `employed(p)` is each site's persons after period `p`.
/// It tests the programs, not the staffing rule.
pub(crate) fn run_driven(world: &World, employed: impl Fn(u64) -> [u64; 4]) -> Vec<Snapshot> {
    run_staffed(world, Some(&employed), &mut |_, _| {})
}

/// The one member of a site's pool, as the engine's staffing sees it.
fn member_state(world: &World, site_index: usize, employed: u64) -> StaffingMemberState {
    let force = world.workers[site_index];
    let binding = StaffingMemberBinding::from_living_force(
        member(site_index),
        worker(site_index),
        place(),
        force,
    );
    StaffingMemberState::try_new(binding, employed, force - employed)
        .expect("the member's persons are the pool's")
}

/// What the engine's staffing decided for the next period.
pub(crate) struct Staffed {
    pub labor: Vec<LaborCapacityRow>,
    pub receipts: Vec<StaffingMemberReceipt>,
    pub employed: [u64; 4],
}
impl Staffed {
    /// One member row for each site's labor row.
    pub(crate) fn member_labor(&self) -> Vec<MemberLaborCapacityRow> {
        self.labor
            .iter()
            .map(|row| MemberLaborCapacityRow {
                member_id: member(site_index(row.site_id)),
                period: row.period,
                available_hours: row.available,
            })
            .collect()
    }
}

fn labor_row(world: &World, closed_period: u64, i: usize, employed: u64) -> LaborCapacityRow {
    LaborCapacityRow {
        site_id: site(i),
        unit_id: self::hours(),
        period: closed_period + 1,
        available: employed * world.hours_per_person,
    }
}

/// Staffing by hand: each site's persons after the period are given.
pub(crate) fn staff_by_hand(
    world: &World,
    period: u64,
    before: [u64; 4],
    after: [u64; 4],
) -> Staffed {
    let mut labor = Vec::new();
    let mut receipts = Vec::new();
    for i in 0..4 {
        labor.push(labor_row(world, period, i, after[i]));
        let force = world.workers[i];
        let (hires, separations) = (
            after[i].saturating_sub(before[i]),
            before[i].saturating_sub(after[i]),
        );
        let receipt = StaffingMemberReceipt {
            period,
            pool_id: StaffingPoolId::from_bytes(site(i).as_bytes()),
            site_id: site(i),
            unit_id: self::hours(),
            member: member_state(world, i, before[i]).binding().clone(),
            hours_per_person: world.hours_per_person,
            opening_employed: before[i],
            opening_reserve: force - before[i],
            hires,
            separations,
            closing_employed: after[i],
            closing_reserve: force - after[i],
            next_opening_hours: after[i] * world.hours_per_person,
        };
        receipt
            .validate()
            .expect("the hand staffing conserves persons");
        receipts.push(receipt);
    }
    Staffed {
        labor,
        receipts,
        employed: after,
    }
}

pub(crate) fn run_staffed(
    world: &World,
    by_hand: Option<&dyn Fn(u64) -> [u64; 4]>,
    observe: &mut dyn FnMut(u64, &MaterialCircuitTransition),
) -> Vec<Snapshot> {
    let (catalog, mut state) = world.build();
    let (bindings, mut staffing) = world.staffing();
    let opening_money = economy(&state)
        .book
        .total_cash_and_reserves()
        .expect("the book totals")
        .micro_units();
    let mut rows = Vec::new();
    let mut before = world.workers;
    for period in 1..=world.periods {
        let closed = babylon_material_circuit::close_material_period(&catalog, &state)
            .unwrap_or_else(|e| panic!("period {period} closes: {e:?}"));
        let requests = closed
            .staffing_requests(&catalog, &bindings)
            .unwrap_or_else(|e| panic!("period {period} asks for staff: {e:?}"));
        let mut asked = [0; 4];
        for request in &requests {
            asked[site_index(request.site_id())] += request.hours();
        }
        let staffed = if let Some(employed) = by_hand {
            staff_by_hand(world, period, before, employed(period))
        } else {
            let staffed = babylon_material_circuit::advance_staffing(&staffing, &requests)
                .unwrap_or_else(|e| panic!("period {period} staffs: {e:?}"));
            let mut employed = [0; 4];
            let mut receipts = Vec::new();
            for receipt in staffed.receipts() {
                let i = site_index(receipt.binding().site_id());
                employed[i] = receipt.closing_employed();
                let members = [member_state(world, i, receipt.opening_employed())];
                receipts.extend(
                    babylon_material_circuit::distribute_staffing_members(receipt, &members)
                        .unwrap_or_else(|e| panic!("period {period} has members: {e:?}")),
                );
            }
            let labor = staffed.next_labor().to_vec();
            staffing = staffed.into_state();
            Staffed {
                labor,
                receipts,
                employed,
            }
        };
        let members = staffed.member_labor();
        let closed = closed
            .finish_with_staffing(&catalog, staffed.labor, members, &staffed.receipts)
            .unwrap_or_else(|e| panic!("period {period} finishes: {e:?}"));
        observe(period, &closed);
        before = staffed.employed;
        let row = snapshot(&catalog, &closed, asked, staffed.employed);
        assert_eq!(
            row.total_money, opening_money,
            "period {period}: money is conserved"
        );
        rows.push(row);
        state = closed.state;
    }
    rows
}

/// Every period's measures equal the first period's, and the first period's cash is the opening's.
pub(crate) fn assert_still(world: &World) -> Snapshot {
    assert_still_rows(world, &run(world))
}

/// `assert_still` over rows the caller already produced from `world`.
pub(crate) fn assert_still_rows(world: &World, rows: &[Snapshot]) -> Snapshot {
    assert_eq!(
        rows.len(),
        usize::try_from(world.periods).expect("few periods")
    );
    let first = rows[0].clone();
    assert_eq!(
        first.cash,
        opening_cash(world),
        "period 1 closes with the opening cash"
    );
    for row in rows {
        let mut same = row.clone();
        same.period = first.period;
        assert_eq!(same, first, "period {} moved", row.period);
    }
    assert_eq!(first.planned, [120, 4, 40, 40]);
    assert_eq!(first.hours_attended, [120, 40, 40, 40]);
    assert_eq!(first.output, [120, 40, 40, 40]);
    assert_eq!(first.stock, [0, 40, 0, 40]);
    assert_eq!(first.price_cents, [1_200, 2_500, 3_000, 3_800]);
    assert_eq!(first.sales, [120, 40, 40, 40]);
    for good in [FOOD, POWER, CARE] {
        assert_eq!(first.required[good], 40);
        assert_eq!(first.consumed[good], 40);
        assert_eq!(first.unmet[good], 0);
    }
    first
}

/// One table line per shown period, for the record. Printed only by the ignored dump test.
pub(crate) fn describe(name: &str, rows: &[Snapshot]) -> String {
    use std::fmt::Write;
    let mut text = format!("== {name}\n");
    for row in rows {
        let _ = writeln!(
            text,
            "p{:>2} cash {:?} | planned {:?} asked {:?} hp {:?} att {:?} used {:?} emp {:?} | out {:?} stock {:?} price {:?} sales {:?} | req {:?} bought {:?} cons {:?} unmet {:?} {:?} | pub {} {} | cleared {:?} | wants {:?} tiers {:?} standards {:?}",
            row.period,
            row.cash,
            row.planned,
            row.asked,
            row.hours_planned,
            row.hours_attended,
            row.hours_used,
            row.employed,
            row.output,
            row.stock,
            row.price_cents,
            row.sales,
            row.required,
            row.bought,
            row.consumed,
            row.unmet,
            row.unmet_by_account,
            row.public_receipts,
            row.public_payments,
            row.cleared_cents,
            row.want_bought,
            row.tier_values,
            row.standards,
        );
        if !row.program_due.is_empty() {
            let _ = writeln!(
                text,
                "    programs due {:?} paid {:?} covered {:?}",
                row.program_due, row.program_paid, row.covered
            );
        }
    }
    text
}
