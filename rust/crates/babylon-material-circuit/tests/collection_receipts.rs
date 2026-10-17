//! Independent actual/refusal row and outcome-tag contracts.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    collection_contribution_id, CollectionOutcome, CollectionReceipt, FinalDemandPrincipalId,
    MaterialCircuitError, OrganizationAccountId, UnitId,
};

fn partial() -> CollectionReceipt {
    let mut row = CollectionReceipt {
        period: 1,
        admitted_period: 0,
        original_commitment_id: [1; 32],
        command_nonce: [2; 16],
        mandate_id: [3; 32],
        source_hash: [4; 32],
        actor_id: 101,
        contributor_id: 201,
        donor: FinalDemandPrincipalId::from_bytes([5; 32]),
        recipient: OrganizationAccountId::from_bytes([6; 32]),
        labor_unit_id: UnitId::from_bytes([7; 32]),
        requested: Currency::from_micro_units(8),
        collected: Currency::from_micro_units(4),
        performed_hours: 2,
        outcome: CollectionOutcome::PartiallyCollected,
        transfer_ordinal: Some(3),
        contribution_use_id: [0; 32],
    };
    row.contribution_use_id = collection_contribution_id(
        row.original_commitment_id,
        row.mandate_id,
        row.period,
        row.actor_id,
        row.contributor_id,
        row.donor,
        row.labor_unit_id,
    );
    row
}

#[test]
fn actual_partial_row_requires_positive_subcap_amount_and_one_identified_time_use() {
    let row = partial();
    row.validate().unwrap();
    assert_eq!(row.contribution_use().unwrap().hours, 2);
    assert_eq!(CollectionOutcome::try_from(9).unwrap(), row.outcome);
    for kind in 0..8 {
        let mut changed = row.clone();
        match kind {
            0 => changed.collected = Currency::from_micro_units(0),
            1 => changed.collected = Currency::from_micro_units(-1),
            2 => changed.collected = changed.requested,
            3 => changed.collected = Currency::from_micro_units(9),
            4 => changed.performed_hours = 0,
            5 => changed.transfer_ordinal = None,
            6 => changed.transfer_ordinal = Some(u32::MAX),
            _ => changed.contribution_use_id = [0; 32],
        }
        assert_eq!(
            changed.validate(),
            Err(MaterialCircuitError::CollectionInvariant)
        );
    }
    for tag in [0, 10, 255] {
        assert_eq!(
            CollectionOutcome::try_from(tag),
            Err(MaterialCircuitError::CollectionInvariant)
        );
    }
}

#[test]
fn full_and_refused_rows_retain_their_existing_tags_and_quantity_contracts() {
    let mut full = partial();
    full.outcome = CollectionOutcome::Collected;
    full.collected = full.requested;
    full.validate().unwrap();
    assert_eq!(full.outcome as u8, 1);
    full.collected = Currency::from_micro_units(4);
    assert!(full.validate().is_err());
    let mut refusal = partial();
    refusal.outcome = CollectionOutcome::InsufficientCash;
    refusal.collected = Currency::from_micro_units(0);
    refusal.performed_hours = 0;
    refusal.transfer_ordinal = None;
    refusal.contribution_use_id = [0; 32];
    refusal.validate().unwrap();
    assert_eq!(refusal.outcome as u8, 7);
    assert!(refusal.contribution_use().is_none());
    refusal.collected = Currency::from_micro_units(1);
    assert!(refusal.validate().is_err());
}
