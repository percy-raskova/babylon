//! Stable company carrier and the integer fields shared by national graph seeding and the native bridge.
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_material_circuit::CompanyId;

pub const EVIDENCE_RULE: &str = "company/portfolio-evidence";
pub const DEFER_WEIGHT: &str = "company/defer-weight";
pub const REPLACEMENT_WEIGHT: &str = "company/replacement-weight";
pub const MODEST_WEIGHT: &str = "company/modest-weight";
pub const LARGER_WEIGHT: &str = "company/larger-weight";
pub const EVIDENCE_PERIOD: &str = "company/evidence-period";
pub const SELECTED_PORTFOLIO: &str = "company/selected-portfolio";
pub const SELECTION_PERIOD: &str = "company/selection-period";
pub const FIELDS: [&str; 7] = [
    DEFER_WEIGHT,
    REPLACEMENT_WEIGHT,
    MODEST_WEIGHT,
    LARGER_WEIGHT,
    EVIDENCE_PERIOD,
    SELECTED_PORTFOLIO,
    SELECTION_PERIOD,
];

#[must_use]
pub fn company_key(scope: &str, company: CompanyId) -> StableElementKey {
    StableElementKey::Node {
        scenario: scope.to_owned(),
        local_name: format!("company-{}", content_digest::base32(&company.as_bytes())),
    }
}

#[cfg(test)]
#[test]
fn company_carriers_fit_graph_symbols_and_preserve_the_full_digest() {
    let scope = "economy/national-world";
    let first = company_key(scope, CompanyId::from_bytes([0; 32]));
    let mut last_bit = [0u8; 32];
    last_bit[31] = 1;
    let second = company_key(scope, CompanyId::from_bytes(last_bit));
    let all_ones = company_key(scope, CompanyId::from_bytes([255; 32]));
    for key in [&first, &second, &all_ones] {
        let bytes = key.canonical_bytes().expect("valid graph seed symbol");
        assert_eq!(
            StableElementKey::from_canonical_bytes(&bytes).as_ref(),
            Ok(key)
        );
    }
    let StableElementKey::Node { local_name, .. } = second else {
        unreachable!()
    };
    assert_eq!(local_name, format!("company-{}q", "a".repeat(51)));
    assert_ne!(first, all_ones);
}
