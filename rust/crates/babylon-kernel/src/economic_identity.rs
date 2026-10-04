//! Source-axis identities for the Designed national QCEW function mapping.
//! These classifications establish neither physical recipes nor class positions.

/// Technical function in `NationalQcewFunctionMappingV1`, ordered by source key.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum EconomicFunction {
    /// Mixed information, financial, professional and support activities.
    BusinessServices,
    /// Machinery and equipment proxy with mixed consumer and capital uses.
    CapitalGoods,
    /// Construction and real-estate activities, not measured dwelling stock.
    ConstructionHousing,
    /// Wholesale, retail and transportation/storage activities.
    DistributionTransport,
    /// Utilities and petroleum/coal products activities.
    EnergyUtilities,
    /// Forestry and mining activities, not measured resource stocks.
    Extraction,
    /// Agriculture, fishing and food/beverage activities.
    Food,
    /// Broad education, health, recreation and other service activities.
    HouseholdServices,
    /// Mixed intermediate, consumer and capital manufacturing activities.
    Manufacturing,
    /// Public administration, distinct from all public ownership.
    PublicProvisioning,
}
impl EconomicFunction {
    /// Exact case-sensitive mapping key; no default or unclassified function.
    #[must_use]
    pub fn from_source_key(value: &str) -> Option<Self> {
        match value {
            "business_services" => Some(Self::BusinessServices),
            "capital_goods" => Some(Self::CapitalGoods),
            "construction_housing" => Some(Self::ConstructionHousing),
            "distribution_transport" => Some(Self::DistributionTransport),
            "energy_utilities" => Some(Self::EnergyUtilities),
            "extraction" => Some(Self::Extraction),
            "food" => Some(Self::Food),
            "household_services" => Some(Self::HouseholdServices),
            "manufacturing" => Some(Self::Manufacturing),
            "public_provisioning" => Some(Self::PublicProvisioning),
            _ => None,
        }
    }
    /// Exact source mapping key, not a claim about product end-use.
    #[must_use]
    pub const fn source_key(self) -> &'static str {
        match self {
            Self::BusinessServices => "business_services",
            Self::CapitalGoods => "capital_goods",
            Self::ConstructionHousing => "construction_housing",
            Self::DistributionTransport => "distribution_transport",
            Self::EnergyUtilities => "energy_utilities",
            Self::Extraction => "extraction",
            Self::Food => "food",
            Self::HouseholdServices => "household_services",
            Self::Manufacturing => "manufacturing",
            Self::PublicProvisioning => "public_provisioning",
        }
    }
}

/// QCEW source ownership axis, independent of technical function.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum QcewOwnership {
    /// Source ownership code 1.
    FederalGovernment,
    /// Source ownership code 2.
    StateGovernment,
    /// Source ownership code 3.
    LocalGovernment,
    /// Source ownership code 5.
    Private,
}
impl QcewOwnership {
    /// Exact disjoint ownership code; aggregate ownership controls are refused.
    #[must_use]
    pub fn from_source_code(value: &str) -> Option<Self> {
        match value {
            "1" => Some(Self::FederalGovernment),
            "2" => Some(Self::StateGovernment),
            "3" => Some(Self::LocalGovernment),
            "5" => Some(Self::Private),
            _ => None,
        }
    }
    /// Original source code, preserving the independent ownership axis.
    #[must_use]
    pub const fn source_code(self) -> &'static str {
        match self {
            Self::FederalGovernment => "1",
            Self::StateGovernment => "2",
            Self::LocalGovernment => "3",
            Self::Private => "5",
        }
    }
}
