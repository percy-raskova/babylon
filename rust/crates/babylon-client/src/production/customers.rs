//! Household customers in the selected retailer’s disclosed production account.
use super::view;
use super::{
    accounting, navigation, readings, PrimaryView, ProductionCommand, ProductionNavigation,
    ProductionObservation, ProductionReadingSection,
};
use crate::atlas::CountyAtlas;
use crate::cli;
use crate::observer::ObservationContext;
use crate::observer_io::ObservationCache;
use crate::observer_map3d::money_map::household::{self, HouseholdRead, Reading};
use crate::observer_theme as theme;
use crate::observer_ui::ObserverUiState;
use crate::ui::Interaction;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_persistence::production_observation::ProductionSnapshot;
use bevy::a11y::AccessibilityNode;
use bevy::input_focus::{FocusCause, InputFocus};
use bevy::prelude::*;
use bevy::tasks::{self, IoTaskPool, Task};

#[derive(Component)]
pub(super) struct Rows;

pub(super) fn served(
    snapshot: &ProductionSnapshot,
    retailer: &str,
    principal: FinalDemandPrincipalId,
    period: u64,
) -> bool {
    served_at(snapshot, retailer, principal, period, None)
}

pub(super) fn served_at(
    snapshot: &ProductionSnapshot,
    retailer: &str,
    principal: FinalDemandPrincipalId,
    period: u64,
    county: Option<&str>,
) -> bool {
    snapshot.household_accounts.iter().any(|row| {
        county.is_none_or(|fips| matches!(row.location, EconomicLocation::County(c) if c.geoid().as_str() == fips))
            && row.retailer_site_id == retailer
            && cli::identity_bytes(&row.demand_principal_id) == Some(principal.as_bytes())
            && row
                .completed
                .as_ref()
                .is_some_and(|done| done.period == period)
    })
}

#[derive(Component, Clone, PartialEq, Eq)]
pub(super) enum CustomerControl {
    Open {
        principal: FinalDemandPrincipalId,
        good: String,
        unit: String,
    },
    Back,
}

#[derive(PartialEq, Eq)]
pub(super) struct CustomerScope {
    context: ObservationContext,
    retailer: String,
    household: Option<FinalDemandPrincipalId>,
    authorized: bool,
}

#[derive(Default)]
pub(super) struct Controls {
    scope: Option<CustomerScope>,
    origin: Option<CustomerControl>,
}

impl Controls {
    fn focus_after(
        &mut self,
        next: Option<&CustomerScope>,
        current: Option<CustomerControl>,
    ) -> Option<CustomerControl> {
        let (old, new) = self.scope.as_ref().zip(next)?;
        if old.retailer != new.retailer
            || old.context.campaign != new.context.campaign
            || old.context.perspective != new.context.perspective
            || !old.authorized
            || !new.authorized
        {
            self.origin = None;
            return None;
        }
        match (old.household, new.household) {
            (None, Some(id)) => {
                self.origin = current.filter(|target| matches!(target, CustomerControl::Open{principal,..} if *principal == id));
                Some(CustomerControl::Back)
            }
            (Some(_), None) => self.origin.take(),
            _ => current,
        }
    }
}

pub(super) fn rebuild_rows(
    mut commands: Commands,
    roots: Query<Entity, With<Rows>>,
    observation: ProductionObservation,
    navigation: Res<ProductionNavigation>,
    controls: Query<(&CustomerControl, &Interaction)>,
    mut focus: Option<ResMut<InputFocus>>,
    mut previous: Local<Controls>,
) {
    if !observation.frame.is_changed()
        && !observation.state.is_changed()
        && !navigation.is_changed()
    {
        return;
    }
    let Ok(root) = roots.single() else { return };
    let snapshot = observation
        .frame
        .for_session(&observation.state)
        .and_then(|frame| frame.production.as_ref());
    let next = navigation
        .selected_site
        .as_ref()
        .filter(|_| {
            snapshot.is_some()
                && navigation.details_open
                && navigation.reading_section == ProductionReadingSection::Flow
        })
        .map(|site| CustomerScope {
            context: observation.state.context(),
            retailer: site.clone(),
            household: navigation.household,
            authorized: accounting::authorized(&observation.state),
        });
    if previous.scope == next && !observation.frame.is_changed() {
        return;
    }
    // A pointer press may start on a different row than the keyboard focus.
    let current = controls
        .iter()
        .find(|(_, interaction)| **interaction == Interaction::Pressed)
        .map(|(row, _)| row)
        .or_else(|| {
            focus
                .as_ref()?
                .get()
                .and_then(|entity| controls.get(entity).ok().map(|(row, _)| row))
        })
        .cloned();
    let restore = previous.focus_after(next.as_ref(), current);
    previous.scope = next;
    let mut rows = commands.entity(root);
    rows.despawn_related::<Children>();
    if let Some((scope, snapshot)) = previous.scope.as_ref().zip(snapshot) {
        rows.with_children(|parent| {
            render_customers(parent, scope, snapshot, |target, entity| {
                if restore.as_ref() == Some(target) {
                    if let Some(focus) = focus.as_deref_mut() {
                        focus.set(entity, FocusCause::Navigated);
                    }
                }
            });
        });
    }
}

