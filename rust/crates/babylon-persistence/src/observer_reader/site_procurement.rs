//! Buyer orders submitted during one authenticated completed period.

use super::{ObserverEconomyError, ObserverMaterialCursor};
use crate::economic_catalog::{CommodityLabel, EconomicOpening};
use crate::identity::CampaignId;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, GoodId, OrderId, OrderRow, SiteId, UnitId};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;
use std::result::Result as StdResult;

type Result<T> = StdResult<T, ObserverEconomyError>;
const INVALID: ObserverEconomyError = ObserverEconomyError::InvalidProjection;

/// Outcome of a newly funded claim at the close which recorded the request.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CommodityOutcome {
    Goods {
        awaiting_dispatch: u64,
        in_transit: u64,
        lost: u64,
    },
    Service {
        expired: u64,
    },
}

/// Exact quantities in the order's native unit.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProcurementQuantities {
    pub requested: u64,
    pub funded: u64,
    pub delivered: u64,
    pub outcome: CommodityOutcome,
}

impl ProcurementQuantities {
    fn goods(requested: u64, funded: u64, shipped: u64, delivered: u64, lost: u64) -> Result<Self> {
        let awaiting_dispatch = funded.checked_sub(shipped).ok_or(INVALID)?;
        let in_transit = shipped
            .checked_sub(delivered)
            .and_then(|rest| rest.checked_sub(lost))
            .ok_or(INVALID)?;
        if funded > requested {
            return Err(INVALID);
        }
        Ok(Self {
            requested,
            funded,
            delivered,
            outcome: CommodityOutcome::Goods {
                awaiting_dispatch,
                in_transit,
                lost,
            },
        })
    }

    fn service(requested: u64, funded: u64, performed: u64, expired: u64) -> Result<Self> {
        if funded > requested || performed.checked_add(expired) != Some(funded) {
            return Err(INVALID);
        }
        Ok(Self {
            requested,
            funded,
            delivered: performed,
            outcome: CommodityOutcome::Service { expired },
        })
    }
}

/// Inventory position when the buyer considered this goods request.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StockPosition {
    pub on_hand: u64,
    pub outstanding_inbound: u64,
    pub target: u64,
}

/// One positive procurement request, including requests that the buyer could not fund.
#[derive(Debug, PartialEq, Eq)]
pub struct SiteProcurementOrder {
    pub order_id: OrderId,
    pub supplier_site_id: SiteId,
    pub good: String,
    pub unit: String,
    pub quantities: ProcurementQuantities,
    pub unit_price: Currency,
    pub reserved_micros: i128,
    pub stock_position: Option<StockPosition>,
}

impl SiteProcurementOrder {
    fn new(
        opening: &EconomicOpening,
        order_id: OrderId,
        supplier_site_id: SiteId,
        commodity: (GoodId, UnitId),
        quantities: ProcurementQuantities,
        unit_price: Currency,
        stock_position: Option<StockPosition>,
    ) -> Result<Self> {
        let label = commodity_label(opening, commodity)?;
        let reserved_micros = unit_price
            .micro_units()
            .checked_mul(i128::from(quantities.funded))
            .ok_or(INVALID)?;
        Ok(Self {
            order_id,
            supplier_site_id,
            good: label.label.clone(),
            unit: label.unit_label.clone(),
            quantities,
            unit_price,
            reserved_micros,
            stock_position,
        })
    }
}

/// An authenticated delivery total on earlier orders from one supplier.
#[derive(Debug, PartialEq, Eq)]
pub struct EarlierOrderDelivery {
    pub supplier_site_id: SiteId,
    pub good: String,
    pub unit: String,
    pub delivered: u64,
}

/// New requests and deliveries from earlier orders cannot overlap.
#[derive(Debug, PartialEq, Eq)]
pub struct SiteProcurementReading {
    pub new_orders: Vec<SiteProcurementOrder>,
    pub earlier_deliveries: Vec<EarlierOrderDelivery>,
}

#[derive(Default)]
struct GoodsSettlement {
    delivered: u64,
    lost: u64,
}

