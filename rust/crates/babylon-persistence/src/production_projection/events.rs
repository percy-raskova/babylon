//! Dated receipt events joined through authenticated orders and shared opening identities.
use super::{history::OrderHistory, metadata::Metadata, ProductionProjectionError};
use crate::{
    michigan_economy::digest_hex,
    production_observation::{
        ProductionDeliveryEvidence, ProductionDeliveryStage, ProductionEvent,
    },
};
use babylon_material_circuit::{OrderId, SupplierRoute, SupplierTransport};
use babylon_tick::material_world::MaterialTickReceipts;
type Result<T> = std::result::Result<T, ProductionProjectionError>;
type Emit<'a> = dyn FnMut(&str, Vec<String>, String, Option<ProductionDeliveryEvidence>) + 'a;

fn order_route<'a>(
    metadata: &Metadata<'a>,
    history: &OrderHistory,
    id: OrderId,
) -> Result<&'a SupplierRoute> {
    let order = history
        .deliveries
        .get(&id)
        .ok_or(ProductionProjectionError::State)?;
    let route = *metadata
        .routes
        .get(&(order.buyer, order.supplier, order.good, order.unit))
        .ok_or(ProductionProjectionError::Content)?;
    if route.route_id != order.route {
        return Err(ProductionProjectionError::State);
    }
    Ok(route)
}

pub(super) fn project_events(
    metadata: &Metadata<'_>,
    history: &OrderHistory,
    receipts: &MaterialTickReceipts,
    digest: [u8; 32],
    events: &mut Vec<ProductionEvent>,
) -> Result<()> {
    let receipt_digest = digest_hex(&digest);
    let mut emit = |kind: &str, subjects: Vec<String>, description: String, delivery_evidence| {
        events.push(ProductionEvent {
            id: format!("{receipt_digest}:{}", events.len()),
            period: receipts.resolve_tick,
            subject_site_ids: subjects,
            kind: kind.to_owned(),
            description,
            receipt_digest: receipt_digest.clone(),
            delivery_evidence,
        });
    };
    emit_production_events(metadata, receipts, &mut emit)?;
    for dispatch in &receipts.dispatches {
        let route = order_route(metadata, history, dispatch.order_id)?;
        if route.route_id != dispatch.route_id {
            return Err(ProductionProjectionError::State);
        }
        emit_route_event(
            metadata,
            (route, dispatch.order_id),
            "dispatch",
            dispatch.quantity,
            Some(dispatch.final_arrival_period),
            None,
            &mut emit,
        )?;
    }
    emit_local_trade_events(metadata, history, receipts, &mut emit)?;
    for loss in &receipts.losses {
        emit_route_event(
            metadata,
            (
                order_route(metadata, history, loss.order_id)?,
                loss.order_id,
            ),
            "freight loss",
            loss.quantity,
            None,
            None,
            &mut emit,
        )?;
    }
    for arrival in &receipts.arrivals {
        emit_route_event(
            metadata,
            (
                order_route(metadata, history, arrival.order_id)?,
                arrival.order_id,
            ),
            "arrival",
            arrival.quantity,
            None,
            Some(ProductionDeliveryStage::Arrival),
            &mut emit,
        )?;
    }
    for delivery in &receipts.deliveries {
        emit_route_event(
            metadata,
            (
                order_route(metadata, history, delivery.order_id)?,
                delivery.order_id,
            ),
            "delivery",
            delivery.quantity,
            None,
            Some(ProductionDeliveryStage::Delivery),
            &mut emit,
        )?;
    }
    for realization in &receipts.realizations {
        emit_route_event(
            metadata,
            (
                order_route(metadata, history, realization.order_id)?,
                realization.order_id,
            ),
            "quantity realization",
            realization.quantity,
            None,
            Some(ProductionDeliveryStage::QuantityRealization),
            &mut emit,
        )?;
    }
    Ok(())
}

