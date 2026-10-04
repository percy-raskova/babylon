//! Compiled current state18 rows: fixed widths, bounds and typed identity fields.
use super::{IdentityKind as K, StorageError};
#[derive(Clone, Copy, Debug)]
pub(super) enum FieldKind {
    Identity(K),
    Account,
    EquipmentAsset,
}
use FieldKind::{Account, EquipmentAsset, Identity};
#[derive(Clone, Copy, Debug)]
pub(super) struct Field {
    pub offset: usize,
    pub kind: FieldKind,
}
#[derive(Clone, Copy, Debug)]
pub(super) struct Layout {
    pub width: usize,
    pub maximum: usize,
    pub fields: &'static [Field],
}
macro_rules! fixed {($id:expr,$width:expr,$maximum:expr,[$(($offset:expr,$kind:expr)),*]) => {($id,Layout{width:$width,maximum:$maximum,fields:&[$(Field{offset:$offset,kind:$kind}),*]})};}
const LAYOUTS: &[(u16, Layout)] = &[
    fixed!(
        2,
        64,
        65_536,
        [(0, Identity(K::Site)), (32, Identity(K::LogisticsNode))]
    ), // site_logistics_nodes
    fixed!(
        3,
        136,
        65_536,
        [
            (0, Identity(K::Process)),
            (32, Identity(K::Site)),
            (64, Identity(K::Good)),
            (96, Identity(K::Unit))
        ]
    ), // process_outputs
    fixed!(
        4,
        104,
        131_072,
        [
            (0, Identity(K::Process)),
            (32, Identity(K::Good)),
            (64, Identity(K::Unit))
        ]
    ), // input_coefficients
    fixed!(
        5,
        72,
        65_536,
        [(0, Identity(K::Process)), (32, Identity(K::Unit))]
    ), // labor_coefficients
    fixed!(
        7,
        161,
        262_144,
        [
            (0, Identity(K::Site)),
            (32, Identity(K::Site)),
            (64, Identity(K::Good)),
            (96, Identity(K::Unit)),
            (128, Identity(K::Route))
        ]
    ), // supplier_routes
    fixed!(
        8,
        104,
        65_536,
        [
            (0, Identity(K::Route)),
            (34, Identity(K::LogisticsNode)),
            (66, Identity(K::LogisticsNode))
        ]
    ), // route_stages
    fixed!(
        9,
        66,
        262_144,
        [(0, Identity(K::Route)), (34, Identity(K::Corridor))]
    ), // route_stage_capacities
    fixed!(
        10,
        104,
        131_072,
        [
            (0, Identity(K::Site)),
            (32, Identity(K::Good)),
            (64, Identity(K::Unit))
        ]
    ), // inventory
    fixed!(
        11,
        201,
        131_072,
        [
            (0, Identity(K::Order)),
            (33, Identity(K::Site)),
            (65, Identity(K::Site)),
            (97, Identity(K::Good)),
            (129, Identity(K::Unit))
        ]
    ), // orders
    fixed!(12, 40, 131_072, [(0, Identity(K::Order))]), // backlog
    fixed!(
        13,
        250,
        65_536,
        [
            (0, Identity(K::FreightLot)),
            (32, Identity(K::Order)),
            (64, Identity(K::Route)),
            (114, Identity(K::Site)),
            (146, Identity(K::Site)),
            (178, Identity(K::Good)),
            (210, Identity(K::Unit))
        ]
    ), // freight
    fixed!(14, 48, 65_536, [(0, Identity(K::Corridor))]), // corridor_capacities
    fixed!(
        15,
        80,
        65_536,
        [(0, Identity(K::Process)), (32, Identity(K::Site))]
    ), // capacities
    fixed!(
        16,
        80,
        65_536,
        [(0, Identity(K::Site)), (32, Identity(K::Unit))]
    ), // labor
    fixed!(
        17,
        80,
        65_536,
        [(0, Identity(K::Process)), (32, Identity(K::Site))]
    ), // production_commitments
    fixed!(
        18,
        103,
        65_536,
        [
            (0, Identity(K::Site)),
            (39, Identity(K::Corridor)),
            (71, Identity(K::Unit))
        ]
    ), // merchants
    fixed!(
        19,
        104,
        65_536,
        [
            (0, Identity(K::Site)),
            (32, Identity(K::Good)),
            (64, Identity(K::Unit))
        ]
    ), // handling_coefficients
    fixed!(20, 38, 65_536, [(0, Identity(K::FinalDemandPrincipal))]), // final_demand_principals
    fixed!(
        21,
        176,
        65_536,
        [
            (0, Identity(K::Order)),
            (32, Identity(K::Site)),
            (64, Identity(K::FinalDemandPrincipal)),
            (96, Identity(K::Good)),
            (128, Identity(K::Unit))
        ]
    ), // final_demand_orders
    fixed!(24, 49, 131_072, [(1, Account)]),            // cash.accounts
    fixed!(
        25,
        139,
        327_680,
        [(1, Identity(K::Order)), (34, Account), (67, Account)]
    ), // cash.purchases
    fixed!(
        26,
        131,
        65_536,
        [(0, Identity(K::Shift)), (33, Account), (66, Account)]
    ), // cash.shifts
    fixed!(
        27,
        145,
        131_072,
        [
            (0, Identity(K::StaffingMember)),
            (32, Identity(K::Site)),
            (64, Identity(K::Unit)),
            (96, Identity(K::FinalDemandPrincipal))
        ]
    ), // employment
    fixed!(28, 48, 131_072, [(0, Identity(K::StaffingMember))]), // member_labor
    fixed!(30, 49, 65_536, [(1, Identity(K::FinalDemandPrincipal))]), // recurring.households
    fixed!(
        31,
        104,
        65_536,
        [
            (0, Identity(K::FinalDemandPrincipal)),
            (32, Identity(K::Good)),
            (64, Identity(K::Unit))
        ]
    ), // recurring.household_stocks
    fixed!(
        32,
        105,
        131_072,
        [
            (0, Identity(K::FinalDemandPrincipal)),
            (32, Identity(K::Good)),
            (64, Identity(K::Unit))
        ]
    ), // recurring.household_needs
    fixed!(
        33,
        145,
        131_072,
        [
            (0, Identity(K::FinalDemandPrincipal)),
            (32, Identity(K::Site)),
            (64, Identity(K::Good)),
            (96, Identity(K::Unit))
        ]
    ), // recurring.household_purchases
    fixed!(
        35,
        160,
        262_144,
        [
            (0, Identity(K::Site)),
            (32, Identity(K::Site)),
            (64, Identity(K::Good)),
            (96, Identity(K::Unit))
        ]
    ), // recurring.replenishment
    fixed!(
        36,
        80,
        65_536,
        [(0, Identity(K::Process)), (32, Identity(K::Site))]
    ), // recurring.production
    fixed!(
        37,
        80,
        65_536,
        [(0, Identity(K::Site)), (32, Identity(K::Unit))]
    ), // recurring.attendance
    fixed!(
        38,
        160,
        65_536,
        [
            (0, Identity(K::Site)),
            (32, Identity(K::Site)),
            (64, Identity(K::Good)),
            (96, Identity(K::Unit))
        ]
    ), // recurring.service_inputs
    fixed!(39, 81, 131_072, [(1, Account)]),            // cost.accounts
    fixed!(
        40,
        113,
        196_608,
        [
            (1, Account),
            (33, Identity(K::Good)),
            (65, Identity(K::Unit))
        ]
    ), // cost.stocks
    fixed!(
        41,
        81,
        65_536,
        [(0, Identity(K::FreightLot)), (33, Account)]
    ), // cost.freight
    fixed!(42, 81, 131_072, [(1, Account), (33, Identity(K::Site))]), // cost.equity
    fixed!(
        43,
        81,
        131_072,
        [(1, EquipmentAsset), (33, Identity(K::Site))]
    ), // cost.equipment
    fixed!(44, 39, 65_536, [(1, Account)]),             // financial.locations
    fixed!(45, 73, 131_072, [(0, Identity(K::Site)), (33, Account)]), // financial.ownership
    fixed!(46, 66, 65_536, [(0, Identity(K::Site))]),   // financial.distributions
    fixed!(
        47,
        84,
        131_072,
        [(1, Account), (33, Identity(K::PublicAccount))]
    ), // financial.taxes
    fixed!(48, 64, 65_536, [(0, Identity(K::PublicAccount))]), // financial.public_budgets
    fixed!(
        49,
        86,
        65_536,
        [(0, Identity(K::PublicAccount)), (33, Account)]
    ), // financial.public_allocations
    fixed!(
        50,
        121,
        65_536,
        [
            (0, Identity(K::Contribution)),
            (41, Account),
            (73, Identity(K::Site))
        ]
    ), // financial.contributions
    fixed!(
        53,
        136,
        65_536,
        [
            (0, Identity(K::FinalDemandPrincipal)),
            (40, Identity(K::Unit))
        ]
    ), // household_time.receipts
    fixed!(54, 96, 65_536, [(40, Identity(K::FinalDemandPrincipal))]), // household_time.contributions
    fixed!(
        57,
        152,
        65_536,
        [
            (0, Identity(K::EquipmentDefinition)),
            (32, Identity(K::Good)),
            (64, Identity(K::Unit)),
            (112, Identity(K::Unit))
        ]
    ), // equipment.definitions
    fixed!(
        58,
        96,
        65_536,
        [
            (0, Identity(K::Process)),
            (32, Identity(K::Site)),
            (64, Identity(K::EquipmentDefinition))
        ]
    ), // equipment.bindings
    fixed!(
        59,
        104,
        65_536,
        [
            (0, Identity(K::EquipmentDefinition)),
            (32, Identity(K::Good)),
            (64, Identity(K::Unit))
        ]
    ), // equipment.installation_inputs
    fixed!(
        60,
        88,
        65_536,
        [
            (0, Identity(K::EquipmentCohort)),
            (32, Identity(K::Process))
        ]
    ), // equipment.cohorts
    fixed!(
        61,
        88,
        65_536,
        [(0, Identity(K::Installation)), (32, Identity(K::Process))]
    ), // equipment.pending
    fixed!(62, 57, 65_536, [(0, Identity(K::Process))]), // equipment.installation_policies
    fixed!(
        63,
        106,
        65_536,
        [(0, Identity(K::Process)), (32, Identity(K::Site))]
    ), // equipment.investment_policies
    fixed!(64, 40, 65_536, [(0, Identity(K::Corridor))]), // capacity.shared
    fixed!(65, 48, 65_536, [(8, Identity(K::Corridor))]), // capacity.future_reservations
    fixed!(
        66,
        129,
        131_072,
        [
            (0, Identity(K::Site)),
            (33, Account),
            (65, Identity(K::Good)),
            (97, Identity(K::Unit))
        ]
    ), // service_connections
    fixed!(
        67,
        177,
        131_072,
        [
            (0, Identity(K::Order)),
            (40, Identity(K::Site)),
            (73, Account),
            (105, Identity(K::Good)),
            (137, Identity(K::Unit))
        ]
    ), // service_orders
    fixed!(
        68,
        72,
        65_536,
        [(0, Identity(K::Process)), (32, Identity(K::Site))]
    ),
    fixed!(
        71,
        282,
        65_536,
        [
            (0, Identity(K::FreightLot)),
            (32, Identity(K::Order)),
            (64, Identity(K::AidMandate)),
            (96, Identity(K::Route)),
            (146, Identity(K::FinalDemandPrincipal)),
            (178, Identity(K::FinalDemandPrincipal)),
            (210, Identity(K::Good)),
            (242, Identity(K::Unit))
        ]
    ), // aid.freight
    fixed!(
        72,
        169,
        327_680,
        [
            (0, Identity(K::Order)),
            (33, Account),
            (65, Identity(K::FinalDemandPrincipal)),
            (97, Identity(K::FinalDemandPrincipal))
        ]
    ), // aid.cash_reserves
];
pub(super) fn layout(id: u16) -> Option<Layout> {
    LAYOUTS
        .iter()
        .find(|(key, _)| *key == id)
        .map(|(_, shape)| *shape)
}
pub(super) fn kind(field: Field, row: &[u8]) -> Result<K, StorageError> {
    match field.kind {
        Identity(kind) => Ok(kind),
        Account => match row.get(field.offset.checked_sub(1).ok_or(StorageError::Layout)?) {
            Some(1) => Ok(K::Site),
            Some(2) => Ok(K::FinalDemandPrincipal),
            Some(3) => Ok(K::OrganizationAccount),
            Some(4) => Ok(K::PublicAccount),
            _ => Err(StorageError::IdentityKind),
        },
        EquipmentAsset => match row.get(field.offset.checked_sub(1).ok_or(StorageError::Layout)?) {
            Some(0) => Ok(K::Installation),
            Some(1) => Ok(K::EquipmentCohort),
            _ => Err(StorageError::IdentityKind),
        },
    }
}
