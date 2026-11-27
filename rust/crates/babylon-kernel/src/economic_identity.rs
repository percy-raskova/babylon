//! Source-axis identities for the Designed national QCEW function mapping.
//! These classifications establish neither physical recipes nor class positions.

/// Technical function in `NationalQcewFunctionMappingV1` and `NationalQcewFunctionMappingV2`, ordered by source key.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum EconomicFunction {
    /// Mixed information, financial, professional and support activities.
    BusinessServices,
    /// Machinery and equipment proxy. Under twelve trades, consumer uses sit in `ConsumerGoods`.
    CapitalGoods,
    /// Construction and real-estate activities, not measured dwelling stock.
    ConstructionHousing,
    /// Consumer manufacturing, present only in the twelve-trade list.
    ConsumerGoods,
    /// Wholesale, retail and transportation/storage activities.
    DistributionTransport,
    /// Utilities and petroleum/coal products activities.
    EnergyUtilities,
    /// Forestry and mining activities, not measured resource stocks.
    Extraction,
    /// Agriculture, fishing and food/beverage activities.
    Food,
    /// Broad education, health and other service activities.
    HouseholdServices,
    /// Accommodation, food service, arts and recreation, present only in the twelve-trade list.
    LeisureHospitality,
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
            "consumer_goods" => Some(Self::ConsumerGoods),
            "distribution_transport" => Some(Self::DistributionTransport),
            "energy_utilities" => Some(Self::EnergyUtilities),
            "extraction" => Some(Self::Extraction),
            "food" => Some(Self::Food),
            "household_services" => Some(Self::HouseholdServices),
            "leisure_hospitality" => Some(Self::LeisureHospitality),
            "manufacturing" => Some(Self::Manufacturing),
            "public_provisioning" => Some(Self::PublicProvisioning),
            _ => None,
        }
    }
    /// Readable name from the captured `NationalQcewFunctionMappingV1` contract.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::BusinessServices => "Business services",
            Self::CapitalGoods => "Capital goods",
            Self::ConstructionHousing => "Construction/housing",
            Self::ConsumerGoods => "Consumer goods",
            Self::DistributionTransport => "Distribution/transport",
            Self::EnergyUtilities => "Energy/utilities",
            Self::Extraction => "Extraction",
            Self::Food => "Food",
            Self::HouseholdServices => "Household services",
            Self::LeisureHospitality => "Leisure and hospitality",
            Self::Manufacturing => "Manufacturing",
            Self::PublicProvisioning => "Public provisioning",
        }
    }

    /// Exact source mapping key, not a claim about product end-use.
    #[must_use]
    pub const fn source_key(self) -> &'static str {
        match self {
            Self::BusinessServices => "business_services",
            Self::CapitalGoods => "capital_goods",
            Self::ConstructionHousing => "construction_housing",
            Self::ConsumerGoods => "consumer_goods",
            Self::DistributionTransport => "distribution_transport",
            Self::EnergyUtilities => "energy_utilities",
            Self::Extraction => "extraction",
            Self::Food => "food",
            Self::HouseholdServices => "household_services",
            Self::LeisureHospitality => "leisure_hospitality",
            Self::Manufacturing => "manufacturing",
            Self::PublicProvisioning => "public_provisioning",
        }
    }
}

const TEN: [EconomicFunction; 10] = [
    EconomicFunction::BusinessServices,
    EconomicFunction::CapitalGoods,
    EconomicFunction::ConstructionHousing,
    EconomicFunction::DistributionTransport,
    EconomicFunction::EnergyUtilities,
    EconomicFunction::Extraction,
    EconomicFunction::Food,
    EconomicFunction::HouseholdServices,
    EconomicFunction::Manufacturing,
    EconomicFunction::PublicProvisioning,
];