fn emit_production_events(
    metadata: &Metadata<'_>,
    receipts: &MaterialTickReceipts,
    emit: &mut Emit<'_>,
) -> Result<()> {
    for production in &receipts.production {
        let (site, _, recipe) = metadata
            .processes
            .get(&production.process_id)
            .ok_or(ProductionProjectionError::Content)?;
        if site.site_id != production.site_id {
            return Err(ProductionProjectionError::State);
        }
        let good = metadata.good(recipe.output.good_id, recipe.output.unit_id)?;
        let quantity = production
            .produced_batches
            .checked_mul(recipe.output.quantity)
            .ok_or(ProductionProjectionError::Arithmetic)?;
        emit(
            "production",
            vec![digest_hex(&site.site_id.as_bytes())],
            format!(
                "{}: {} of {} planned batches; {quantity} {} {} produced.",
                site.label,
                production.produced_batches,
                production.planned_batches,
                good.unit_label,
                good.label,
            ),
            None,
        );
    }
    Ok(())
}

fn emit_local_trade_events(
    metadata: &Metadata<'_>,
    history: &OrderHistory,
    receipts: &MaterialTickReceipts,
    emit: &mut Emit<'_>,
) -> Result<()> {
    for transfer in &receipts.local_transfers {
        let route = order_route(metadata, history, transfer.order_id)?;
        if !matches!(route.transport_kind, SupplierTransport::Local)
            || (
                transfer.supplier_site_id,
                transfer.buyer_site_id,
                transfer.good_id,
                transfer.unit_id,
            ) != (
                route.supplier_site_id,
                route.buyer_site_id,
                route.good_id,
                route.unit_id,
            )
        {
            return Err(ProductionProjectionError::State);
        }
        emit_route_event(
            metadata,
            (route, transfer.order_id),
            "local transfer",
            transfer.quantity,
            None,
            None,
            emit,
        )?;
    }
    for fulfillment in &receipts.local_fulfillments {
        let order = &history
            .final_orders
            .get(&fulfillment.order_id)
            .ok_or(ProductionProjectionError::State)?
            .order;
        let retailer = metadata.site(order.retailer_site_id)?;
        let good = metadata.good(order.good_id, order.unit_id)?;
        if (
            fulfillment.retailer_site_id,
            fulfillment.demand_principal_id,
            fulfillment.good_id,
            fulfillment.unit_id,
        ) != (
            retailer.site_id,
            order.demand_principal_id,
            good.good_id,
            good.unit_id,
        ) {
            return Err(ProductionProjectionError::State);
        }
        emit("end-buyer fulfillment", vec![digest_hex(&retailer.site_id.as_bytes())], format!(
            "{}: {} {} {} delivered to local end buyers; consumption and payment have separate receipts.",
            retailer.label, fulfillment.quantity, good.unit_label, good.label,
        ), None);
    }
    Ok(())
}

fn emit_route_event(
    metadata: &Metadata<'_>,
    (route, order_id): (&SupplierRoute, OrderId),
    kind: &str,
    quantity: u64,
    arrival: Option<u64>,
    stage: Option<ProductionDeliveryStage>,
    emit: &mut Emit<'_>,
) -> Result<()> {
    let supplier = metadata.site(route.supplier_site_id)?;
    let buyer = metadata.site(route.buyer_site_id)?;
    let good = metadata.good(route.good_id, route.unit_id)?;
    let suffix = arrival.map_or_else(String::new, |period| format!(" Arrival period {period}."));
    emit(
        kind,
        vec![
            digest_hex(&supplier.site_id.as_bytes()),
            digest_hex(&buyer.site_id.as_bytes()),
        ],
        format!(
            "{} -> {}: {quantity} {} {} {kind}.{suffix}",
            supplier.label, buyer.label, good.unit_label, good.label
        ),
        stage.map(|stage| ProductionDeliveryEvidence {
            supplier_relation_id: super::routes::relation_id((
                route.buyer_site_id,
                route.supplier_site_id,
                route.good_id,
                route.unit_id,
            )),
            stage,
            order_id: digest_hex(&order_id.as_bytes()),
            route_id: digest_hex(&route.route_id.as_bytes()),
            good_id: digest_hex(&good.good_id.as_bytes()),
            unit_id: digest_hex(&good.unit_id.as_bytes()),
            quantity,
        }),
    );
    Ok(())
}