impl ObserverMaterialCursor {
    /// Read new requests and arrivals from earlier orders at the displayed close.
    ///
    /// Goods receipts join by order identity to that close's deliveries, local
    /// transfers, freight losses and remaining orders. Service receipts already
    /// record admission, performance and expiry for each provider.
    ///
    /// # Errors
    /// Refuses changed frames, unknown buyers and inconsistent close quantities.
    pub fn site_procurement_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        buyer: SiteId,
        foundation: [u8; 32],
        tick_hash: [u8; 32],
    ) -> Result<SiteProcurementReading> {
        let (admission, close) = self.displayed_frame(campaign, tick, foundation, tick_hash)?;
        let opening = admission.view().opening;
        if !opening.sites.iter().any(|site| site.site_id == buyer) {
            return Err(ObserverEconomyError::SiteAbsent);
        }
        let rows = &close.receipts;
        let prior = &close.opening(&admission).state().orders;
        let closing = &close.register.state().orders;
        let mut new_orders = new_goods_orders(opening, rows, closing, buyer)?;
        for row in &rows.service_performance {
            if row.buyer != AccountId::Site(buyer) || row.requested_quantity == 0 {
                continue;
            }
            let quantities = ProcurementQuantities::service(
                row.requested_quantity,
                row.admitted_quantity,
                row.performed_quantity,
                row.expired_quantity,
            )?;
            new_orders.push(SiteProcurementOrder::new(
                opening,
                row.order_id,
                row.provider_site_id,
                (row.good_id, row.unit_id),
                quantities,
                row.unit_price,
                None,
            )?);
        }
        let earlier_deliveries = earlier_delivery_totals(prior, buyer, deliveries(rows))?
            .into_iter()
            .map(|((supplier_site_id, good, unit), delivered)| {
                let label = commodity_label(opening, (good, unit))?;
                Ok(EarlierOrderDelivery {
                    supplier_site_id,
                    good: label.label.clone(),
                    unit: label.unit_label.clone(),
                    delivered,
                })
            })
            .collect::<Result<_>>()?;
        Ok(SiteProcurementReading {
            new_orders,
            earlier_deliveries,
        })
    }
}

fn new_goods_orders(
    opening: &EconomicOpening,
    rows: &MaterialTickReceipts,
    closing: &[OrderRow],
    buyer: SiteId,
) -> Result<Vec<SiteProcurementOrder>> {
    let mut settlements = rows
        .procurement
        .iter()
        .filter(|row| row.buyer_site_id == buyer && row.desired_quantity > 0)
        .map(|row| (row.order_id, GoodsSettlement::default()))
        .collect::<BTreeMap<_, _>>();
    if settlements.is_empty() {
        return Ok(Vec::new());
    }
    for (order, quantity) in deliveries(rows) {
        if let Some(settlement) = settlements.get_mut(&order) {
            settlement.delivered = settlement.delivered.checked_add(quantity).ok_or(INVALID)?;
        }
    }
    for row in &rows.losses {
        if let Some(settlement) = settlements.get_mut(&row.order_id) {
            settlement.lost = settlement.lost.checked_add(row.quantity).ok_or(INVALID)?;
        }
    }
    let mut result = Vec::with_capacity(settlements.len());
    for row in &rows.procurement {
        let Some(settlement) = settlements.remove(&row.order_id) else {
            continue;
        };
        let shipped = match closing.binary_search_by_key(&row.order_id, |order| order.order_id) {
            Ok(index) => {
                let order = &closing[index];
                if (
                    order.buyer_site_id,
                    order.supplier_site_id,
                    order.good_id,
                    order.unit_id,
                ) != (
                    row.buyer_site_id,
                    row.supplier_site_id,
                    row.good_id,
                    row.unit_id,
                ) || order.ordered != row.admitted_quantity
                    || order.delivered != settlement.delivered
                    || order.lost != settlement.lost
                {
                    return Err(INVALID);
                }
                order.shipped
            }
            Err(_)
                if settlement.delivered.checked_add(settlement.lost)
                    == Some(row.admitted_quantity) =>
            {
                row.admitted_quantity
            }
            Err(_) => return Err(INVALID),
        };
        let quantities = ProcurementQuantities::goods(
            row.desired_quantity,
            row.admitted_quantity,
            shipped,
            settlement.delivered,
            settlement.lost,
        )?;
        result.push(SiteProcurementOrder::new(
            opening,
            row.order_id,
            row.supplier_site_id,
            (row.good_id, row.unit_id),
            quantities,
            row.unit_price,
            Some(StockPosition {
                on_hand: row.on_hand,
                outstanding_inbound: row.outstanding_inbound,
                target: row.target_stock,
            }),
        )?);
    }
    Ok(result)
}

fn commodity_label(
    opening: &EconomicOpening,
    commodity: (GoodId, UnitId),
) -> Result<&CommodityLabel> {
    opening
        .commodity_labels
        .iter()
        .find(|row| (row.good_id, row.unit_id) == commodity)
        .ok_or(INVALID)
}

