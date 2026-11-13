//! Re-enter Archive history through current earned subjects and disclosed links.

use bevy::ecs::system::SystemParam;
use bevy::prelude::*;

use crate::dossier;
use crate::navigation::position::ArchiveFocus;
use crate::observer_ui::ObserverUiState;

use super::dossier_card::{
    chip_request, navigable_link, DossierControl, DossierFetchState, DossierPageView,
    DossierPresentation, DossierReadIdentity, DossierRefusal, DossierWriteState,
    SubjectPageRequest,
};
use babylon_persistence::ArchivePageRef;

const MAX_ROUTE_STEPS: usize = 128;

/// No cursor is retained: Archive cursors contain a read scope and must be reacquired.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct ArchiveRoute {
    subjects: Vec<ArchivePageRef>,
    page: usize,
    details: bool,
    technical: bool,
}

#[derive(Resource, Default)]
pub(crate) struct ArchiveNavigation {
    subjects: Vec<ArchivePageRef>,
    page: usize,
    restore: Option<ArchiveRestore>,
    failed: bool,
}

#[derive(SystemParam)]
pub(crate) struct ArchiveCapture<'w> {
    view: Option<Res<'w, DossierPageView>>,
    presentation: Option<Res<'w, DossierPresentation>>,
    navigation: Option<Res<'w, ArchiveNavigation>>,
}

impl ArchiveCapture<'_> {
    pub(crate) fn capture(&self) -> Option<ArchiveRoute> {
        Some(
            self.navigation
                .as_ref()?
                .capture(self.view.as_ref()?, self.presentation.as_ref()?),
        )
    }
}

#[derive(SystemParam)]
pub(crate) struct ArchiveDetails<'w> {
    presentation: Option<ResMut<'w, DossierPresentation>>,
}

impl ArchiveDetails<'_> {
    pub(crate) fn close_top(&mut self) -> bool {
        let Some(presentation) = self.presentation.as_mut() else {
            return false;
        };
        if presentation.technical_open {
            presentation.technical_open = false;
        } else if presentation.details_open {
            presentation.details_open = false;
        } else {
            return false;
        }
        true
    }
}

struct ArchiveRestore {
    route: ArchiveRoute,
    next_subject: usize,
    next_page: usize,
    started: bool,
}

impl ArchiveNavigation {
    pub(super) fn capture(
        &self,
        view: &DossierPageView,
        presentation: &DossierPresentation,
    ) -> ArchiveRoute {
        let subjects = match view {
            DossierPageView::Card => Vec::new(),
            DossierPageView::Subject(request) => {
                let target = request.target();
                if self.subjects.last() == target.as_ref() {
                    self.subjects.clone()
                } else {
                    target.into_iter().collect()
                }
            }
        };
        ArchiveRoute {
            subjects,
            page: if presentation.cursor.is_some() {
                self.page
            } else {
                0
            },
            details: presentation.details_open,
            technical: presentation.technical_open,
        }
    }

    pub(super) fn opened(&mut self, view: &DossierPageView) {
        self.cancel();
        self.page = 0;
        self.subjects = match view {
            DossierPageView::Card => Vec::new(),
            DossierPageView::Subject(request) => request.target().into_iter().collect(),
        };
    }

    pub(super) fn accepted(&mut self, control: &DossierControl) {
        self.cancel();
        match control {
            DossierControl::Link(request) => {
                if let Some(target) = request.target() {
                    if self.subjects.len() < MAX_ROUTE_STEPS {
                        self.subjects.push(target);
                    }
                }
                self.page = 0;
            }
            DossierControl::Back(_) => {
                self.subjects.clear();
                self.page = 0;
            }
            DossierControl::More(_, _) => self.page = (self.page + 1).min(MAX_ROUTE_STEPS),
            DossierControl::First(_) => self.page = 0,
            DossierControl::Details(_)
            | DossierControl::Technical(_)
            | DossierControl::OpenDetails(_, _) => {}
        }
    }

    pub(crate) fn begin(&mut self, route: ArchiveRoute) {
        self.failed = false;
        self.restore = Some(ArchiveRestore {
            route,
            next_subject: 0,
            next_page: 0,
            started: false,
        });
    }

    pub(crate) fn cancel(&mut self) {
        self.restore = None;
        self.failed = false;
    }

    pub(crate) fn is_restoring(&self) -> bool {
        self.restore.is_some()
    }

    pub(crate) fn restoration_failed(&self) -> bool {
        self.failed
    }
}

pub(super) fn focus_key(control: &DossierControl) -> Option<ArchiveFocus> {
    Some(match control {
        DossierControl::Link(request) => ArchiveFocus::Subject(request.target()?),
        DossierControl::Back(_) => ArchiveFocus::Back,
        DossierControl::More(_, _) => ArchiveFocus::More,
        DossierControl::First(_) => ArchiveFocus::First,
        DossierControl::Details(_) | DossierControl::OpenDetails(_, _) => ArchiveFocus::Details,
        DossierControl::Technical(_) => ArchiveFocus::Technical,
    })
}

