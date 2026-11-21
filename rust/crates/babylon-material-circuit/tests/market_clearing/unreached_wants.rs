//! A want its money cannot reach is no unmet need: it is kept out of every reader of one.

use super::service_support::{self, ServiceFixture, LOCAL, UTILITY};
use super::support::{self, Fixture, Shelf};
use babylon_material_circuit::{HouseholdStandard, MaterialCircuitTransition, WantTier};

fn goods_close(fixture: &Fixture) -> MaterialCircuitTransition {
    let (catalog, state) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes")
}

fn services_close(fixture: &ServiceFixture) -> MaterialCircuitTransition {
    let (catalog, state) = fixture.build();
    babylon_material_circuit::advance_material_circuit(&catalog, &state)
        .expect("the fixture period closes")
}

/// Every account holds exactly what its need of good 2 costs ($4 a unit, 100 units).
fn goods_fixture(wanting: bool) -> Fixture {
    let mut fixture = Fixture::new(
        1_000,
        &[
            support::dollars(400),
            support::dollars(400),
            support::dollars(400),
        ],
    );
    fixture.shelves.push(Shelf {
        good: 3,
        price: support::dollars(10),
        stock: 1_000,
        needed: false,
    });
    fixture.paying_order = Some(vec![2, 3]);
    if wanting {
        for account in 0..3 {
            fixture
                .household_wants
                .push((account, WantTier::Comfort, 3, 50));
            fixture
                .household_wants
                .push((account, WantTier::Luxury, 2, 50));
        }
    }
    fixture
}

/// Every account holds exactly what its local need costs ($3 a unit, 100 units).
fn services_fixture(wanting: bool) -> ServiceFixture {
    let mut fixture = ServiceFixture::new(
        &[support::dollars(300), support::dollars(300)],
        &[vec![(LOCAL, 100)], vec![(LOCAL, 100)]],
    );
    if wanting {
        for account in 0..2 {
            fixture
                .household_wants
                .push((account, WantTier::Comfort, UTILITY, 100));
            fixture
                .household_wants
                .push((account, WantTier::Luxury, LOCAL, 100));
        }
    }
    fixture
}

fn assert_no_unmet_need(closed: &MaterialCircuitTransition) {
    assert!(closed
        .household_consumption
        .iter()
        .all(|row| row.unmet_quantity == 0));
    assert!(closed
        .household_services
        .iter()
        .all(|row| row.unmet_quantity == 0));
}

#[test]
fn an_unreached_want_is_not_going_without() {
    let goods = goods_close(&goods_fixture(true));
    let goods_plain = goods_close(&goods_fixture(false));
    let services = services_close(&services_fixture(true));
    let services_plain = services_close(&services_fixture(false));
    for (closed, plain, accounts) in [(&goods, &goods_plain, 3), (&services, &services_plain, 2)] {
        assert_eq!(closed.household_consumption, plain.household_consumption);
        assert_eq!(closed.household_services, plain.household_services);
        assert_eq!(closed.household_demand, plain.household_demand);
        assert_no_unmet_need(closed);
        assert!(!closed.household_wants.is_empty(), "the wants were written");
        assert!(closed
            .household_wants
            .iter()
            .all(|row| row.bought_quantity == 0 && row.wanted_quantity > 0));
        for index in 0..accounts {
            let standard = babylon_material_circuit::household_standard(
                service_support::account(index),
                &closed.household_consumption,
                &closed.household_services,
                &closed.household_tiers,
            )
            .expect("the account's tiers are recorded");
            assert_eq!(standard, HouseholdStandard::GettingBy);
        }
    }
}