fn deliveries(rows: &MaterialTickReceipts) -> impl Iterator<Item = (OrderId, u64)> + '_ {
    rows.deliveries
        .iter()
        .map(|row| (row.order_id, row.quantity))
        .chain(
            rows.local_transfers
                .iter()
                .map(|row| (row.order_id, row.quantity)),
        )
}

type SupplierCommodity = (SiteId, GoodId, UnitId);

fn earlier_delivery_totals(
    opening_orders: &[OrderRow],
    buyer: SiteId,
    receipts: impl Iterator<Item = (OrderId, u64)>,
) -> Result<BTreeMap<SupplierCommodity, u64>> {
    let prior = opening_orders
        .iter()
        .filter(|row| row.buyer_site_id == buyer)
        .map(|row| (row.order_id, row))
        .collect::<BTreeMap<_, _>>();
    let mut totaled = BTreeMap::<_, u64>::new();
    if prior.is_empty() {
        return Ok(totaled);
    }
    for (order_id, quantity) in receipts {
        if let Some(order) = prior.get(&order_id) {
            let key = (order.supplier_site_id, order.good_id, order.unit_id);
            let total = totaled.entry(key).or_default();
            *total = total.checked_add(quantity).ok_or(INVALID)?;
        }
    }
    Ok(totaled)
}

#[cfg(test)]
mod tests {
    use super::{CommodityOutcome, ProcurementQuantities};
    use babylon_material_circuit::{GoodId, OrderAccessMode, OrderId, OrderRow, SiteId, UnitId};
    use std::collections::BTreeMap;

    #[test]
    fn earlier_deliveries_use_the_opening_order_even_when_fully_settled() {
        let buyer = SiteId::from_bytes([1; 32]);
        let supplier = SiteId::from_bytes([2; 32]);
        let other_buyer = SiteId::from_bytes([3; 32]);
        let good = GoodId::from_bytes([4; 32]);
        let unit = UnitId::from_bytes([5; 32]);
        let prior = OrderRow {
            order_id: OrderId::from_bytes([6; 32]),
            access_mode: OrderAccessMode::CommoditySale,
            buyer_site_id: buyer,
            supplier_site_id: supplier,
            good_id: good,
            unit_id: unit,
            ordered: 34,
            shipped: 34,
            lost: 0,
            delivered: 0,
            realized: 0,
        };
        let unrelated = OrderRow {
            order_id: OrderId::from_bytes([7; 32]),
            buyer_site_id: other_buyer,
            ..prior.clone()
        };
        let new_order = OrderId::from_bytes([8; 32]);
        let deliveries = [
            (prior.order_id, 12),
            (prior.order_id, 22),
            (unrelated.order_id, 27),
            (new_order, 88),
        ];
        assert_eq!(
            super::earlier_delivery_totals(&[prior, unrelated], buyer, deliveries.into_iter()),
            Ok(BTreeMap::from([((supplier, good, unit), 34)])),
        );
    }

    #[test]
    fn partial_admission_keeps_delivery_pending_and_loss_separate() {
        let quantities =
            ProcurementQuantities::goods(20, 16, 8, 6, 1).expect("consistent settlement");
        assert_eq!(quantities.requested, 20);
        assert_eq!(quantities.funded, 16);
        assert_eq!(quantities.delivered, 6);
        assert_eq!(
            quantities.outcome,
            CommodityOutcome::Goods {
                awaiting_dispatch: 8,
                in_transit: 1,
                lost: 1,
            },
        );
        assert!(ProcurementQuantities::goods(20, 16, 8, 8, 1).is_err());
    }

    #[test]
    fn period_service_expires_while_an_unfunded_request_never_ships() {
        let service = ProcurementQuantities::service(20, 14, 3, 11).expect("service close");
        assert_eq!(service.delivered, 3);
        assert_eq!(service.outcome, CommodityOutcome::Service { expired: 11 });
        assert!(ProcurementQuantities::service(20, 14, 3, 0).is_err());

        let unfunded = ProcurementQuantities::goods(20, 0, 0, 0, 0).expect("unfunded order");
        assert_eq!(unfunded.funded, 0);
        assert_eq!(unfunded.delivered, 0);
        assert_eq!(
            unfunded.outcome,
            CommodityOutcome::Goods {
                awaiting_dispatch: 0,
                in_transit: 0,
                lost: 0,
            },
        );
    }
}