/// Runs before the ordinary fetch driver. Each step reacquires its own current read scope.
pub(super) fn restore(
    mut navigation: ResMut<ArchiveNavigation>,
    identity: DossierReadIdentity,
    mut outputs: DossierWriteState,
    ui: Option<Res<ObserverUiState>>,
    mut refusal: DossierRefusal,
) {
    let Some(mut pending) = navigation.restore.take() else {
        return;
    };
    if ui.as_ref().is_none_or(|ui| !ui.archive_open) {
        return;
    }
    if !pending.started {
        *outputs.view = DossierPageView::Card;
        *outputs.presentation = DossierPresentation::default();
        outputs.projection.0 = None;
        *outputs.fetch = DossierFetchState::Idle;
        navigation.subjects.clear();
        navigation.page = 0;
        pending.started = true;
    }
    if identity.observer.as_ref().is_some_and(|session| {
        matches!(
            session.phase,
            crate::observer::SessionPhase::Failed | crate::observer::SessionPhase::Closed
        )
    }) {
        fallback(&mut refusal, &mut outputs, &mut navigation);
        return;
    }
    let Some(scope) = identity.scope(&outputs.view) else {
        navigation.restore = Some(pending);
        return;
    };
    if matches!(*outputs.fetch, DossierFetchState::Failed(_)) {
        fallback(&mut refusal, &mut outputs, &mut navigation);
        return;
    }
    if let Some(target) = pending.route.subjects.get(pending.next_subject) {
        let mut direct_scope = scope.clone();
        direct_scope.subject = target.clone();
        let direct = SubjectPageRequest {
            scope: direct_scope,
            kind: target.kind().as_str().into(),
            id: target.id().into(),
            label: None,
        };
        let earned_entry = pending.next_subject == 0
            && identity.observer.as_ref().is_some_and(|session| {
                identity
                    .organizer
                    .as_ref()
                    .is_some_and(|client| client.body_for(session).is_some())
            })
            && identity.organizer_subject(&DossierPageView::Subject(Box::new(direct.clone())));
        let request = if earned_entry {
            Some(direct)
        } else {
            let Some(installed) = outputs
                .projection
                .0
                .as_ref()
                .filter(|installed| identity.admits(installed, &outputs.view))
            else {
                navigation.restore = Some(pending);
                return;
            };
            dossier::retained_page(&installed.read).and_then(|page| {
                page.links
                    .iter()
                    .filter(|link| navigable_link(link))
                    .map(|link| chip_request(link, &installed.scope))
                    .find(|request| request.target().as_ref() == Some(target))
            })
        };
        let Some(request) = request else {
            fallback(&mut refusal, &mut outputs, &mut navigation);
            return;
        };
        navigation.subjects.push(target.clone());
        *outputs.view = DossierPageView::Subject(Box::new(request));
        outputs.projection.0 = None;
        *outputs.fetch = DossierFetchState::Idle;
        pending.next_subject += 1;
        navigation.restore = Some(pending);
        return;
    }
    let Some(installed) = outputs
        .projection
        .0
        .as_ref()
        .filter(|installed| identity.admits(installed, &outputs.view))
    else {
        navigation.restore = Some(pending);
        return;
    };
    let Some(page) = dossier::retained_page(&installed.read) else {
        fallback(&mut refusal, &mut outputs, &mut navigation);
        return;
    };
    if pending.next_page < pending.route.page {
        let Some(cursor) = page.changes.next_cursor.clone() else {
            fallback(&mut refusal, &mut outputs, &mut navigation);
            return;
        };
        outputs.presentation.cursor = Some(cursor);
        outputs.projection.0 = None;
        *outputs.fetch = DossierFetchState::Idle;
        pending.next_page += 1;
        navigation.page = pending.next_page;
        navigation.restore = Some(pending);
        return;
    }
    outputs.presentation.details_open = pending.route.details;
    outputs.presentation.technical_open = pending.route.details && pending.route.technical;
}

fn fallback(
    refusal: &mut DossierRefusal,
    outputs: &mut DossierWriteState,
    navigation: &mut ArchiveNavigation,
) {
    *outputs.view = DossierPageView::Card;
    *outputs.presentation = DossierPresentation::default();
    outputs.projection.0 = None;
    *outputs.fetch = DossierFetchState::Idle;
    navigation.subjects.clear();
    navigation.page = 0;
    navigation.failed = true;
    if let Some(feedback) = &mut refusal.feedback {
        feedback.reject(
            "That Archive subject or page is unavailable. Returned to its available parent.",
            refusal
                .time
                .as_ref()
                .map_or(0.0, |time| time.elapsed_secs_f64()),
        );
    }
}
