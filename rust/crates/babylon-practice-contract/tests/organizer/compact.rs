//! Compact causal authority: tombstones, learned index and household witness.

use crate::support;
use babylon_kernel::content_digest;
use babylon_practice_contract::{
    OrganizerChoice, OrganizerConfig, OrganizerError, OrganizerMaterialSupport,
    OrganizerPeriodJournal, OrganizerPeriodTimeWitness, OrganizerState, ResolvedOrganizerPeriod,
};
use std::collections::BTreeSet;

#[test]
fn consumed_contact_product_tombstone_survives_creation_receipt_eviction() {
    let config = support::config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let first = support::act(&config, &opening, OrganizerChoice::Hold, 160);
    let product = first.state.contact_products[0].clone();
    assert_eq!(first.journal.receipts.len(), 1);
    let second = support::act(&config, &first, OrganizerChoice::Reinforce, 160);
    // The old product is gone from live state; only its durable tombstone remains.
    assert!(second
        .state
        .consumed_product_ids
        .contains(&product.product_id));
    assert!(!second
        .state
        .contact_products
        .iter()
        .any(|row| row.product_id == product.product_id));
    assert!(!second
        .journal
        .receipts
        .iter()
        .any(|row| row.receipt_id == product.receipt_id));
    // Re-forging the creation row is refused by the tombstone, not by a receipt.
    let mut reforged = second.state.clone();
    reforged.contact_products.push(product.clone());
    assert_eq!(
        babylon_practice_contract::encode_organizer_state(&reforged),
        Err(OrganizerError::InvalidState)
    );
    assert_eq!(
        babylon_practice_contract::consume_organizer_contact_products(&config, &reforged, 3),
        Err(OrganizerError::InvalidState)
    );
    // With no live product, a later consumer cannot renew from the evicted receipt.
    let renewed =
        babylon_practice_contract::consume_organizer_contact_products(&config, &second.state, 3)
            .expect("the live period-product set reduces without the evicted receipt");
    assert!(!renewed
        .agreements
        .iter()
        .any(|row| row.source_product_id == Some(product.product_id)));
    assert!(renewed.contact_products.is_empty());
}

#[test]
fn household_time_witness_refuses_evicted_last_period_hour_partition() {
    let mut config = support::captured_household_config();
    if let babylon_practice_contract::OrganizerTimeBindingMode::Household { bindings } =
        &mut config.time_binding
    {
        for binding in bindings {
            binding.principal_id = [u8::try_from(binding.contributor_id)
                .expect("the fixture identity fits one byte");
                32];
        }
    }
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let resolved = household_period(&config, &opening);
    let witness = resolved
        .state
        .last_period_time_witness
        .as_ref()
        .expect("a household resolution records its exact time partition");
    assert_eq!(witness.period, 1);
    assert!(!witness.contribution_use_ids.is_empty());
    assert_eq!(witness.contribution_use_ids, expected_use_ids(&resolved));
    babylon_practice_contract::validate_organizer_journal(
        &config,
        &resolved.state,
        &support::journal_of(&resolved.journal),
    )
    .expect("the resolved period validates with its exact evidence");
    // Evicting the receipt leaves only the witness; the period must refuse
    // rather than let the same hour be charged again.
    let mut evicted = resolved.journal.clone();
    evicted.receipts.clear();
    assert_eq!(
        babylon_practice_contract::validate_organizer_journal(
            &config,
            &resolved.state,
            &support::journal_of(&evicted)
        ),
        Err(OrganizerError::InvalidState)
    );
    // A witness cannot describe a period later than the current state.
    let mut forged = resolved.state.clone();
    forged.last_period_time_witness = Some(OrganizerPeriodTimeWitness {
        period: 2,
        contribution_use_ids: witness.contribution_use_ids.clone(),
    });
    assert_eq!(
        babylon_practice_contract::validate_organizer_state(&forged),
        Err(OrganizerError::InvalidState)
    );
}

fn household_period(config: &OrganizerConfig, opening: &OrganizerState) -> ResolvedOrganizerPeriod {
    babylon_practice_contract::resolve_organizer_period_with_time(
        config,
        opening,
        &support::facts(1, 160),
        None,
        &crate::aid::time(config, 201, 16),
        OrganizerMaterialSupport {
            aid: &[],
            collection: None,
        },
    )
    .expect("the household period resolves with exact supplies")
}

fn expected_use_ids(resolved: &ResolvedOrganizerPeriod) -> Vec<[u8; 32]> {
    let mut ids = BTreeSet::new();
    for receipt in &resolved.journal.receipts {
        for usage in &receipt.time_use {
            let mut identity = b"babylon.organizer-household-contribution.v1\0".to_vec();
            identity.extend_from_slice(&receipt.receipt_id);
            identity.extend_from_slice(&usage.actor_id.to_be_bytes());
            identity.extend_from_slice(&usage.contributor_id.to_be_bytes());
            ids.insert(content_digest::sha256_of(&identity));
        }
    }
    ids.into_iter().collect()
}

#[test]
fn journal_append_refuses_a_repeated_period() {
    let config = support::config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let first = support::act(&config, &opening, OrganizerChoice::Hold, 160);
    let mut journal = OrganizerPeriodJournal::empty();
    journal
        .append(first.journal.clone())
        .expect("the first period extends an empty window");
    assert_eq!(
        journal.append(first.journal.clone()),
        Err(OrganizerError::PeriodMismatch)
    );
}
