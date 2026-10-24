//! One shared native-unit resource allocator for routed and local outbound work.

mod residual;

#[path = "outbound/orders.rs"]
mod orders;

pub(crate) use orders::allocate_services;
#[cfg(test)]
pub(super) use orders::ensure_resource_group_count;
pub(super) use orders::{
    credit_local_transfers, dispatch_orders, dispatch_orders_with_aid, AidDispatch,
    OutboundReceipts, OutboundSelection,
};
use orders::{FreightRequest, FreightResourceKey};

use super::{BTreeMap, MaterialCircuitError};
