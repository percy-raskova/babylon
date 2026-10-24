//! Qualification uses the exact production national source roster.

use babylon_persistence::economic_catalog::EconomicCatalogInput;

pub fn input() -> EconomicCatalogInput {
    babylon_persistence::economic_catalog::national_catalog_input()
}
