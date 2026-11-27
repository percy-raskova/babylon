//! The restart's price raise (step (b) of the owner's restart) keeps each offer inside its own range and
//! leaves alone a provider that a public body funds with an operating grant.
//!
//! The fixture is the doubled world at the restart's figures, opened and then changed by the test: the
//! clinic of place A has its people's hours of period 1 taken away (so its price rests at the first close),
//! its posted price lowered under one unit's cost, and its offer's range set as each case needs.

use babylon_circuit_worlds::doubled::{self, Figures};
use babylon_circuit_worlds::{Kind, Place, ShockBook, Workplace, World};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    self as engine, AccountId, AdjustmentReceipt, CircuitAccounting, MaterialCircuitError,
    MaterialCircuitState, MaterialCircuitTransition, PricePolicy, PublicAllocation,
    PublicTransferTreatment, SiteId, WorkplaceStanding,
};

fn dollars(whole: i128) -> Currency {
    Currency::from_micro_units(whole * 1_000_000)
}

fn clinic() -> SiteId {
    Workplace {
        place: Place::A,
        kind: Kind::Clinic,
    }
    .site_id()
}

/// What the clinic's offer is made to look like.
struct Clinic {
    price: Currency,
    pricing: PricePolicy,
    grant: bool,
}

/// Open the doubled world at the restart's figures, change the clinic as asked, and close period 1 the way the
/// runner does for a world whose people look for work in their place.
fn close_first_period(
    clinic_is: &Clinic,
) -> Result<MaterialCircuitTransition, MaterialCircuitError> {
    let mut world = World::scene();
    world.rules = World::switches_at(world.scale)[..5].to_vec();
    let figures: Figures = ShockBook::default().figures(1);
    let catalog = doubled::catalog_of(&world, &figures, &world.rules).expect("the catalog");
    let mut state: MaterialCircuitState = doubled::opening_state_of(&world).expect("the opening");
    let site = clinic();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the opening is monetary");
    };
    let members: Vec<_> = economy
        .employment
        .iter()
        .filter(|terms| terms.site_id == site)
        .map(|terms| terms.member_id)
        .collect();
    for row in economy
        .member_labor
        .iter_mut()
        .filter(|row| members.contains(&row.member_id))
    {
        row.available_hours = 0;
    }
    for row in state.labor.iter_mut().filter(|row| row.site_id == site) {
        row.available = 0;
    }
    if clinic_is.grant {
        economy.financial.public_allocations.push(PublicAllocation {
            public_account: babylon_circuit_worlds::treasury(),
            recipient: AccountId::Site(site),
            treatment: PublicTransferTreatment::ProviderOperatingGrant,
            priority: 1,
            amount_per_period: dollars(1),
        });
    }
    let recurring = economy.recurring.as_mut().expect("a recurring economy");
    for row in recurring
        .attendance
        .iter_mut()
        .filter(|row| row.site_id == site)
    {
        row.planned_hours = 0;
    }
    for offer in recurring.offers.iter_mut().filter(|o| o.site_id == site) {
        offer.unit_price = clinic_is.price;
        offer.pricing = clinic_is.pricing.clone();
    }
    let staffing = doubled::staffing_of(&world).expect("staffing").1;
    let pools = doubled::pool_members_of(&world).expect("members");
    let closed = engine::close_material_period_with_standing(
        &catalog,
        &state,
        &WorkplaceStanding::opening(),
    )?;
    let placed = closed
        .staff_in_places(&catalog, &staffing, &pools, &doubled::places())
        .expect("staffing in places");
    closed.finish_with_place_staffing(&catalog, &placed)
}

fn range(maximum: Currency) -> PricePolicy {
    PricePolicy::ServiceResponsive {
        minimum: dollars(1),
        maximum,
        step: dollars(1),
    }
}

fn raises(closed: &MaterialCircuitTransition) -> Vec<(Currency, Currency)> {
    closed
        .adjustments
        .iter()
        .filter_map(|row| match row {
            AdjustmentReceipt::RestingPriceToCost(r) if r.site_id == clinic() => {
                Some((r.old, r.raised))
            }
            _ => None,
        })
        .collect()
}

fn offer_price(closed: &MaterialCircuitTransition) -> Currency {
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        panic!("monetary");
    };
    economy
        .recurring
        .as_ref()
        .expect("recurring")
        .offers
        .iter()
        .find(|o| o.site_id == clinic())
        .expect("the clinic's offer")
        .unit_price
}

#[test]
fn a_resting_price_is_raised_no_further_than_its_offer_allows() {
    let closed = close_first_period(&Clinic {
        price: dollars(1),
        pricing: range(dollars(2)),
        grant: false,
    })
    .expect("the period closes");
    assert_eq!(offer_price(&closed), dollars(2));
    assert_eq!(raises(&closed), vec![(dollars(1), dollars(2))]);
    let site = clinic();
    for row in closed.prices.iter().filter(|r| r.site_id == site) {
        assert_eq!(row.next_price, dollars(2));
    }
    let markets: Vec<_> = closed
        .service_markets
        .iter()
        .filter(|r| r.site_id == site)
        .collect();
    assert!(!markets.is_empty(), "the clinic has a service market row");
    for row in markets {
        assert_eq!(row.next_price, dollars(2));
    }
}

#[test]
fn a_provider_funded_by_a_grant_keeps_its_price() {
    let closed = close_first_period(&Clinic {
        price: dollars(1),
        pricing: range(dollars(2)),
        grant: true,
    })
    .expect("the period closes");
    assert_eq!(offer_price(&closed), dollars(1));
    assert_eq!(raises(&closed), vec![]);
}

#[test]
fn a_resting_price_under_its_ceiling_is_raised_to_cost_as_before() {
    let closed = close_first_period(&Clinic {
        price: dollars(1),
        pricing: range(dollars(1_000)),
        grant: false,
    })
    .expect("the period closes");
    let raised = raises(&closed);
    assert_eq!(raised.len(), 1);
    let (old, cost) = raised[0];
    assert_eq!(old, dollars(1));
    assert!(cost > dollars(2) && cost < dollars(1_000), "cost {cost:?}");
    assert_eq!(offer_price(&closed), cost);
    let site = clinic();
    let markets: Vec<_> = closed
        .service_markets
        .iter()
        .filter(|r| r.site_id == site)
        .collect();
    assert!(!markets.is_empty(), "the clinic has a service market row");
    for row in markets {
        assert_eq!(row.next_price, cost);
    }
}
