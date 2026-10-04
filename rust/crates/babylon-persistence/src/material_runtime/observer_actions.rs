//! Full-observer semantic proof from public, authenticated accepted intents.
//! Runtime additionally proves consumption against its private command ledger.
use super::MaterialRuntimeError;
use babylon_kernel::{content_digest::sha256_of, replay::ReplaySessionId};
use babylon_practice_contract::{
    admit_organizer, decode_practice_intent, encode_practice_action_id_preimage,
    encode_practice_intent, organizer_action_batch, validate_organizer_pair,
    OrderedPracticeActionBatch, OrganizerChoice, OrganizerCommand, OrganizerConfig, OrganizerState,
    PracticeIntent, MAX_PRACTICE_INTENT_CANONICAL_BYTES, MAX_RESOLVED_PRACTICE_BATCH_ITEMS,
    ORDERED_PRACTICE_ACTION_BATCH_DOMAIN_BYTES,
};

type Result<T> = std::result::Result<T, MaterialRuntimeError>;

pub(super) fn reconstruct(
    config: &OrganizerConfig,
    prior: &OrganizerState,
    current: &OrganizerState,
    session: &ReplaySessionId,
    tick: u64,
    bytes: &[u8],
) -> Result<OrderedPracticeActionBatch> {
    validate_organizer_pair(config, prior).map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?;
    validate_organizer_pair(config, current)
        .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?;
    if current.period != tick {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let mut receipts = current
        .receipts
        .iter()
        .filter(|row| row.actor_id == config.controlled_actor_id && row.period == tick);
    let receipt = receipts
        .next()
        .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    if receipts.next().is_some() || prior.period.checked_add(1) != Some(tick) {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    if receipt.commitment_id.is_none() && receipt.choice != OrganizerChoice::Hold {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let mut accepted = None;
    for intent in parse(session, tick, bytes)? {
        if intent.actor_org_id.to_bytes() != config.controlled_actor_id.to_be_bytes() {
            continue;
        }
        let command = OrganizerCommand {
            campaign_id: config.campaign_id,
            actor_id: config.controlled_actor_id,
            authority_id: intent.input_authority_id.as_bytes(),
            expected_period: intent.submit_after_tick,
            content_digest: intent.quoted_content_digest,
            resource_digest: intent.quoted_resource_contract_digest,
            nonce: intent.proposal_nonce.as_bytes(),
            choice: receipt.choice,
        };
        // Delayed aid has a retimed nonce: date equality alone is never a match.
        if let Ok(commitment) = admit_organizer(config, prior, &command) {
            if Some(commitment.commitment_id) == receipt.commitment_id
                && accepted.replace(commitment).is_some()
            {
                return Err(MaterialRuntimeError::InvalidCheckpoint);
            }
        }
    }
    if accepted.as_ref().map(|row| row.commitment_id) != receipt.commitment_id {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let expected = organizer_action_batch(config, prior, accepted.as_ref(), session.clone())
        .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?;
    if expected.canonical_bytes() != bytes {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    Ok(expected)
}

fn parse(session: &ReplaySessionId, tick: u64, bytes: &[u8]) -> Result<Vec<PracticeIntent>> {
    let session_bytes = session
        .canonical_bytes()
        .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?;
    let maximum = ORDERED_PRACTICE_ACTION_BATCH_DOMAIN_BYTES.len()
        + 1
        + 2
        + session_bytes.len()
        + 8
        + 2
        + MAX_RESOLVED_PRACTICE_BATCH_ITEMS * (36 + MAX_PRACTICE_INTENT_CANONICAL_BYTES);
    if bytes.len() > maximum {
        return Err(MaterialRuntimeError::Bounds);
    }
    let mut input = Cursor(bytes);
    input.equal(ORDERED_PRACTICE_ACTION_BATCH_DOMAIN_BYTES)?;
    input.equal(&[0])?;
    input.equal(&1_u16.to_be_bytes())?;
    input.equal(&session_bytes)?;
    input.equal(&tick.to_be_bytes())?;
    let count = usize::from(input.u16()?);
    if count > MAX_RESOLVED_PRACTICE_BATCH_ITEMS {
        return Err(MaterialRuntimeError::Bounds);
    }
    let mut intents = Vec::new();
    intents
        .try_reserve(count)
        .map_err(|_| MaterialRuntimeError::Bounds)?;
    for ordinal in 0..count {
        if usize::from(input.u16()?) != ordinal {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        let action_id = input.take(32)?;
        let length = usize::from(input.u16()?);
        if length > MAX_PRACTICE_INTENT_CANONICAL_BYTES {
            return Err(MaterialRuntimeError::Bounds);
        }
        let encoded = input.take(length)?;
        let intent =
            decode_practice_intent(encoded).map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?;
        if intent.resolve_tick != tick
            || encode_practice_intent(&intent)
                .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?
                != encoded
        {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        let preimage = encode_practice_action_id_preimage(session, &intent)
            .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?;
        if action_id != sha256_of(&preimage) {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        intents.push(intent);
    }
    if !input.0.is_empty() {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    Ok(intents)
}

struct Cursor<'a>(&'a [u8]);
impl<'a> Cursor<'a> {
    fn take(&mut self, length: usize) -> Result<&'a [u8]> {
        let value = self
            .0
            .get(..length)
            .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
        self.0 = &self.0[length..];
        Ok(value)
    }
    fn equal(&mut self, expected: &[u8]) -> Result<()> {
        if self.take(expected.len())? != expected {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        Ok(())
    }
    fn u16(&mut self) -> Result<u16> {
        Ok(u16::from_be_bytes(
            self.take(2)?
                .try_into()
                .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?,
        ))
    }
}

#[cfg(test)]
mod tests;
