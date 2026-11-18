//! The buyer's dated orders and links to suppliers in the same observer frame.

use super::{
    accounting, readings, view, PrimaryView, ProductionCommand, ProductionNavigation,
    ProductionObservation, ProductionReadingSection,
};
use crate::cli;
use crate::human_numbers;
use crate::observer::ObservationContext;
use crate::observer_io::ObservationCache;
use crate::observer_theme as theme;
use babylon_material_circuit::SiteId;
use babylon_persistence::observer_reader::{
    CommodityOutcome, ObserverEconomyError, SiteProcurementOrder, SiteProcurementReading,
};
use babylon_persistence::production_observation::ProductionSnapshot;
use bevy::prelude::*;

#[derive(Component)]
pub(super) struct Rows;

pub(super) fn rebuild_rows(
    mut commands: Commands,
    roots: Query<Entity, With<Rows>>,
    observation: ProductionObservation,
    primary: Res<PrimaryView>,
    navigation: Res<ProductionNavigation>,
    cache: Option<Res<ObservationCache>>,
) {
    if !primary.is_changed()
        && !observation.frame.is_changed()
        && !observation.state.is_changed()
        && !navigation.is_changed()
        && !cache.as_ref().is_some_and(DetectChanges::is_changed)
    {
        return;
    }
    let Ok(root) = roots.single() else { return };
    let mut panel = commands.entity(root);
    panel.despawn_related::<Children>();
    if *primary != PrimaryView::Production
        || !navigation.details_open
        || navigation.reading_section != ProductionReadingSection::Orders
        || !accounting::authorized(&observation.state)
    {
        return;
    }

    let context = observation.state.context();
    if context.tick == 0 {
        panel.with_children(|parent| {
            parent.spawn(view::text(
                "Orders appear after the first completed period.",
                15.0,
                theme::PAPER,
            ));
        });
        return;
    }
    let Some(frame) = observation.frame.for_session(&observation.state) else {
        return;
    };
    let Some(snapshot) = frame.production.as_ref() else {
        return;
    };
    panel.with_children(|parent| {
        let orders = (|| {
            let buyer = navigation
                .selected_site
                .as_deref()
                .and_then(cli::identity_bytes)
                .map(SiteId::from_bytes)
                .ok_or(ObserverEconomyError::SiteAbsent)?;
            let foundation = cli::identity_bytes(&frame.foundation_digest)
                .ok_or(ObserverEconomyError::SourceChanged)?;
            let hash = frame
                .tick_content_hash
                .as_deref()
                .and_then(cli::identity_bytes)
                .ok_or(ObserverEconomyError::SourceChanged)?;
            let cursor = cache
                .as_deref()
                .ok_or(ObserverEconomyError::ProductionHistoryUnavailable)?
                .full_cursor_for_frame(
                    &observation.state,
                    &observation.frame,
                    &context,
                    foundation,
                    hash,
                )?;
            cursor.site_procurement_for_frame(
                context.campaign,
                context.tick,
                buyer,
                foundation,
                hash,
            )
        })();
        match orders {
            Ok(orders) => render_rows(parent, orders, &context, snapshot),
            Err(error) => {
                parent.spawn(view::text(
                    format!("Orders are unavailable for this period ({error})."),
                    15.0,
                    theme::PAPER,
                ));
            }
        }
    });
}

fn render_rows(
    parent: &mut ChildSpawnerCommands,
    reading: SiteProcurementReading,
    context: &ObservationContext,
    snapshot: &ProductionSnapshot,
) {
    let tick = context.tick;
    if reading.new_orders.is_empty() {
        parent.spawn(view::text(
            format!("No purchase requests recorded in period {tick}."),
            15.0,
            theme::PAPER,
        ));
    } else {
        parent.spawn(view::text(
            format!("Purchase requests recorded in period {tick}"),
            15.0,
            theme::YELLOW,
        ));
        for order in reading.new_orders {
            supplier_button(
                parent,
                context,
                snapshot,
                order.supplier_site_id,
                &summary(&order),
            );
        }
    }
    if !reading.earlier_deliveries.is_empty() {
        parent.spawn(view::text(
            format!("Received in period {tick} from earlier orders"),
            15.0,
            theme::YELLOW,
        ));
        for delivery in reading.earlier_deliveries {
            let delivered = human_numbers::grouped(u128::from(delivery.delivered));
            supplier_button(
                parent,
                context,
                snapshot,
                delivery.supplier_site_id,
                &format!(
                    "Received {delivered} · {} ({})",
                    delivery.good, delivery.unit
                ),
            );
        }
    }
}

fn supplier_button(
    parent: &mut ChildSpawnerCommands,
    context: &ObservationContext,
    snapshot: &ProductionSnapshot,
    supplier_id: SiteId,
    summary: &str,
) {
    let supplier = snapshot
        .sites
        .iter()
        .find(|site| cli::identity_bytes(&site.id) == Some(supplier_id.as_bytes()));
    if let Some(supplier) = supplier {
        view::button(
            parent,
            &format!("Supplier · {}\n{summary}", readings::site_subject(supplier)),
            ProductionCommand::Select {
                site_id: supplier.id.clone(),
                context: context.clone(),
            },
        );
    } else {
        parent.spawn(view::text(
            format!("Supplier site unavailable\n{summary}"),
            15.0,
            theme::PAPER,
        ));
    }
}

fn summary(order: &SiteProcurementOrder) -> String {
    use std::fmt::Write as _;

    let count = |quantity| human_numbers::grouped(u128::from(quantity));
    let quantities = order.quantities;
    let requested = count(quantities.requested);
    let funded = count(quantities.funded);
    let unfunded = count(quantities.requested - quantities.funded);
    let delivered = count(quantities.delivered);
    let price = human_numbers::currency(order.unit_price.micro_units());
    let reserved = human_numbers::currency(order.reserved_micros);
    let mut lines = format!(
        "{} ({}) · {price} per unit\nRequested {requested} · funded {funded} · unfunded {unfunded}\nFunding at order {reserved}",
        order.good, order.unit,
    );
    if let Some(position) = order.stock_position {
        let on_hand = count(position.on_hand);
        let outstanding = count(position.outstanding_inbound);
        let target = count(position.target);
        write!(
            lines,
            "\nAt decision: On hand {on_hand} · already on order {outstanding}\nStock target {target}"
        )
        .expect("writing to a String is infallible");
    }
    match quantities.outcome {
        CommodityOutcome::Goods {
            awaiting_dispatch,
            in_transit,
            lost,
        } => {
            let waiting = count(awaiting_dispatch);
            let transit = count(in_transit);
            let lost = count(lost);
            write!(
                lines,
                "\nDelivered {delivered} · awaiting dispatch {waiting}\nIn transit {transit} · freight loss {lost}"
            )
            .expect("writing to a String is infallible");
        }
        CommodityOutcome::Service { expired } => {
            let expired = count(expired);
            write!(lines, "\nService performed {delivered} · expired {expired}")
                .expect("writing to a String is infallible");
        }
    }
    lines
}
