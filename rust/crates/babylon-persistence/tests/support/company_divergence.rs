//! Positive support and the same raw observations are required to attribute a choice difference to the seed.
use babylon_material_circuit::{CompanyId, CompanyPortfolioEvidence, CompanyPortfolioRegister};
use serde_json::{json, Value};
use std::collections::BTreeMap;

pub(super) struct Samples(Vec<(CompanyPortfolioEvidence, usize)>);
impl Samples {
    pub(super) fn new(
        register: &CompanyPortfolioRegister,
        selected: &BTreeMap<CompanyId, usize>,
    ) -> Self {
        Self(
            register
                .companies
                .iter()
                .map(|r| (r.clone(), selected[&r.company]))
                .collect(),
        )
    }
}

#[derive(Default)]
struct Comparison {
    changed_evidence: u64,
    single_feasible: u64,
    single_supported: u64,
    comparable_alternatives: u64,
    demonstrated: u64,
    first_witness: Option<Value>,
}

impl Comparison {
    fn compare(
        &mut self,
        left: &(CompanyPortfolioEvidence, usize),
        right: &(CompanyPortfolioEvidence, usize),
    ) {
        let (a, i) = left;
        let (b, j) = right;
        assert_eq!(
            (a.company, a.period),
            (b.company, b.period),
            "identical captured controller and observation period"
        );
        assert!(a.feasible[*i] && a.weights[*i] > 0 && b.feasible[*j] && b.weights[*j] > 0);
        if a != b {
            self.changed_evidence += 1;
            return;
        }
        if a.feasible.iter().filter(|&&f| f).count() == 1 {
            assert_eq!(i, j);
            self.single_feasible += 1;
        } else if a.weights.iter().filter(|&&n| n > 0).count() == 1 {
            assert_eq!(i, j);
            self.single_supported += 1;
        } else {
            self.comparable_alternatives += 1;
            if i != j {
                self.demonstrated += 1;
                self.first_witness.get_or_insert_with(||json!({"company":babylon_tick::hex(&a.company.as_bytes()),"evidence_period":a.period,
                    "original_weights":a.original_weights,"feasible":a.feasible,"positive_eligible_weights":a.weights,
                    "first_choice":i,"second_choice":j}));
            }
        }
    }
    fn status(&self) -> &'static str {
        if self.demonstrated > 0 {
            "divergence_demonstrated"
        } else if self.comparable_alternatives > 0 {
            "multiple_supported_same_choices_for_these_seeds"
        } else if self.single_supported > 0 {
            "one_positive_weight_for_each_comparable_decision"
        } else if self.single_feasible > 0 {
            "one_feasible_branch_for_each_comparable_decision"
        } else {
            "no_identical_decision_evidence"
        }
    }
}

pub(super) fn report(first: &[Samples], second: &[Samples], count: usize, condition: &str) {
    assert!(!first.is_empty());
    assert_eq!(first.len(), second.len());
    let mut comparison = Comparison::default();
    for (a, b) in first.iter().zip(second) {
        assert_eq!(a.0.len(), count);
        assert_eq!(b.0.len(), count);
        for (left, right) in a.0.iter().zip(&b.0) {
            comparison.compare(left, right);
        }
    }
    println!(
        "{}",
        json!({"experiment":"national_company_choice_divergence","controllers":count,"opening_treatment":condition,
        "seeds":[37,319],"status":comparison.status(),"identical_evidence_multiple_positive_choices":comparison.comparable_alternatives,
        "different_selections_with_identical_raw_evidence":comparison.demonstrated,"changed_evidence_excluded":comparison.changed_evidence,
        "single_feasible_branch":comparison.single_feasible,"multiple_feasible_single_positive_weight":comparison.single_supported,
        "first_verified_difference":comparison.first_witness})
    );
}

#[test]
fn stochastic_difference_requires_equal_raw_evidence_and_two_supported_branches() {
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::CompanyCondition;
    let mut row = CompanyPortfolioEvidence {
        company: CompanyId::from_bytes([1; 32]),
        period: 1,
        history: vec![Currency::from_micro_units(5)],
        treasury_available: Currency::from_micro_units(100),
        processes: vec![],
        original_weights: [70, 30, 0, 0],
        weights: [70, 30, 0, 0],
        feasible: [true, true, false, false],
        condition: CompanyCondition::Loss,
        plans: Default::default(),
    };
    let mut comparison = Comparison::default();
    let first = (row.clone(), 0);
    let same = (row.clone(), 0);
    comparison.compare(&first, &same);
    assert_eq!(
        comparison.status(),
        "multiple_supported_same_choices_for_these_seeds"
    );
    row.treasury_available = Currency::from_micro_units(101);
    comparison.compare(&first, &(row.clone(), 1));
    assert_eq!(comparison.changed_evidence, 1);
    assert_eq!(comparison.demonstrated, 0);
    comparison.compare(&(row.clone(), 0), &(row.clone(), 1));
    assert_eq!(comparison.status(), "divergence_demonstrated");
    let mut single = Comparison::default();
    row.weights = [70, 0, 0, 0];
    row.feasible = [true, false, false, false];
    single.compare(&(row.clone(), 0), &(row, 0));
    assert_eq!(
        single.status(),
        "one_feasible_branch_for_each_comparable_decision"
    );
}
