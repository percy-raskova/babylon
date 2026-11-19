use crate::{
    FinalDemandPrincipalId, HouseholdLifecycleBook, HouseholdLifecycleRates, ResidentAges,
};
#[test]
fn whole_people_and_carried_fraction_have_distinct_openings() {
    let h = FinalDemandPrincipalId::from_bytes([1; 32]);
    let rates = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: 500_000,
        deaths_per_million_per_period: [0; 4],
    };
    let opening = ResidentAges {
        age_18_64: 1,
        ..ResidentAges::default()
    };
    let mut book =
        HouseholdLifecycleBook::new(rates, vec![(h, opening)]).expect("captured resident exposure");
    let first = book.positions[0]
        .next(rates, 1, 1)
        .expect("valid four-week population close");
    assert_eq!(
        (first.opening, first.births, first.closing),
        (opening, 0, opening)
    );
    let second = book.positions[0]
        .next(rates, 2, 1)
        .expect("valid four-week population close");
    assert_eq!(
        (second.births, second.reached_16, second.closing.under_16),
        (1, 0, 1)
    );
    second.validate().expect("age flows reconcile");
}
#[test]
fn known_birth_crosses_sixteen_eighteen_and_sixty_five_after_exact_elapsed_periods() {
    let principal = FinalDemandPrincipalId::from_bytes([2; 32]);
    let birth = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: 1_000_000,
        deaths_per_million_per_period: [0; 4],
    };
    let mut book = HouseholdLifecycleBook::new(
        birth,
        vec![(
            principal,
            ResidentAges {
                age_18_64: 1,
                ..ResidentAges::default()
            },
        )],
    )
    .expect("valid captured age exposure");
    let p = &mut book.positions[0];
    p.next(birth, 1, 1)
        .expect("valid four-week population close");
    let no_birth = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: 0,
        ..birth
    };
    let parent_exit = HouseholdLifecycleRates {
        deaths_per_million_per_period: [0, 0, 1_000_000, 0],
        ..no_birth
    };
    let sole_child = p
        .next(parent_exit, 2, 1)
        .expect("valid four-week population close");
    assert_eq!(
        sole_child.closing.persons().expect("resident count fits"),
        1
    );
    for n in 3..=208 {
        let r = p
            .next(no_birth, n, 1)
            .expect("valid four-week population close");
        assert_eq!(r.closing.under_16, 1);
        assert_eq!(r.reached_16, 0);
    }
    let r = p
        .next(no_birth, 209, 1)
        .expect("valid four-week population close");
    assert_eq!(r.reached_16, 1);
    assert_eq!(r.closing.age_16_17, 1);
    for n in 210..235 {
        assert_eq!(
            p.next(no_birth, n, 1)
                .expect("valid four-week population close")
                .reached_18,
            0
        );
    }
    assert_eq!(
        p.next(no_birth, 235, 1)
            .expect("valid four-week population close")
            .reached_18,
        1
    );
    for n in 236..846 {
        let r = p
            .next(no_birth, n, 1)
            .expect("valid four-week population close");
        assert_eq!(
            (r.reached_65, r.closing.age_18_64, r.closing.age_65_plus),
            (0, 1, 0),
            "P{n}"
        );
    }
    let senior = p
        .next(no_birth, 846, 1)
        .expect("valid four-week population close");
    assert_eq!((senior.reached_65, senior.closing.age_65_plus), (1, 1));
    assert_eq!(p.birthdays, []);
}
#[test]
fn ending_a_household_exhausts_actual_members_and_an_elder_can_still_work() {
    use crate::{StaffingMemberBinding, StaffingMemberId, StaffingMemberState, StaffingPoolId};
    let principal = FinalDemandPrincipalId::from_bytes([2; 32]);
    let mut book = HouseholdLifecycleBook::new(
        HouseholdLifecycleRates {
            births_per_million_working_age_per_period: 0,
            deaths_per_million_per_period: [0, 0, 0, 1_000_000],
        },
        vec![(
            principal,
            ResidentAges {
                age_65_plus: 1,
                ..ResidentAges::default()
            },
        )],
    )
    .expect("valid captured age exposure");
    let binding = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes([3; 32]),
        principal,
        "county:26163".parse().expect("valid Wayne county key"),
        1,
    )
    .expect("valid captured age exposure");
    let pool = StaffingPoolId::from_bytes([4; 32]);
    let live = StaffingMemberState::try_new(binding.clone(), 1, 0).expect("one employed resident");
    let no_death = HouseholdLifecycleRates {
        deaths_per_million_per_period: [0; 4],
        ..book.rates
    };
    let r = book.positions[0]
        .next(no_death, 1, 1)
        .expect("valid four-week population close");
    assert_eq!(
        crate::reconcile_resident_workforce(&[r], &[(pool, live.clone())])
            .expect("receipted force fits its opening residents"),
        []
    );
    let r = book.positions[0]
        .next(book.rates, 2, 1)
        .expect("valid four-week population close");
    assert_eq!(r.closing_households, 0);
    assert_eq!(r.closing.eligible().expect("living eligible count fits"), 0);
    let loss = crate::reconcile_resident_workforce(&[r], &[(pool, live)])
        .expect("receipted force fits its opening residents");
    assert_eq!((loss[0].employed_removed, loss[0].reserve_removed), (1, 0));
    assert!(StaffingMemberState::try_new(
        binding
            .with_living_force(0)
            .expect("remaining force may reach zero"),
        0,
        0
    )
    .is_ok());
}