const TWELVE: [EconomicFunction; 12] = [
    EconomicFunction::BusinessServices,
    EconomicFunction::CapitalGoods,
    EconomicFunction::ConstructionHousing,
    EconomicFunction::ConsumerGoods,
    EconomicFunction::DistributionTransport,
    EconomicFunction::EnergyUtilities,
    EconomicFunction::Extraction,
    EconomicFunction::Food,
    EconomicFunction::HouseholdServices,
    EconomicFunction::LeisureHospitality,
    EconomicFunction::Manufacturing,
    EconomicFunction::PublicProvisioning,
];

/// Which list of trades a scenario uses. Ten for schema 7 and earlier, twelve for schema 8.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum TradeSet {
    /// Today's ten trades.
    Ten,
    /// The ten plus consumer goods and leisure and hospitality.
    Twelve,
}

impl TradeSet {
    /// The set's trades in `Ord` order. `Ten` is exactly the opening's trade list of schema 7.
    #[must_use]
    pub const fn functions(self) -> &'static [EconomicFunction] {
        match self {
            Self::Ten => &TEN,
            Self::Twelve => &TWELVE,
        }
    }

    /// Whether the set names this trade.
    #[must_use]
    pub fn contains(self, function: EconomicFunction) -> bool {
        self.functions().contains(&function)
    }

    /// `EconomicFunction::from_source_key`, then `None` for a trade outside the set.
    #[must_use]
    pub fn from_source_key(self, key: &str) -> Option<EconomicFunction> {
        EconomicFunction::from_source_key(key).filter(|function| self.contains(*function))
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

#[cfg(test)]
mod tests {
    use super::{EconomicFunction, TradeSet};

    const TWELVE_KEYS: [&str; 12] = [
        "business_services",
        "capital_goods",
        "construction_housing",
        "consumer_goods",
        "distribution_transport",
        "energy_utilities",
        "extraction",
        "food",
        "household_services",
        "leisure_hospitality",
        "manufacturing",
        "public_provisioning",
    ];

    #[test]
    fn twelve_trades_sort_where_the_builders_sort_them() {
        let functions = TradeSet::Twelve.functions();
        assert_eq!(functions.len(), 12);
        let keys: Vec<&str> = functions.iter().map(|f| f.source_key()).collect();
        assert_eq!(keys, TWELVE_KEYS);
        assert!(keys.windows(2).all(|pair| pair[0] < pair[1]));
        assert!(functions.windows(2).all(|pair| pair[0] < pair[1]));
    }

    #[test]
    fn ten_trades_keep_their_order() {
        use EconomicFunction::*;
        let today = [
            BusinessServices,
            CapitalGoods,
            ConstructionHousing,
            DistributionTransport,
            EnergyUtilities,
            Extraction,
            Food,
            HouseholdServices,
            Manufacturing,
            PublicProvisioning,
        ];
        assert_eq!(TradeSet::Ten.functions(), today);
        assert!(TradeSet::Ten.functions().windows(2).all(|p| p[0] < p[1]));
        assert!(!TradeSet::Ten.contains(ConsumerGoods));
        assert!(!TradeSet::Ten.contains(LeisureHospitality));
        assert!(TradeSet::Twelve.contains(ConsumerGoods));
        assert_eq!(TradeSet::Ten.from_source_key("consumer_goods"), None);
        assert_eq!(TradeSet::Ten.from_source_key("leisure_hospitality"), None);
        assert_eq!(
            TradeSet::Twelve.from_source_key("consumer_goods"),
            Some(ConsumerGoods)
        );
        assert_eq!(TradeSet::Ten.from_source_key("food"), Some(Food));
    }

    #[test]
    fn new_trades_have_their_labels() {
        let consumer = EconomicFunction::ConsumerGoods;
        assert_eq!(consumer.label(), "Consumer goods");
        assert_eq!(consumer.source_key(), "consumer_goods");
        let leisure = EconomicFunction::LeisureHospitality;
        assert_eq!(leisure.label(), "Leisure and hospitality");
        assert_eq!(leisure.source_key(), "leisure_hospitality");
        assert_eq!(
            EconomicFunction::from_source_key("leisure_hospitality"),
            Some(leisure)
        );
    }
}
