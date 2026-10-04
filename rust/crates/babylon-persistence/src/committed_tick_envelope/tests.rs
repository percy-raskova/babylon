use super::*;
fn row(key: u8, payload: u8) -> CommittedTickRow {
    CommittedTickRow::compose(vec![key], vec![payload]).expect("bounded canonical row")
}
fn singleton_families(payload: u8) -> CommittedTickRowFamilies {
    CommittedTickRowFamilies {
        graph: vec![row(0x01, payload)],
        state: vec![row(0x02, payload)],
        event: vec![row(0x03, payload)],
        choice_receipt: vec![row(0x04, payload)],
        checkpoint: vec![row(0x05, payload)],
        archive_dirty_receipt: row(0x06, payload),
    }
}
#[test]
fn row_keys_are_nonempty_unique_and_strictly_ordered_in_choice_family() {
    assert!(matches!(
        CommittedTickRow::compose(Vec::new(), vec![1]),
        Err(CommittedTickEnvelopeError::EmptyRowKey)
    ));

    let mut duplicate = singleton_families(1);
    duplicate.choice_receipt = vec![row(1, 1), row(1, 2)];
    assert!(matches!(
        compose_row_families(duplicate),
        Err(CommittedTickEnvelopeError::DuplicateRowKey {
            family: CommittedTickRowFamily::ChoiceReceipt,
            ..
        })
    ));

    let mut descending = singleton_families(1);
    descending.choice_receipt = vec![row(2, 1), row(1, 2)];
    assert!(matches!(
        compose_row_families(descending),
        Err(CommittedTickEnvelopeError::RowOrder {
            family: CommittedTickRowFamily::ChoiceReceipt,
            ..
        })
    ));
}
#[test]
fn cumulative_bounds_cover_six_families_and_singular_archive() {
    let ceilings = ALL_COMMITTED_TICK_ROW_FAMILIES.map(CommittedTickRowFamily::maximum_body_bytes);
    assert_eq!(
        ceilings,
        [
            134_217_728,
            67_108_864,
            67_108_864,
            67_108_864,
            67_108_864,
            67_108_864
        ]
    );
    assert_eq!(
        validate_committed_tick_envelope_bounds([1; 6], ceilings)
            .expect("each independent byte maximum"),
        MAX_COMMITTED_COMPONENT_BODY_BYTES
    );
    for (index, family) in ALL_COMMITTED_TICK_ROW_FAMILIES.into_iter().enumerate() {
        let mut oversized = ceilings;
        oversized[index] += 1;
        assert_eq!(
            validate_committed_tick_envelope_bounds([1; 6], oversized),
            Err(CommittedTickEnvelopeError::BatchBytes {
                family,
                actual: ceilings[index] + 1,
                maximum: ceilings[index]
            })
        );
    }

    let mut maximum_rows = [0_usize; 6];
    maximum_rows[0] = MAX_COMMITTED_TICK_ROWS - 1;
    maximum_rows[5] = 1;
    let mut minimum_bodies = [0_usize; 6];
    minimum_bodies[0] = (MAX_COMMITTED_TICK_ROWS - 1) * 9;
    minimum_bodies[5] = 9;
    assert!(validate_committed_tick_envelope_bounds(maximum_rows, minimum_bodies).is_ok());
    maximum_rows[3] = 1;
    minimum_bodies[3] = 9;
    assert!(matches!(
        validate_committed_tick_envelope_bounds(maximum_rows, minimum_bodies),
        Err(CommittedTickEnvelopeError::AggregateRows { .. })
    ));

    assert!(matches!(
        validate_committed_tick_envelope_bounds([2, 0, 0, 0, 0, 1], [9, 0, 0, 0, 0, 9]),
        Err(CommittedTickEnvelopeError::BatchShape {
            family: CommittedTickRowFamily::Graph,
            ..
        })
    ));
    assert!(matches!(
        validate_committed_tick_envelope_bounds([0; 6], [0; 6]),
        Err(CommittedTickEnvelopeError::MissingArchiveDirtyReceipt)
    ));
    assert!(matches!(
        validate_committed_tick_envelope_bounds([0, 0, 0, 0, 0, 2], [0, 0, 0, 0, 0, 18]),
        Err(CommittedTickEnvelopeError::DuplicateArchiveDirtyReceipt { actual: 2 })
    ));
}