#[test]
fn incoming_residents_do_not_age_twice_and_collective_residences_gain_no_households() {
    let id = FinalDemandPrincipalId::from_bytes([5; 32]);
    let rates = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: 0,
        deaths_per_million_per_period: [0; 4],
    };
    let mut b = HouseholdLifecycleBook::new(
        rates,
        vec![(
            id,
            ResidentAges {
                under_16: 208,
                ..ResidentAges::default()
            },
        )],
    )
    .expect("valid captured age exposure");
    let r = b.positions[0]
        .next(rates, 1, 0)
        .expect("valid four-week population close");
    assert_eq!(
        (
            r.reached_16,
            r.reached_18,
            r.closing.age_16_17,
            r.closing.age_18_64,
            r.closing_households
        ),
        (1, 0, 1, 0, 0)
    );
}

#[test]
fn deaths_remove_only_living_birth_cohorts_and_leave_no_phantom_birthday() {
    let id = FinalDemandPrincipalId::from_bytes([6; 32]);
    let rates = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: 1_000_000,
        deaths_per_million_per_period: [0; 4],
    };
    let mut b = HouseholdLifecycleBook::new(
        rates,
        vec![(
            id,
            ResidentAges {
                age_18_64: 1,
                ..ResidentAges::default()
            },
        )],
    )
    .expect("valid captured age exposure");
    let p = &mut b.positions[0];
    p.next(rates, 1, 1)
        .expect("valid four-week population close");
    let mortality = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: 0,
        deaths_per_million_per_period: [1_000_000, 0, 1_000_000, 0],
    };
    let loss = p
        .next(mortality, 2, 1)
        .expect("valid four-week population close");
    assert_eq!(loss.deaths.under_16, 1);
    assert_eq!(loss.deaths.age_18_64, 1);
    assert_eq!(loss.closing.persons().expect("resident count fits"), 0);
    assert_eq!(p.birthdays, []);
    for n in 3..=235 {
        let row = p
            .next(rates, n, 0)
            .expect("valid four-week population close");
        assert_eq!(row.births, 0);
        assert_eq!(row.reached_16, 0);
        assert_eq!(row.closing.persons().expect("resident count fits"), 0);
    }
}

#[test]
fn all_surviving_openers_cross_each_birthday_within_their_original_age_span() {
    let rate = HouseholdLifecycleRates {
        births_per_million_working_age_per_period: 0,
        deaths_per_million_per_period: [0; 4],
    };
    let principal = FinalDemandPrincipalId::from_bytes([7; 32]);
    for band in 0..3 {
        let mut ages = [0; 4];
        ages[band] = 1_000_000;
        let mut book =
            HouseholdLifecycleBook::new(rate, vec![(principal, ResidentAges::from_array(ages))])
                .expect("captured resident exposure");
        let mut crossings = vec![[0_u64; 3]; 846];
        for tick in 1..=845 {
            let row = book.positions[0]
                .next(rate, tick as u64, 1)
                .expect("valid four-week population close");
            row.validate().expect("age flows reconcile");
            crossings[tick] = [row.reached_16, row.reached_18, row.reached_65];
            assert_eq!(
                row.closing.persons().expect("resident count fits"),
                1_000_000
            );
            if tick >= [208, 26, 611][band] {
                assert_eq!(
                    row.closing.array()[band],
                    0,
                    "original band {band} at P{tick}"
                );
            }
            if band == 0 {
                assert_eq!(
                    row.reached_18,
                    tick.checked_sub(26).map_or(0, |p| crossings[p][0])
                );
            }
            if band <= 1 {
                assert_eq!(
                    row.reached_65,
                    tick.checked_sub(611).map_or(0, |p| crossings[p][1])
                );
            }
        }
        assert_eq!(book.positions[0].ages.age_65_plus, 1_000_000);
    }
}