fn render_customers(
    parent: &mut ChildSpawnerCommands,
    scope: &CustomerScope,
    snapshot: &ProductionSnapshot,
    mut rendered: impl FnMut(&CustomerControl, Entity),
) {
    if scope.household.is_some() && scope.authorized {
        let entity = customer_button(
            parent,
            "Back to retailer".into(),
            ProductionCommand::Reading(ProductionReadingSection::Flow),
            CustomerControl::Back,
        );
        rendered(&CustomerControl::Back, entity);
        return;
    }
    for row in snapshot
        .household_accounts
        .iter()
        .filter(|row| row.retailer_site_id == scope.retailer)
    {
        let summary = readings::customer_summary(row);
        let principal =
            cli::identity_bytes(&row.demand_principal_id).map(FinalDemandPrincipalId::from_bytes);
        let admitted = scope.authorized
            && row
                .completed
                .as_ref()
                .is_some_and(|done| done.period == scope.context.tick);
        if let Some(principal) = principal.filter(|_| admitted) {
            let target = CustomerControl::Open {
                principal,
                good: row.good_id.clone(),
                unit: row.unit_id.clone(),
            };
            let entity = customer_button(
                parent,
                format!(
                    "Open household receipt · {}\n{summary}",
                    &row.demand_principal_id[..8]
                ),
                ProductionCommand::Household {
                    site_id: scope.retailer.clone(),
                    principal,
                    context: scope.context.clone(),
                },
                target.clone(),
            );
            rendered(&target, entity);
        } else {
            parent.spawn(view::text(summary, 15.0, theme::PAPER));
        }
    }
}

fn customer_button(
    parent: &mut ChildSpawnerCommands,
    label: String,
    command: ProductionCommand,
    target: CustomerControl,
) -> Entity {
    let mut entity = parent.spawn((view::button_node(command), target));
    entity.with_child(view::text(label.clone(), 15.0, theme::PAPER));
    entity
        .entry::<AccessibilityNode>()
        .and_modify(move |mut node| node.set_label(label));
    entity.id()
}

#[derive(Resource, Default)]
pub(crate) struct Receipt {
    request: Option<HouseholdRead>,
    text: Option<String>,
}
impl Receipt {
    pub(super) fn text(&self) -> &str {
        self.text
            .as_deref()
            .unwrap_or("Reading the household receipt…")
    }
}

fn request(
    observation: &ProductionObservation,
    navigation: &ProductionNavigation,
    view: PrimaryView,
    ui: &ObserverUiState,
) -> Option<HouseholdRead> {
    let principal = navigation.household?;
    if !accounting::authorized(&observation.state)
        || navigation.reading_section != ProductionReadingSection::Flow
    {
        return None;
    }
    let frame = observation.frame.for_session(&observation.state)?;
    let snapshot = frame.production.as_ref()?;
    let site = navigation.selected_site.as_ref()?;
    if !navigation::readings_panel_visible(view, navigation, ui, Some(snapshot))
        || !served(snapshot, site, principal, frame.resolve_tick)
    {
        return None;
    }
    Some(HouseholdRead {
        context: observation.state.context(),
        principal,
        foundation: frame.foundation_digest.clone(),
        tick_hash: frame.tick_content_hash.clone()?,
    })
}

pub(super) fn update(
    observation: ProductionObservation,
    navigation: Res<ProductionNavigation>,
    view: Res<PrimaryView>,
    ui: Res<ObserverUiState>,
    (cache, atlas): (Option<Res<ObservationCache>>, Res<CountyAtlas>),
    mut receipt: ResMut<Receipt>,
    mut pending: Local<Option<(HouseholdRead, Task<Reading>)>>,
) {
    if observation.frame.is_changed()
        || observation.state.is_changed()
        || navigation.is_changed()
        || view.is_changed()
        || ui.is_changed()
    {
        let current = request(&observation, &navigation, *view, &ui);
        if receipt.request != current {
            receipt.request = current;
            receipt.text = None;
        }
    }
    if let Some((key, task)) = pending.as_mut() {
        let Some(result) = tasks::block_on(tasks::futures_lite::future::poll_once(task)) else {
            return;
        };
        if receipt.request.as_ref() == Some(key) {
            receipt.text = Some(household::sections(Some(&result), &atlas).join("\n\n"));
        }
        *pending = None;
    }
    if let Some(key) = receipt.request.as_ref().filter(|_| receipt.text.is_none()) {
        let reader = cache.as_deref().and_then(ObservationCache::full_reader);
        let requested = key.clone();
        *pending = Some((
            key.clone(),
            IoTaskPool::get().spawn(async move { requested.read(reader) }),
        ));
    }
}
