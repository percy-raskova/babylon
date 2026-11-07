//! Presentation derived solely from the admitted organizer projection.

use babylon_persistence::runtime_session::{
    OrganizerBodyDisclosure, OrganizerPosition, OrganizerView,
};
#[cfg(test)]
use babylon_persistence::ArchiveEvidenceClass;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum OrganizerSubject {
    Collective(u64),
    AidPartner(u64),
    Contributor(u64),
    WorkplaceCommittee(u64),
    NeighborhoodGroup(u64),
    Workplace(u64),
}

impl OrganizerSubject {
    pub(super) fn report_subject(self, view: &OrganizerView) -> Option<u64> {
        match self {
            Self::Workplace(id) if id == view.workplace_id => Some(id),
            Self::WorkplaceCommittee(id) if id == view.workplace_partner_id => {
                Some(view.workplace_id)
            }
            Self::AidPartner(id) if view.aid_partners.iter().any(|p| p.actor_id == id) => Some(id),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum OrganizerSceneMode {
    #[default]
    Places,
    Relationships,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct SceneNode {
    pub subject: OrganizerSubject,
    pub label: String,
}

impl SceneNode {
    pub fn caption(&self) -> String {
        let kind = match self.subject {
            OrganizerSubject::Collective(_) => "Collective",
            OrganizerSubject::AidPartner(_) => "Aid partner",
            OrganizerSubject::Contributor(_) => "Contributor",
            OrganizerSubject::WorkplaceCommittee(_) => "Workplace committee",
            OrganizerSubject::NeighborhoodGroup(_) => "Neighborhood group",
            OrganizerSubject::Workplace(_) => "Workplace",
        };
        format!("{kind} · {}", self.label)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum RelationKind {
    Agreement,
    RoutineContact,
    EarnedContact,
    BodyIncidence,
}

impl RelationKind {
    pub fn marker(self) -> &'static str {
        match self {
            Self::Agreement => "A",
            Self::RoutineContact => "R",
            Self::EarnedContact => "E",
            Self::BodyIncidence => "B",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct SceneRelation {
    pub from: OrganizerSubject,
    pub to: OrganizerSubject,
    pub kind: RelationKind,
    pub label: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum BodyShape {
    Halo,
    Capsule,
    Membrane,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct OrganizerScene {
    pub nodes: Vec<SceneNode>,
    pub relations: Vec<SceneRelation>,
    pub body_shape: Option<BodyShape>,
    pub body_members: Vec<OrganizerSubject>,
    pub body_status: String,
}

fn ordered_positions(view: &OrganizerView) -> Vec<&OrganizerPosition> {
    let mut positions = view.positions.iter().collect::<Vec<_>>();
    positions.sort_by_key(|position| position.contributor_id);
    positions.dedup_by_key(|position| position.contributor_id);
    positions
}

fn subjects(view: &OrganizerView) -> Vec<SceneNode> {
    let collective = OrganizerSubject::Collective(view.actor_id);
    let committee = OrganizerSubject::WorkplaceCommittee(view.workplace_partner_id);
    let neighborhood = OrganizerSubject::NeighborhoodGroup(view.neighborhood_partner_id);
    let workplace = OrganizerSubject::Workplace(view.workplace_id);
    let mut nodes = vec![
        SceneNode {
            subject: collective,
            label: view.organization_label.clone(),
        },
        SceneNode {
            subject: committee,
            label: view.workplace_partner_label.clone(),
        },
        SceneNode {
            subject: neighborhood,
            label: view.neighborhood_partner_label.clone(),
        },
        SceneNode {
            subject: workplace,
            label: view.workplace_label.clone(),
        },
    ];
    nodes.extend(view.aid_partners.iter().map(|p| SceneNode {
        subject: OrganizerSubject::AidPartner(p.actor_id),
        label: p.label.clone(),
    }));
    let positions = ordered_positions(view);
    nodes.extend(positions.iter().map(|position| SceneNode {
        subject: OrganizerSubject::Contributor(position.contributor_id),
        label: position.label.clone(),
    }));
    nodes
}

impl OrganizerScene {
    pub fn from_disclosure(view: &OrganizerView, body: &OrganizerBodyDisclosure) -> Self {
        let collective = OrganizerSubject::Collective(view.actor_id);
        let committee = OrganizerSubject::WorkplaceCommittee(view.workplace_partner_id);
        let neighborhood = OrganizerSubject::NeighborhoodGroup(view.neighborhood_partner_id);
        let nodes = subjects(view);
        let positions = ordered_positions(view);
        let partner = |id| {
            if id == view.workplace_partner_id {
                Some(committee)
            } else if id == view.neighborhood_partner_id {
                Some(neighborhood)
            } else {
                None
            }
        };
        let mut relations = Vec::new();
        for agreement in &view.agreements {
            if agreement.actor_id == view.actor_id {
                if let Some(to) = partner(agreement.partner_actor_id) {
                    relations.push(SceneRelation {
                        from: collective,
                        to,
                        kind: RelationKind::Agreement,
                        label: format!(
                            "Agreement · periods {}–{}",
                            agreement.valid_from_period, agreement.valid_through_period
                        ),
                    });
                }
            }
        }
        if view.standing.authorized {
            if let Some(to) = partner(view.standing.partner_actor_id) {
                relations.push(SceneRelation {
                    from: collective,
                    to,
                    kind: RelationKind::RoutineContact,
                    label: "Authorized routine contact".into(),
                });
            }
        }
        for receipt in &view.receipts {
            if receipt.actor_id == view.actor_id
                && receipt.period > 0
                && receipt.period <= view.period
                && receipt.contact_product_id.is_some()
            {
                if let Some(to) = receipt.partner_actor_id.and_then(partner) {
                    relations.push(SceneRelation {
                        from: collective,
                        to,
                        kind: RelationKind::EarnedContact,
                        label: format!("Earned contact · period {}", receipt.period),
                    });
                }
            }
        }
        let (body_shape, body_members, body_status) = match body {
            OrganizerBodyDisclosure::Unavailable => {
                (None, vec![], "Collective structure unknown".into())
            }
            OrganizerBodyDisclosure::KnownAbsent => (
                None,
                vec![],
                "No shared collective structure recorded".into(),
            ),
            OrganizerBodyDisclosure::Partial(part) => {
                let mut members = vec![collective];
                for position in positions {
                    if part.contributors.contains(&position.contributor_id) {
                        let contributor = OrganizerSubject::Contributor(position.contributor_id);
                        members.push(contributor);
                        relations.push(SceneRelation {
                            from: collective,
                            to: contributor,
                            kind: RelationKind::BodyIncidence,
                            label: "Contributor link".into(),
                        });
                    }
                }
                let shape = match members.len() {
                    1 => BodyShape::Halo,
                    2 => BodyShape::Capsule,
                    _ => BodyShape::Membrane,
                };
                (
                    Some(shape),
                    members,
                    "Partial view of our collective · further links unknown".into(),
                )
            }
        };
        relations.sort_by(|a, b| (a.from, a.to, &a.label).cmp(&(b.from, b.to, &b.label)));
        Self {
            nodes,
            relations,
            body_shape,
            body_members,
            body_status,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::runtime_session::{
        OrganizerBodyDisclosure, OrganizerPauseReason, OrganizerStandingWork, OrganizerView,
    };

    fn view() -> OrganizerView {
        OrganizerView {
            period: 0,
            actor_id: 1,
            authority_id: [1; 16],
            organization_label: "Collective".into(),
            workplace_id: 2,
            workplace_label: "Workplace".into(),
            workplace_partner_id: 3,
            workplace_partner_label: "Committee".into(),
            neighborhood_partner_id: 4,
            neighborhood_partner_label: "Neighborhood".into(),
            available_hours: 2,
            inquiry_hours: 2,
            contact_hours: 2,
            public_workplace_contact: false,
            content_digest: [2; 32],
            resource_digest: [3; 32],
            standing: OrganizerStandingWork {
                partner_actor_id: 4,
                authorized: false,
                paused_reason: Some(OrganizerPauseReason::Explicit),
            },
            agreements: vec![],
            total_observation_count: 0,
            observations: vec![],
            total_receipt_count: 0,
            receipts: vec![],
            positions: vec![],
            aid_partners: vec![],
            aid_options: vec![],
        }
    }

    #[test]
    fn scene_uses_only_disclosed_inputs() {
        let view = view();
        let scene = OrganizerScene::from_disclosure(&view, &OrganizerBodyDisclosure::Unavailable);
        assert_eq!(
            scene,
            OrganizerScene::from_disclosure(&view, &OrganizerBodyDisclosure::Unavailable)
        );
        assert!(scene.body_shape.is_none());
        assert_eq!(scene.body_status, "Collective structure unknown");
        assert!(!scene
            .relations
            .iter()
            .any(|relation| relation.label.contains("receipt")));
    }
    #[test]
    fn scene_body_shapes_are_disclosed_partial_incidence() {
        use babylon_persistence::runtime_session::{OrganizerBodyPart, OrganizerPosition};
        let mut view = view();
        let mut part = OrganizerBodyPart {
            runtime_hyperedge_id: 1,
            scenario: "national".into(),
            local_name: "body".into(),
            contributors: vec![],
            evidence_class: ArchiveEvidenceClass::Designed,
        };
        let scene =
            OrganizerScene::from_disclosure(&view, &OrganizerBodyDisclosure::Partial(part.clone()));
        assert_eq!(scene.body_shape, Some(BodyShape::Halo));
        assert_eq!(scene.body_members, vec![OrganizerSubject::Collective(1)]);
        for id in [1, 7] {
            view.positions.push(OrganizerPosition {
                contributor_id: id,
                label: format!("Contributor {id}"),
                promised_hours: 1,
                concern: String::new(),
                objection: String::new(),
                review_condition: String::new(),
            });
            part.contributors.push(id);
            let actual = OrganizerScene::from_disclosure(
                &view,
                &OrganizerBodyDisclosure::Partial(part.clone()),
            );
            assert_eq!(
                actual.body_shape,
                Some(if id == 1 {
                    BodyShape::Capsule
                } else {
                    BodyShape::Membrane
                })
            );
            assert!(actual.body_status.contains("Partial"));
            assert!(actual
                .relations
                .iter()
                .any(|relation| relation.label == "Contributor link"));
            assert_ne!(
                OrganizerSubject::Collective(1),
                OrganizerSubject::Contributor(1)
            );
        }
        let actual =
            OrganizerScene::from_disclosure(&view, &OrganizerBodyDisclosure::Partial(part.clone()));
        part.runtime_hyperedge_id = 99;
        part.contributors.push(999);
        assert_eq!(
            actual,
            OrganizerScene::from_disclosure(&view, &OrganizerBodyDisclosure::Partial(part))
        );
    }
    #[test]
    fn scene_distinguishes_agreement_routine_and_earned_contact() {
        use babylon_persistence::runtime_session::{
            OrganizerAgreement, OrganizerChoice, OrganizerOutcome, OrganizerPartnerResponse,
            OrganizerReceipt,
        };
        let mut view = view();
        view.period = 1;
        view.standing.authorized = true;
        view.agreements.push(OrganizerAgreement {
            actor_id: 1,
            partner_actor_id: 3,
            valid_from_period: 0,
            valid_through_period: 1,
            source_product_id: None,
        });
        view.receipts.push(OrganizerReceipt {
            receipt_id: [1; 32],
            commitment_id: Some([2; 32]),
            actor_id: 1,
            period: 1,
            choice: OrganizerChoice::Reinforce,
            standing_work: false,
            outcome: OrganizerOutcome::ContactCompleted,
            hours_spent: 2,
            partner_actor_id: Some(3),
            partner_response: OrganizerPartnerResponse::Participated,
            observation_ids: vec![],
            contact_product_id: Some([3; 32]),
            time_use: vec![],
        });
        let scene = OrganizerScene::from_disclosure(&view, &OrganizerBodyDisclosure::Unavailable);
        let labels = scene
            .relations
            .iter()
            .map(|relation| relation.label.as_str())
            .collect::<Vec<_>>();
        assert!(labels.iter().any(|label| label.starts_with("Agreement")));
        assert!(labels.contains(&"Authorized routine contact"));
        assert!(labels.contains(&"Earned contact · period 1"));
        for (label, kind) in [
            ("Authorized routine contact", RelationKind::RoutineContact),
            ("Earned contact · period 1", RelationKind::EarnedContact),
        ] {
            assert!(scene
                .relations
                .iter()
                .any(|relation| relation.label == label && relation.kind == kind));
        }
        assert!(scene
            .relations
            .iter()
            .any(|relation| relation.label.starts_with("Agreement")
                && relation.kind == RelationKind::Agreement));
        view.period = 0;
        assert!(
            !OrganizerScene::from_disclosure(&view, &OrganizerBodyDisclosure::Unavailable)
                .relations
                .iter()
                .any(|relation| relation.label.starts_with("Earned contact"))
        );
    }
}
