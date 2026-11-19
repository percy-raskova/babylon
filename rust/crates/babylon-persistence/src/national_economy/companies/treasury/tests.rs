use super::claims;
use super::{opening, MemberFunding, OriginalClaim};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, CompanyId, FinalDemandPrincipalId, SiteId};

#[test]
fn sweep_keeps_the_operating_floor_and_fractional_micro_at_the_site() {
    let micros = Currency::from_micro_units;
    for (cash, floor, want) in [
        (129, 100, 2),
        (100, 100, 0),
        (99, 100, 0),
        (i128::MAX, 0, i128::MAX / 10),
    ] {
        assert_eq!(
            opening::sweep(micros(cash), micros(floor), 1000).expect("valid 10%"),
            micros(want)
        );
    }
}
#[test]
fn fractional_beneficiary_claims_keep_the_original_capital_and_denominators() {
    let id = CompanyId::from_bytes([45; 32]);
    let members = [(1_u8, 11_i128), (2, 5)].map(|(site, capital)| MemberFunding {
        site: SiteId::from_bytes([site; 32]),
        company: id,
        original_cash: Currency::from_micro_units(capital),
        cash_floor: Currency::from_micro_units(0),
        swept: Currency::from_micro_units(0),
        remaining_cash: Currency::from_micro_units(capital),
        original_capital: Currency::from_micro_units(capital),
        remaining_capital: Currency::from_micro_units(capital),
    });
    let owners =
        [3_u8, 4].map(|n| AccountId::Household(FinalDemandPrincipalId::from_bytes([n; 32])));
    let sources = [(0, 0, 1, 3), (0, 1, 2, 3), (1, 0, 1, 2), (1, 1, 1, 2)].map(
        |(site, owner, shares, total)| OriginalClaim {
            site: members[site].site,
            company: id,
            beneficiary: owners[owner],
            capital: members[site].original_capital,
            original_shares: shares,
            site_total_shares: total,
            original_carrying_value: Currency::from_micro_units(0),
        },
    );
    let (companies, claims) =
        claims::combine(&members, &sources).expect("exact capital entitlements");
    assert_eq!(companies[0].common_denominator, 6);
    assert_eq!(companies[0].total_weight, 96);
    assert_eq!(claims[0].beneficiary, owners[0]);
    assert_eq!(claims[0].weight, 37);
    assert_eq!(claims[1].weight, 59);
}
