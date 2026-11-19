use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{Apportionment, CountyReviewError, Ties};

#[test]
fn equal_remainders_at_the_cut_are_withheld_or_go_in_order() {
    assert_eq!(
        practice_contract::apportion(5, &[2, 2, 2], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![1, 1, 1],
            withheld: 2
        },
        "three equal remainders share two units: none of them gets one"
    );
    assert_eq!(
        practice_contract::apportion(5, &[2, 2, 2], Ties::InOrder).expect("splits"),
        Apportionment {
            shares: vec![2, 2, 1],
            withheld: 0
        },
        "the earlier parts take the two units"
    );
    assert_eq!(
        practice_contract::apportion(3, &[1, 2, 3], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![0, 1, 1],
            withheld: 1
        },
        "the first and third remainders tie for one unit"
    );
    assert_eq!(
        practice_contract::apportion(3, &[1, 2, 3], Ties::InOrder).expect("splits"),
        Apportionment {
            shares: vec![1, 1, 1],
            withheld: 0
        },
        "the earlier of the tied parts takes it"
    );
}

#[test]
fn a_split_with_no_tie_adds_back_exactly() {
    assert_eq!(
        practice_contract::apportion(7, &[10, 20, 30], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![1, 2, 4],
            withheld: 0
        }
    );
    assert_eq!(
        practice_contract::apportion(0, &[0, 0], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![0, 0],
            withheld: 0
        },
        "nothing to split over nothing"
    );
    assert_eq!(
        practice_contract::apportion(4, &[1, 2], Ties::InOrder),
        Err(CountyReviewError::SplitExceedsWeights)
    );
}

#[test]
fn a_tie_below_the_cut_does_not_stop_the_larger_remainders() {
    // 10 over [3, 3, 4]: floors 3, 3, 4 add to 10 exactly, nothing left over.
    assert_eq!(
        practice_contract::apportion(10, &[3, 3, 4], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![3, 3, 4],
            withheld: 0
        }
    );
    // 4 over [1, 1, 3, 3] (sum 8): floors 0, 0, 1, 1 and remainders 4, 4, 4, 4 of 8: 2 left, all tied.
    assert_eq!(
        practice_contract::apportion(4, &[1, 1, 3, 3], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![0, 0, 1, 1],
            withheld: 2
        }
    );
    // 5 over [1, 1, 1, 5] (sum 8): floors 0, 0, 0, 3; remainders 5, 5, 5, 1 of 8; 2 left over from three
    // equal remainders, so the whole run is withheld.
    assert_eq!(
        practice_contract::apportion(5, &[1, 1, 1, 5], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![0, 0, 0, 3],
            withheld: 2
        }
    );
    // 7 over [1, 1, 1, 6] (sum 9): floors 0, 0, 0, 4; remainders 7, 7, 7, 6 of 9; three left over and
    // all three tied ones fit, so they are given and the smaller remainder is not.
    assert_eq!(
        practice_contract::apportion(7, &[1, 1, 1, 6], Ties::Withhold).expect("splits"),
        Apportionment {
            shares: vec![1, 1, 1, 4],
            withheld: 0
        }
    );
}

#[test]
fn ratio_split_gives_the_odd_household_to_the_larger_remainder() {
    assert_eq!(
        practice_contract::ratio_split(70_060, 1, 9).expect("splits"),
        (7_006, 63_054)
    );
    assert_eq!(
        practice_contract::ratio_split(630_523, 4, 5).expect("splits"),
        (280_232, 350_291)
    );
    assert_eq!(
        practice_contract::ratio_split(15, 1, 9).expect("splits"),
        (1, 14),
        "an exact tie goes to the lower part"
    );
    assert_eq!(
        practice_contract::ratio_split(4, 4, 5).expect("splits"),
        (2, 2)
    );
    assert_eq!(
        practice_contract::ratio_split(0, 0, 0).expect("splits"),
        (0, 0)
    );
    assert_eq!(
        practice_contract::ratio_split(3, 0, 0),
        Err(CountyReviewError::SplitExceedsWeights)
    );
}
