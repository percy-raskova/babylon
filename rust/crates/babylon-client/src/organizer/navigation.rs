//! Presentation descriptors restored against the current organizer disclosure.

use crate::observer::ObserverSession;
use bevy::prelude::*;

use super::evidence::EvidenceMode;
use super::scene::{OrganizerSceneMode, OrganizerSubject};
use super::ui::OrganizerAction;
use super::workspace::DispatchDestination;
use super::workspace_copy::Destination;
use super::{OrganizerClient, OrganizerInspector};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum EvidenceRoute {
    Reports,
    Subject(u64),
    Saved,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum FocusControl {
    Action(OrganizerAction),
    Detail(DispatchDestination),
    Subject(OrganizerSubject),
}

/// Dated links contribute their destination only, never their captured admission context.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct OrganizerFocus(FocusControl);

impl OrganizerFocus {
    pub(crate) fn from_action(action: OrganizerAction) -> Self {
        Self(match action {
            OrganizerAction::Follow(link) => match link.destination {
                Destination::Detail(detail) => FocusControl::Detail(detail),
                Destination::Subject(subject) => FocusControl::Subject(subject),
            },
            action => FocusControl::Action(action),
        })
    }
}

pub(super) fn sync_focus_keys(
    buttons: Query<(
        Entity,
        &super::ui::ActionButton,
        Option<&crate::navigation::position::NavigationFocus>,
    )>,
    mut commands: Commands,
) {
    for (entity, action, current) in &buttons {
        let next = crate::navigation::position::NavigationFocus::Organizer(
            OrganizerFocus::from_action(action.0),
        );
        if current != Some(&next) {
            commands.entity(entity).insert(next);
        }
    }
}

/// Contains identities and presentation choices, never a retained organizer view.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct OrganizerRoute {
    scene: OrganizerSceneMode,
    subject: Option<OrganizerSubject>,
    inspector: OrganizerInspector,
    evidence: EvidenceRoute,
    report: Option<[u8; 32]>,
}

impl OrganizerClient {
    pub(crate) fn navigation_route(&self, period: u64) -> OrganizerRoute {
        OrganizerRoute {
            scene: self.scene_mode,
            subject: self.selected_subject,
            inspector: self.inspector,
            evidence: match self.evidence.mode {
                EvidenceMode::Reports => EvidenceRoute::Reports,
                EvidenceMode::Subject(id) => EvidenceRoute::Subject(id),
                EvidenceMode::Saved => EvidenceRoute::Saved,
            },
            report: (self.inspector == OrganizerInspector::Evidence)
                .then(|| self.selected_evidence_id(period))
                .flatten(),
        }
    }

    /// Context changes invalidate reviews while preserving the draft and accepted ruling.
    pub(crate) fn navigation_context_changed(&mut self) {
        self.clear_review();
        self.return_focus = None;
        if self.inspector == OrganizerInspector::Review {
            self.inspector = OrganizerInspector::Closed;
        }
    }

    pub(crate) fn organizing_home(&mut self) {
        self.inspector = OrganizerInspector::Closed;
        self.return_focus = None;
    }

    pub(crate) fn close_navigation_detail(&mut self, focus: &mut bevy::input_focus::InputFocus) {
        self.inspector = OrganizerInspector::Closed;
        if let Some(entity) = self.return_focus.take() {
            focus.set(entity, bevy::input_focus::FocusCause::Navigated);
        }
    }

    /// A missing identity returns to its parent, without selecting a replacement subject.
    pub(crate) fn restore_navigation(&mut self, route: &OrganizerRoute, session: &ObserverSession) {
        self.scene_mode = route.scene;
        self.return_focus = None;
        self.inspector = route.inspector;
        self.selected_subject = route.subject.filter(|subject| {
            self.scene_for(session)
                .is_some_and(|scene| scene.nodes.iter().any(|node| node.subject == *subject))
        });
        if route.subject.is_some() && self.selected_subject.is_none() {
            self.inspector = OrganizerInspector::Closed;
            self.message =
                "That subject is unavailable in this observation. Returned to organizing.".into();
        }
        if route.inspector == OrganizerInspector::Review {
            self.clear_review();
            self.inspector = OrganizerInspector::Closed;
            self.message = "Review this approach again against the current situation.".into();
        }
        if self.inspector != OrganizerInspector::Evidence {
            return;
        }
        // A saved reference remains part of the current draft. Navigation cannot replace it
        // with an older draft selection, nor make an unavailable report into disclosure.
        if route.evidence == EvidenceRoute::Saved {
            self.open_saved_references();
            return;
        }
        self.open_evidence_reports(session.viewed_tick);
        if let Some(id) = route.report {
            if self.body_for(session).is_none()
                || !self.open_evidence_report(id, session.viewed_tick)
            {
                self.message =
                    "That report is unavailable in this observation. Returned to reports.".into();
                return;
            }
        }
        if let EvidenceRoute::Subject(id) = route.evidence {
            if self.selected_report_subject() == Some(id) {
                self.evidence.mode = EvidenceMode::Subject(id);
            } else {
                self.message =
                    "That subject is unavailable in this observation. Returned to reports.".into();
            }
        }
    }
}

#[cfg(test)]
#[path = "navigation_tests.rs"]
mod tests;
