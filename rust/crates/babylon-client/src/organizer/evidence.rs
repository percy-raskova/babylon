//! Personal report references resolved only through the current lawful projection.

use babylon_persistence::runtime_session::OrganizerObservation;

use crate::observer::{ObserverSession, SessionPhase};

use super::{draft::MAX_EVIDENCE_REFERENCES, OrganizerClient};

#[derive(Clone, Copy, Default, PartialEq, Eq)]
pub(super) enum EvidenceMode {
    #[default]
    Reports,
    Saved,
}

#[derive(Default)]
pub(super) struct EvidenceInspection {
    pub mode: EvidenceMode,
    selected_report: Option<[u8; 32]>,
}

impl OrganizerClient {
    pub(super) fn lawful_evidence(
        &self,
        id: [u8; 32],
        period: u64,
    ) -> Option<&OrganizerObservation> {
        let view = self.view.as_ref()?;
        view.observations.iter().find(|item| {
            item.observation_id == id
                && item.actor_id == view.actor_id
                && item.subject_id == view.workplace_id
                && item.observed_period <= period
                && item.acquired_period <= period
        })
    }

    pub(super) fn evidence_ids(&self, period: u64) -> Vec<[u8; 32]> {
        if self.evidence.mode == EvidenceMode::Saved {
            return self
                .draft
                .as_ref()
                .map_or_else(Vec::new, |draft| draft.references.clone());
        }
        let Some(view) = &self.view else {
            return Vec::new();
        };
        let mut reports = view
            .observations
            .iter()
            .filter(|item| {
                item.actor_id == view.actor_id
                    && item.subject_id == view.workplace_id
                    && item.observed_period <= period
                    && item.acquired_period <= period
            })
            .collect::<Vec<_>>();
        reports.sort_by_key(|item| {
            (
                item.observed_period,
                item.acquired_period,
                item.observation_id,
            )
        });
        reports
            .into_iter()
            .rev()
            .map(|item| item.observation_id)
            .collect()
    }

    pub(super) fn selected_evidence_id(&self, period: u64) -> Option<[u8; 32]> {
        match self.evidence.mode {
            EvidenceMode::Reports => self
                .evidence
                .selected_report
                .or_else(|| self.evidence_ids(period).first().copied()),
            EvidenceMode::Saved => self.draft.as_ref()?.selected_reference,
        }
    }

    pub(super) fn open_evidence_reports(&mut self, period: u64) {
        self.evidence.mode = EvidenceMode::Reports;
        if self.evidence.selected_report.is_none() {
            self.evidence.selected_report = self.evidence_ids(period).first().copied();
        }
    }

    pub(super) fn open_saved_references(&mut self) {
        self.evidence.mode = EvidenceMode::Saved;
    }

    pub(super) fn evidence_neighbor(&self, next: bool, period: u64) -> Option<[u8; 32]> {
        let ids = self.evidence_ids(period);
        let index = self
            .selected_evidence_id(period)
            .and_then(|id| ids.iter().position(|item| *item == id));
        let index = match (next, index) {
            (true, Some(index)) => index.checked_add(1)?,
            (false, Some(index)) => index.checked_sub(1)?,
            (true, None) => 0,
            (false, None) => return None,
        };
        ids.get(index).copied()
    }

    pub(super) fn move_evidence(&mut self, next: bool, period: u64, now: f64) {
        let Some(id) = self.evidence_neighbor(next, period) else {
            return;
        };
        match self.evidence.mode {
            EvidenceMode::Reports => self.evidence.selected_report = Some(id),
            EvidenceMode::Saved => {
                if let Some(draft) = &mut self.draft {
                    draft.selected_reference = Some(id);
                    self.dirty(now);
                }
            }
        }
    }

    pub(super) fn evidence_is_saved(&self, id: [u8; 32]) -> bool {
        self.draft
            .as_ref()
            .is_some_and(|draft| draft.references.contains(&id))
    }

    fn reference_scope(&self, session: &ObserverSession) -> Result<(), &'static str> {
        let Some(view) = &self.view else {
            return Err("Wait for the committed workplace report.");
        };
        if self.campaign != Some(*session.campaign.as_uuid())
            || view.period != session.durable_tick
            || !matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
            || self
                .draft
                .as_ref()
                .is_none_or(|draft| draft.workplace_id != view.workplace_id)
        {
            return Err("This reference is unavailable in the current campaign view.");
        }
        if !self.draft_writable {
            return Err("The personal draft cannot be saved; its original file remains retained.");
        }
        Ok(())
    }

    pub(super) fn can_keep_evidence(
        &self,
        session: &ObserverSession,
    ) -> Result<[u8; 32], &'static str> {
        self.reference_scope(session)?;
        let id = self
            .selected_evidence_id(session.viewed_tick)
            .filter(|id| self.lawful_evidence(*id, session.viewed_tick).is_some())
            .ok_or("This report is unavailable in this inspected view.")?;
        let draft = self
            .draft
            .as_ref()
            .ok_or("Personal draft is unavailable.")?;
        if draft.references.contains(&id) {
            return Err("This report is already saved in the personal draft.");
        }
        if draft.references.len() >= MAX_EVIDENCE_REFERENCES {
            return Err(
                "The personal draft holds 32 references. Remove one before adding another.",
            );
        }
        Ok(id)
    }

    pub(super) fn keep_evidence(
        &mut self,
        session: &ObserverSession,
        now: f64,
    ) -> Result<(), &'static str> {
        let id = self.can_keep_evidence(session)?;
        let draft = self
            .draft
            .as_mut()
            .ok_or("Personal draft is unavailable.")?;
        draft.references.push(id);
        draft.selected_reference = Some(id);
        self.dirty(now);
        Ok(())
    }

    pub(super) fn can_remove_reference(
        &self,
        session: &ObserverSession,
    ) -> Result<[u8; 32], &'static str> {
        self.reference_scope(session)?;
        self.selected_evidence_id(session.viewed_tick)
            .filter(|id| self.evidence_is_saved(*id))
            .ok_or("No saved reference is selected.")
    }

    pub(super) fn remove_reference(
        &mut self,
        session: &ObserverSession,
        now: f64,
    ) -> Result<(), &'static str> {
        let id = self.can_remove_reference(session)?;
        let draft = self
            .draft
            .as_mut()
            .ok_or("Personal draft is unavailable.")?;
        draft.references.retain(|item| *item != id);
        if draft.selected_reference == Some(id) {
            draft.selected_reference = draft.references.first().copied();
        }
        self.dirty(now);
        Ok(())
    }
}
