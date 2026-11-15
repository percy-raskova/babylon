use super::{CompanyPortfolioEvidence, CompanyPortfolioPolicy, CompanyProcessEvidence};
use crate::{CompanyId, ProcessId, SiteId};
use babylon_kernel::currency::Currency;
fn terms() -> CompanyPortfolioPolicy {
    CompanyPortfolioPolicy {
        rows: [
            [70, 30, 0, 0],
            [10, 70, 15, 5],
            [60, 25, 15, 0],
            [10, 10, 60, 20],
        ],
        high_utilization_bps: 8000,
        history_periods: 3,
        modest_expansion_bps: 5000,
    }
}
fn evidence() -> CompanyPortfolioEvidence {
    let micro = Currency::from_micro_units;
    CompanyPortfolioEvidence::from_close(
        CompanyId::from_bytes([1; 32]),
        1,
        vec![micro(4)],
        micro(12),
        vec![CompanyProcessEvidence {
            site: SiteId::from_bytes([2; 32]),
            process: ProcessId::from_bytes([3; 32]),
            produced_batches: 8,
            capacity_batches: 10,
            unmet_accepted_units: 1,
            used_service_batches: 8,
            replacement: 0,
            expansion: 4,
            unit_price: micro(3),
            free_cash: micro(0),
            earnings_budget: micro(12),
        }],
        &terms(),
    )
    .expect("funded high-demand alternatives")
}
#[test]
fn portfolios_remove_infeasible_mass_and_limit_real_committed_expansion() {
    let row = evidence();
    assert_eq!(row.original_weights, [10, 10, 60, 20]);
    assert_eq!(row.weights, [10, 0, 60, 20]);
    assert_eq!(row.plans[2][0].expansion, 2);
    assert_eq!(row.plans[2][0].funding, Currency::from_micro_units(6));
    assert_eq!(row.plans[3][0].expansion, 4);
    assert_eq!(row.plans[3][0].funding, Currency::from_micro_units(12));
}
