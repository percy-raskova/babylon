use super::*;
use crate::michigan_content::MichiganContentPreset;
use babylon_practice_contract::OrderedPracticeActionBatch;

fn opening(preset: MichiganContentPreset) -> crate::material_runtime::MaterialRuntimeFoundation {
    preset
        .create_foundation(&crate::test_support::catalog())
        .unwrap()
}
fn admit_delta(lookup: &TypedLookup, delta: &[IdentityEntry]) -> TypedLookup {
    let mut entries = lookup.entries().to_vec();
    entries.extend_from_slice(delta);
    TypedLookup::from_entries(entries).unwrap()
}
#[test]
fn current_tick_reconstructs_exact_canonical_register_without_current_input() {
    let foundation = opening(MichiganContentPreset::FourWeekStandard);
    let base = foundation.initial_register().canonical_bytes().to_vec();
    let authority = OpeningRegister::from_canonical(&base).unwrap();
    let lookup = authority.lookup().clone();
    let session = foundation.into_session().unwrap();
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 1)
            .unwrap();
    let candidate = session.prepare_advance(&actions).unwrap();
    let current = candidate.material().register().canonical_bytes();
    let admitted_current = MaterialWorldRegister::decode(current).unwrap();
    let encoded = encode_register_with_opening(&authority, &admitted_current, &lookup).unwrap();
    let updated = admit_delta(&lookup, &encoded.lookup_delta);
    assert_eq!(
        decode_admitted(&authority, &encoded.package, &updated, [0; 32])
            .unwrap()
            .0,
        current
    );
    assert_eq!(
        encoded.package,
        encode_register_with_opening(&authority, &admitted_current, &lookup)
            .unwrap()
            .package
    );
    // Later receipt ownership must not change an earlier state prefix binding.
    let mut later = updated;
    later.intern(IdentityKind::Contribution, [231; 32]).unwrap();
    assert_eq!(
        decode_admitted(&authority, &encoded.package, &later, [0; 32])
            .unwrap()
            .0,
        current
    );
}
#[test]
fn current_organizer_bytes_are_retained_instead_of_assuming_empty_trailer() {
    let foundation = opening(MichiganContentPreset::FourWeekStandard);
    let defines = crate::michigan_defines::MichiganDefines::parse(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .unwrap();
    let register = foundation.initial_register().clone();
    let config = crate::organizer_content::config(
        crate::identity::CampaignId::from_uuid(uuid::Uuid::from_u128(719)),
        &defines.organizer,
        register.state().process_outputs[0].process_id.as_bytes(),
    )
    .unwrap();
    let organizer = babylon_practice_contract::initial_organizer_state(&config).unwrap();
    let register = register.with_organizer(config, organizer).unwrap();
    let base = register.canonical_bytes();
    assert!(register.organizer_config().is_some());
    let authority = OpeningRegister::from_canonical(base).unwrap();
    let lookup = authority.lookup().clone();
    let admitted_current = MaterialWorldRegister::decode(base).unwrap();
    let encoded = encode_register_with_opening(&authority, &admitted_current, &lookup).unwrap();
    assert_eq!(
        decode_admitted(&authority, &encoded.package, &lookup, [0; 32])
            .unwrap()
            .0,
        base
    );
    let trailer = sections(base).unwrap().pop().unwrap();
    assert!(trailer.end - trailer.start > 1);
}
#[test]
fn wrong_base_damaged_package_and_trailing_bytes_refuse() {
    let foundation = opening(MichiganContentPreset::FourWeekStandard);
    let base = foundation.initial_register().canonical_bytes();
    let authority = OpeningRegister::from_canonical(base).unwrap();
    let lookup = authority.lookup().clone();
    let admitted_current = MaterialWorldRegister::decode(base).unwrap();
    let encoded = encode_register_with_opening(&authority, &admitted_current, &lookup).unwrap();
    let mut damaged = encoded.package.clone();
    damaged[DOMAIN.len()] ^= 1;
    assert_eq!(
        decode_admitted(&authority, &damaged, &lookup, [0; 32]),
        Err(StorageError::ParentMismatch)
    );
    let mut trailing = encoded.package.clone();
    trailing.push(0);
    assert_eq!(
        decode_admitted(&authority, &trailing, &lookup, [0; 32]),
        Err(StorageError::Trailing)
    );
    let mut future = encoded.package;
    future[0] ^= 1;
    assert_eq!(
        decode_admitted(&authority, &future, &lookup, [0; 32]),
        Err(StorageError::Version)
    );
}
#[test]
fn typed_lookup_does_not_alias_equal_bytes_across_identity_domains() {
    let mut lookup = TypedLookup::default();
    let bytes = [0; 32];
    let site = lookup.intern(IdentityKind::Site, bytes).unwrap();
    let good = lookup.intern(IdentityKind::Good, bytes).unwrap();
    assert_ne!(site, good);
    assert_eq!(lookup.intern(IdentityKind::Site, bytes).unwrap(), site);
    assert_eq!(
        lookup.resolve(site, IdentityKind::Good),
        Err(StorageError::IdentityKind)
    );
    assert_eq!(
        lookup.resolve(u32::MAX, IdentityKind::Site),
        Err(StorageError::LookupIndex)
    );
    let packed = encode_lookup(lookup.entries()).unwrap();
    assert_eq!(packed.len(), 70);
    assert_eq!(&packed[..4], &2_u32.to_be_bytes());
    assert_eq!(packed[4], IdentityKind::Site as u8);
    assert_eq!(&packed[5..37], bytes);
    assert_eq!(packed[37], IdentityKind::Good as u8);
    assert_eq!(&packed[38..70], bytes);
}
#[test]
fn typed_lookup_refuses_unknown_tags_and_duplicates() {
    let entry = IdentityEntry {
        kind: IdentityKind::Site,
        bytes: [7; 32],
    };
    assert!(matches!(
        TypedLookup::from_entries(vec![entry, entry]),
        Err(StorageError::DuplicateIdentity)
    ));
    assert_eq!(IdentityKind::from_tag(255), Err(StorageError::IdentityKind));
}
#[test]
fn account_and_equipment_variants_use_their_own_typed_domain() {
    for (tag, expected) in [
        (1, IdentityKind::Site),
        (2, IdentityKind::FinalDemandPrincipal),
        (3, IdentityKind::OrganizationAccount),
        (4, IdentityKind::PublicAccount),
    ] {
        let mut raw = 1_u32.to_be_bytes().to_vec();
        raw.push(tag);
        raw.extend_from_slice(&[19; 32]);
        raw.extend_from_slice(&(-43_i128).to_be_bytes());
        let shape = layout(24).unwrap();
        let mut lookup = TypedLookup::default();
        let normalized = normalize(&raw, shape, &mut lookup, true).unwrap();
        assert_eq!(lookup.entries()[0].kind, expected);
        assert_eq!(
            expand(&normalized.bytes, 1, shape, &lookup, lookup.entries().len()).unwrap(),
            raw
        );
    }
    let field = layout(43).unwrap().fields[0];
    assert_eq!(kind(field, &[0]).unwrap(), IdentityKind::Installation);
    assert_eq!(kind(field, &[1]).unwrap(), IdentityKind::EquipmentCohort);
    assert_eq!(kind(field, &[2]), Err(StorageError::IdentityKind));
}
#[test]
fn xor_restores_exact_numeric_bytes_but_refuses_changed_identity_rows() {
    let shape = layout(10).unwrap();
    let mut old = 1_u32.to_be_bytes().to_vec();
    old.extend_from_slice(&[7; 32]);
    old.extend_from_slice(&[9; 32]);
    old.extend_from_slice(&[11; 32]);
    old.extend_from_slice(&42_u64.to_be_bytes());
    let mut current = old.clone();
    current[107] = 43;
    let mut lookup = TypedLookup::default();
    let prior = normalize(&old, shape, &mut lookup, true).unwrap();
    let next = normalize(&current, shape, &mut lookup, true).unwrap();
    let xor = next
        .bytes
        .iter()
        .zip(&prior.bytes)
        .map(|(a, b)| a ^ b)
        .collect::<Vec<_>>();
    let block = compressed(
        3,
        columns(&xor, 1, normalized_width(shape).unwrap()).unwrap(),
    )
    .unwrap();
    let stored = StoredSection {
        id: 10,
        mode: 3,
        count: Some(1),
        raw_length: current.len(),
        raw_digest: digest(&current),
        body_length: block.body_length,
        body_digest: block.body_digest,
        encoded: block.encoded,
    };
    let section = Section {
        id: 10,
        start: 0,
        end: old.len(),
        count: Some(1),
    };
    assert_eq!(
        restore_section(
            &stored,
            Some((&section, &old)),
            &lookup,
            lookup.entries().len()
        )
        .unwrap(),
        current
    );
    let mut changed_key = current.clone();
    changed_key[4] = 8;
    let changed = normalize(&changed_key, shape, &mut lookup, true).unwrap();
    let xor = changed
        .bytes
        .iter()
        .zip(&prior.bytes)
        .map(|(a, b)| a ^ b)
        .collect::<Vec<_>>();
    let block = compressed(
        3,
        columns(&xor, 1, normalized_width(shape).unwrap()).unwrap(),
    )
    .unwrap();
    let changed_stored = StoredSection {
        id: 10,
        mode: 3,
        count: Some(1),
        raw_length: changed_key.len(),
        raw_digest: digest(&changed_key),
        body_length: block.body_length,
        body_digest: block.body_digest,
        encoded: block.encoded,
    };
    assert_eq!(
        restore_section(
            &changed_stored,
            Some((&section, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Layout)
    );
    let mut malformed = stored;
    malformed.body_length += 1;
    assert_eq!(
        restore_section(
            &malformed,
            Some((&section, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Layout)
    );
}
#[test]
fn compiled_layouts_include_all_empty_family_identity_fields() {
    for (id, width) in [(41, 81), (71, 282), (72, 169)] {
        assert_eq!(layout(id).unwrap().width, width);
    }
    let mut lookup = TypedLookup::default();
    let mandate = lookup.intern(IdentityKind::AidMandate, [17; 32]).unwrap();
    let order = lookup.intern(IdentityKind::Order, [17; 32]).unwrap();
    assert_ne!(mandate, order);
    assert_eq!(
        IdentityKind::from_tag(20).unwrap(),
        IdentityKind::AidMandate
    );
    assert_eq!(
        lookup.resolve(mandate, IdentityKind::AidMandate).unwrap(),
        [17; 32]
    );
    assert_eq!(
        lookup.resolve(mandate, IdentityKind::Order),
        Err(StorageError::IdentityKind)
    );
    let encoded = encode_lookup(lookup.entries()).unwrap();
    assert_eq!(encoded.len(), 70);
    assert_eq!(&encoded[..4], &2_u32.to_be_bytes());
    assert_eq!(encoded[4], 20);
    assert_eq!(&encoded[5..37], [17; 32]);
    assert_eq!(encoded[37], IdentityKind::Order as u8);
    assert_eq!(&encoded[38..70], [17; 32]);
    for id in [21, 26, 41, 50, 54, 61, 65, 67, 68, 71, 72] {
        let shape = layout(id).unwrap();
        assert!(!shape.fields.is_empty());
        assert!(shape
            .fields
            .iter()
            .all(|field| field.offset + 32 <= shape.width));
    }
}

#[test]
fn raw_byte_admission_refuses_malformed_opening_and_current_before_typed_encoding() {
    let foundation = opening(MichiganContentPreset::FourWeekStandard);
    let bytes = foundation.initial_register().canonical_bytes();
    assert!(OpeningRegister::from_canonical(&bytes[..bytes.len() - 1]).is_err());
    assert!(MaterialWorldRegister::decode(&bytes[..bytes.len() - 1]).is_err());
    let raw_opening = OpeningRegister::from_canonical(bytes).unwrap();
    let typed_opening = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    assert_eq!(
        raw_opening.lookup().entries(),
        typed_opening.lookup().entries()
    );
    let current = MaterialWorldRegister::decode(bytes).unwrap();
    let raw_encoded =
        encode_register_with_opening(&raw_opening, &current, raw_opening.lookup()).unwrap();
    let typed_encoded = encode_register_with_opening(
        &typed_opening,
        foundation.initial_register(),
        typed_opening.lookup(),
    )
    .unwrap();
    assert_eq!(raw_encoded.package, typed_encoded.package);
}

use crate::organizer_aid_fixture;

fn assert_aid_period_package(
    opening: &[u8],
    candidate: &organizer_aid_fixture::Candidate,
    previous_chain: [u8; 32],
) -> [u8; 32] {
    use crate::material_storage::{self, LookupAnchor};
    let current = candidate.material().register();
    let receipts = candidate.material().receipt_bytes();
    let authority = OpeningRegister::from_canonical(opening).unwrap();
    let encoded = material_storage::encode(current, receipts, &authority, previous_chain).unwrap();
    // Independent inverse owns only the canonical immutable opening and stored packets.
    let inverse = OpeningRegister::from_canonical(opening).unwrap();
    let tick = current.completed_tick();
    let lookup = material_storage::read_period_lookup(
        &inverse,
        tick,
        &encoded.lookup_delta_bytes,
        LookupAnchor::Previous(previous_chain),
    )
    .unwrap();
    assert_eq!(lookup.chain, encoded.lookup_chain);
    assert_eq!(lookup.previous_chain, previous_chain);
    let restored = material_storage::decode(
        &inverse,
        tick,
        &encoded.register_storage_bytes,
        &encoded.receipt_storage_bytes,
        &lookup.lookup,
        lookup.chain,
    )
    .unwrap();
    assert_eq!(restored.0, current.canonical_bytes());
    assert_eq!(restored.1, receipts);
    assert_eq!(
        MaterialWorldRegister::decode(&restored.0).unwrap(),
        *current
    );
    assert_eq!(
        babylon_tick::material_world::decode_material_receipts(&restored.1).unwrap(),
        babylon_tick::material_world::decode_material_receipts(receipts).unwrap()
    );
    let current_sections = sections(&restored.0).unwrap();
    assert_eq!(
        current_sections
            .iter()
            .find(|section| section.id == 70)
            .unwrap()
            .count,
        Some(1)
    );
    let organizer = current_sections
        .iter()
        .find(|section| section.id == 69)
        .unwrap();
    assert!(organizer.raw(&restored.0).len() > 1);
    let saved = MaterialWorldRegister::decode(&restored.0).unwrap();
    assert_eq!(saved.organizer_state(), current.organizer_state());
    // A valid packet cannot be transplanted to another predecessor attestation.
    assert!(matches!(
        material_storage::read_period_lookup(
            &inverse,
            tick,
            &encoded.lookup_delta_bytes,
            LookupAnchor::Previous([251; 32])
        ),
        Err(material_storage::Error::LookupChain)
    ));
    let mut damaged = encoded.register_storage_bytes.clone();
    damaged.push(0);
    assert!(material_storage::decode(
        &inverse,
        tick,
        &damaged,
        &encoded.receipt_storage_bytes,
        &lookup.lookup,
        lookup.chain
    )
    .is_err());
    let mut damaged_lookup = encoded.lookup_delta_bytes.clone();
    damaged_lookup.push(0);
    assert!(matches!(
        material_storage::read_period_lookup(
            &inverse,
            tick,
            &damaged_lookup,
            LookupAnchor::Previous(previous_chain)
        ),
        Err(material_storage::Error::Trailing)
    ));
    assert_eq!(
        inverse.digest(),
        babylon_kernel::content_digest::sha256_of(opening)
    );
    encoded.lookup_chain
}
#[test]
fn local_grant_canonical_state_and_complete_receipt_package_inverse() {
    use babylon_practice_contract::OrganizerChoice;
    use organizer_aid_fixture as f;
    let mut cfg = f::config();
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = f::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        cfg,
        false,
        false,
    );
    let opening = session.material().canonical_bytes().to_vec();
    let authority = OpeningRegister::from_canonical(&opening).unwrap();
    let chain = crate::material_storage::initial_lookup_chain(&authority).unwrap();
    let accepted = f::commitment(&session, OrganizerChoice::LocalAid);
    let candidate = f::prepare(&session, Some(&accepted));
    assert_aid_period_package(&opening, &candidate, chain);
    assert_retained_aid_postings(
        &candidate
            .material()
            .register()
            .organizer_state()
            .unwrap()
            .aid_receipts
            .last()
            .unwrap()
            .support,
        2,
        4,
        6,
        6,
        0,
    );
    let receipts = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .unwrap();
    assert!(receipts.aid.iter().any(|row| row.outcome
        == babylon_material_circuit::AidOutcome::Granted
        && row.quantity == 2));
    assert!(candidate
        .material()
        .register()
        .organizer_state()
        .unwrap()
        .pending_aid
        .is_empty());
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    f::commit(&mut session, &mut sink, candidate);
    assert_eq!(
        session
            .material()
            .organizer_state()
            .unwrap()
            .aid_receipts
            .last()
            .unwrap()
            .authorization
            .gift
            .commitment,
        accepted
    );
}

fn assert_aid_dispatch(
    candidate: &organizer_aid_fixture::Candidate,
    accepted: &babylon_practice_contract::OrganizerCommitment,
) -> babylon_material_circuit::OrderId {
    use babylon_material_circuit::AidOutcome;
    let first_state = candidate.material().register();
    let first_sections = sections(first_state.canonical_bytes()).unwrap();
    for id in [71, 72] {
        assert_eq!(
            first_sections
                .iter()
                .find(|section| section.id == id)
                .unwrap()
                .count,
            Some(1)
        );
    }
    assert_retained_aid_postings(
        &first_state
            .organizer_state()
            .unwrap()
            .aid_receipts
            .last()
            .unwrap()
            .support,
        2,
        4,
        6,
        0,
        0,
    );
    let pending = &first_state.organizer_state().unwrap().pending_aid;
    assert_eq!(pending.len(), 1);
    assert_eq!(pending[0].gift.commitment, *accepted);
    let first_receipts = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .unwrap();
    assert!(first_receipts
        .aid
        .iter()
        .any(|r| r.outcome == AidOutcome::Dispatched && r.quantity == 2));
    first_receipts
        .aid
        .iter()
        .find(|r| r.outcome == AidOutcome::Dispatched)
        .unwrap()
        .commitment_id
}

fn assert_aid_arrival(
    candidate: &organizer_aid_fixture::Candidate,
    accepted: &babylon_practice_contract::OrganizerCommitment,
    commitment_id: babylon_material_circuit::OrderId,
    arrived: u64,
    refunded: i128,
) -> usize {
    use babylon_material_circuit::{
        AccountId, AidOutcome, CircuitAccounting, MoneyLocation, MoneyTransferPurpose,
        OrganizationAccountId,
    };
    let receipts = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .unwrap();
    let granted = receipts
        .aid
        .iter()
        .filter(|r| r.outcome == AidOutcome::Granted)
        .map(|r| r.quantity)
        .sum::<u64>();
    let lost = receipts
        .aid
        .iter()
        .filter(|r| r.outcome == AidOutcome::Lost)
        .map(|r| r.quantity)
        .sum::<u64>();
    assert_eq!(granted, arrived);
    assert_eq!(lost, 2 - arrived);
    assert!(receipts
        .aid
        .iter()
        .all(|r| r.commitment_id == commitment_id && r.dispatch_period == 1));
    let payer = AccountId::Organization(OrganizationAccountId::from_bytes([96; 32]));
    let refund = receipts
        .money_transfers
        .iter()
        .filter(|r| {
            matches!(r.purpose, MoneyTransferPurpose::AidRefund(_))
                && r.credit.location == MoneyLocation::Cash(payer)
        })
        .map(|r| r.credit.delta.micro_units())
        .sum::<i128>();
    assert_eq!(refund, refunded);
    let CircuitAccounting::Monetary(economy) = &candidate.material().register().state().accounting
    else {
        panic!("actual monetary gift")
    };
    assert_eq!(economy.book.cash(payer).unwrap().micro_units(), refunded);
    assert!(economy.aid.freight.is_empty());
    assert!(economy.book.snapshot().aid.is_empty());
    let closed_sections = sections(candidate.material().register().canonical_bytes()).unwrap();
    for id in [71, 72] {
        assert_eq!(
            closed_sections
                .iter()
                .find(|section| section.id == id)
                .unwrap()
                .count,
            Some(0)
        );
    }
    let completed = candidate.material().register().organizer_state().unwrap();
    assert!(completed.pending_aid.is_empty());
    assert_eq!(
        completed
            .aid_receipts
            .last()
            .unwrap()
            .authorization
            .gift
            .commitment,
        *accepted
    );
    assert_eq!(
        completed
            .aid_receipts
            .last()
            .unwrap()
            .authorization
            .dispatch_period,
        1
    );
    assert_eq!(completed.aid_receipts.last().unwrap().practice.period, 2);
    assert_retained_aid_postings(
        &completed.aid_receipts.last().unwrap().support,
        0,
        0,
        0,
        i128::from(arrived) * 3,
        refunded,
    );
    completed.aid_receipts.len()
}

fn routed_aid_package_sequence(loss_ppm: u32, arrived: u64, refunded: i128) {
    use babylon_practice_contract::{OrganizerAidKind, OrganizerChoice};
    use organizer_aid_fixture as f;
    let mut cfg = f::config();
    cfg.aid_bindings[0].kind = OrganizerAidKind::Remote;
    cfg.aid_bindings[0].coordination_hours = 1;
    let mut session = f::authored_session_with_loss(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        cfg,
        false,
        true,
        loss_ppm,
    );
    let opening = session.material().canonical_bytes().to_vec();
    let immutable = opening.clone();
    let authority = OpeningRegister::from_canonical(&opening).unwrap();
    let chain = crate::material_storage::initial_lookup_chain(&authority).unwrap();
    let accepted = f::commitment(&session, OrganizerChoice::RemoteAid);
    let first = f::prepare(&session, Some(&accepted));
    let chain = assert_aid_period_package(&opening, &first, chain);
    let commitment_id = assert_aid_dispatch(&first, &accepted);
    let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
    f::commit(&mut session, &mut sink, first);
    let second = f::prepare(&session, None);
    let chain = assert_aid_period_package(&opening, &second, chain);
    let terminal_count = assert_aid_arrival(&second, &accepted, commitment_id, arrived, refunded);
    f::commit(&mut session, &mut sink, second);
    let third = f::prepare(&session, None);
    assert_aid_period_package(&opening, &third, chain);
    let receipts =
        babylon_tick::material_world::decode_material_receipts(third.material().receipt_bytes())
            .unwrap();
    assert!(receipts.aid.is_empty());
    assert!(third
        .material()
        .register()
        .organizer_state()
        .unwrap()
        .pending_aid
        .is_empty());
    assert_eq!(
        third
            .material()
            .register()
            .organizer_state()
            .unwrap()
            .aid_receipts
            .len(),
        terminal_count
    );
    assert_eq!(opening, immutable);
}
#[test]
fn routed_dispatch_and_arrival_package_preserve_original_authorization_once() {
    routed_aid_package_sequence(0, 2, 0);
}
#[test]
fn partial_freight_loss_package_preserves_exact_gift_and_cash_refund() {
    routed_aid_package_sequence(500_000, 1, 3);
}
#[test]
fn total_freight_loss_package_refunds_payer_without_repeating_authorization() {
    routed_aid_package_sequence(1_000_000, 0, 6);
}

fn assert_retained_aid_postings(
    support: &babylon_practice_contract::OrganizerAidSupport,
    dispatched: u64,
    hours: u64,
    reserved: i128,
    granted: i128,
    refunded: i128,
) {
    assert_eq!(
        serde_json::to_value(support).unwrap()["material_postings"],
        serde_json::json!({
            "dispatched_quantity": dispatched, "fulfillment_hours": hours,
            "payer_cash_reserved_micros": reserved.to_string(),
            "payer_cash_granted_micros": granted.to_string(),
            "payer_cash_refunded_micros": refunded.to_string()
        })
    );
}

// These fixtures author complete inventory rows independently of the codec.
fn prefix_inventory(count: u32) -> Vec<u8> {
    let mut raw = count.to_be_bytes().to_vec();
    for row in 0..count {
        let mut site = [0; 32];
        site[28..].copy_from_slice(&row.to_be_bytes());
        raw.extend_from_slice(&site);
        raw.extend_from_slice(&[9; 32]);
        raw.extend_from_slice(&[11; 32]);
        raw.extend_from_slice(&digest(&row.to_le_bytes())[..8]);
    }
    raw
}
fn prefix_section(id: u16, raw: &[u8], count: usize) -> Section {
    Section {
        id,
        start: 0,
        end: raw.len(),
        count: Some(count),
    }
}
fn prefix_selected(old: &[u8], current: &[u8]) -> (Block, StoredSection, TypedLookup) {
    let old_count = u32::from_be_bytes(old[..4].try_into().unwrap()) as usize;
    let count = u32::from_be_bytes(current[..4].try_into().unwrap()) as usize;
    let old_section = prefix_section(10, old, old_count);
    let section = prefix_section(10, current, count);
    let mut lookup = TypedLookup::default();
    normalize(old, layout(10).unwrap(), &mut lookup, true).unwrap();
    let selected = block(current, &section, Some((&old_section, old)), &mut lookup).unwrap();
    let mut wire = Vec::new();
    append_block(&mut wire, current, &section, &selected).unwrap();
    let stored = stored_section(&mut Cursor::new(&wire)).unwrap();
    (selected, stored, lookup)
}
fn prefix_manual(old: &[u8], current: &[u8]) -> (StoredSection, TypedLookup) {
    let shape = layout(10).unwrap();
    let count = u32::from_be_bytes(current[..4].try_into().unwrap()) as usize;
    let mut lookup = TypedLookup::default();
    let previous = normalize(old, shape, &mut lookup, true).unwrap();
    let next = normalize(current, shape, &mut lookup, true).unwrap();
    let delta = next
        .bytes
        .iter()
        .enumerate()
        .map(|(index, byte)| byte ^ previous.bytes.get(index).copied().unwrap_or(0))
        .collect::<Vec<_>>();
    let body = columns(&delta, count, normalized_width(shape).unwrap()).unwrap();
    let body_length = body.len();
    let body_digest = digest(&body);
    let encoded = compressed(4, body).unwrap().encoded;
    (
        StoredSection {
            id: 10,
            mode: 4,
            count: Some(count),
            raw_length: current.len(),
            raw_digest: digest(current),
            body_length,
            body_digest,
            encoded,
        },
        lookup,
    )
}
#[test]
fn opening_prefix_producer_selects_smaller_frame_for_added_removed_and_rekeyed_rows() {
    let old = prefix_inventory(256);
    let added = prefix_inventory(257);
    let removed = prefix_inventory(255);
    let mut rekeyed = old.clone();
    let last = 4 + 255 * 104;
    rekeyed[last..last + 32].copy_from_slice(&[244; 32]);
    for current in [added, removed, rekeyed] {
        let (selected, stored, mut lookup) = prefix_selected(&old, &current);
        let count = stored.count.unwrap();
        let full_rows = normalize(&current, layout(10).unwrap(), &mut lookup, false).unwrap();
        let full = compressed(2, columns(&full_rows.bytes, count, 20).unwrap()).unwrap();
        assert_eq!(
            selected.mode, 4,
            "current full-row fallback loses the retained opening prefix"
        );
        assert!(selected.encoded.len() < full.encoded.len());
        let base = prefix_section(10, &old, 256);
        assert_eq!(
            restore_section(
                &stored,
                Some((&base, &old)),
                &lookup,
                lookup.entries().len()
            )
            .unwrap(),
            current
        );
    }
}
#[test]
fn opening_prefix_keeps_full_frame_when_smaller_and_preserves_empty_and_missing_base() {
    let old = prefix_inventory(256);
    let mut current = prefix_inventory(32);
    for row in current[4..].chunks_exact_mut(104) {
        row[96..].fill(0);
    }
    let (selected, stored, lookup) = prefix_selected(&old, &current);
    assert_eq!(selected.mode, 2);
    let base = prefix_section(10, &old, 256);
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        )
        .unwrap(),
        current
    );
    for (old, current) in [
        (prefix_inventory(0), prefix_inventory(1)),
        (prefix_inventory(1), prefix_inventory(0)),
    ] {
        assert_eq!(prefix_selected(&old, &current).0.mode, 2);
    }
    let section = prefix_section(10, &current, 32);
    let mut lookup = TypedLookup::default();
    assert_eq!(
        block(&current, &section, None, &mut lookup).unwrap().mode,
        2
    );
    assert_eq!(prefix_selected(&old, &old).0.mode, 0);
}
#[test]
fn opening_prefix_inverse_checks_base_layout_counts_extents_and_typed_prefix() {
    let old = prefix_inventory(256);
    let current = prefix_inventory(257);
    let (mut stored, lookup) = prefix_manual(&old, &current);
    let mut base = prefix_section(10, &old, 256);
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        )
        .unwrap(),
        current
    );
    assert_eq!(
        restore_section(&stored, None, &lookup, lookup.entries().len()),
        Err(StorageError::ParentMismatch)
    );
    base.id = 11;
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Layout)
    );
    base.id = 10;
    base.count = Some(255);
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Layout)
    );
    base.count = Some(256);
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old[..old.len() - 1])),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Layout)
    );
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len() - 1
        ),
        Err(StorageError::LookupIndex)
    );
    let mut wrong = lookup.entries().to_vec();
    wrong[0].kind = IdentityKind::Contribution;
    let wrong = TypedLookup::from_entries(wrong).unwrap();
    assert_eq!(
        restore_section(&stored, Some((&base, &old)), &wrong, wrong.entries().len()),
        Err(StorageError::LookupIndex)
    );
    stored.body_length += 1;
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Layout)
    );
    stored.body_length -= 1;
    stored.count = Some(layout(10).unwrap().maximum + 1);
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Count)
    );
    stored.id = 69;
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Layout)
    );
}
#[test]
fn opening_prefix_single_frame_and_digest_cannot_hide_truncation_or_extra_bytes() {
    let old = prefix_inventory(8);
    let current = prefix_inventory(9);
    let (mut stored, lookup) = prefix_manual(&old, &current);
    let base = prefix_section(10, &old, 8);
    let encoded = stored.encoded.clone();
    stored.encoded.pop();
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Compression)
    );
    stored.encoded = encoded.clone();
    stored
        .encoded
        .extend(compress_exact(&[], MAX_BYTES).unwrap());
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Compression)
    );
    stored.encoded = encoded;
    stored.body_digest[0] ^= 1;
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Compression)
    );
}
// Author a complete physical package with one explicit prefix block. This does
// not call typed encoding on invalid registers: decoder admission is the subject.
fn prefix_package(opening: &OpeningRegister, current: &[u8], id: u16) -> (Vec<u8>, TypedLookup) {
    let parsed = sections(current).unwrap();
    let mut lookup = opening.lookup().clone();
    let mut blocks = Vec::new();
    for section in &parsed {
        let old = opening
            .sections
            .iter()
            .find(|old| old.id == section.id)
            .unwrap();
        let old_raw = old.raw(opening.canonical_bytes());
        if section.id == id {
            let shape = layout(id).unwrap();
            let prior = normalize(old_raw, shape, &mut lookup, false).unwrap();
            let next = normalize(section.raw(current), shape, &mut lookup, true).unwrap();
            let delta = next
                .bytes
                .iter()
                .enumerate()
                .map(|(index, byte)| byte ^ prior.bytes.get(index).copied().unwrap_or(0))
                .collect::<Vec<_>>();
            blocks.push(
                compressed(
                    4,
                    columns(
                        &delta,
                        section.count.unwrap(),
                        normalized_width(shape).unwrap(),
                    )
                    .unwrap(),
                )
                .unwrap(),
            );
        } else {
            blocks.push(block(current, section, Some((old, old_raw)), &mut lookup).unwrap());
        }
    }
    let mut package = DOMAIN.to_vec();
    package.extend_from_slice(&opening.digest());
    package.extend_from_slice(&digest(current));
    package.extend_from_slice(&[0; 32]);
    package.extend_from_slice(&u64::try_from(current.len()).unwrap().to_be_bytes());
    package.extend_from_slice(&u32::try_from(lookup.entries().len()).unwrap().to_be_bytes());
    package.extend_from_slice(&lookup.prefix_digest(lookup.entries().len()).unwrap());
    package.extend_from_slice(&u16::try_from(parsed.len()).unwrap().to_be_bytes());
    for (section, block) in parsed.iter().zip(blocks) {
        append_block(&mut package, current, section, &block).unwrap();
    }
    (package, lookup)
}
#[test]
fn opening_prefix_full_admission_rejects_rehashed_duplicate_and_out_of_order_rows() {
    let foundation = opening(MichiganContentPreset::FourWeekStandard);
    let authority = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    let canonical = authority.canonical_bytes();
    let section = authority
        .sections
        .iter()
        .find(|section| section.id == 2)
        .unwrap();
    assert!(section.count.unwrap() >= 2);
    let (package, lookup) = prefix_package(&authority, canonical, 2);
    assert_eq!(
        decode_admitted(&authority, &package, &lookup, [0; 32])
            .unwrap()
            .0,
        canonical
    );
    assert_eq!(
        decode_against_admitted(
            &authority,
            &package,
            &lookup,
            [0; 32],
            foundation.initial_register()
        )
        .unwrap(),
        canonical
    );
    for duplicate in [true, false] {
        let mut invalid = canonical.to_vec();
        let first = section.start + 4;
        let second = first + 64;
        let row = invalid[first..second].to_vec();
        if duplicate {
            invalid[second..second + 64].copy_from_slice(&row);
        } else {
            invalid.copy_within(second..second + 64, first);
            invalid[second..second + 64].copy_from_slice(&row);
        }
        assert!(MaterialWorldRegister::decode(&invalid).is_err());
        let (rehashed, lookup) = prefix_package(&authority, &invalid, 2);
        assert_eq!(
            decode_admitted(&authority, &rehashed, &lookup, [0; 32]),
            Err(StorageError::Canonical)
        );
        assert_eq!(
            decode_against_admitted(
                &authority,
                &rehashed,
                &lookup,
                [0; 32],
                foundation.initial_register()
            ),
            Err(StorageError::Canonical)
        );
    }
    let mut wrong_opening = package.clone();
    wrong_opening[DOMAIN.len()] ^= 1;
    assert_eq!(
        decode_admitted(&authority, &wrong_opening, &lookup, [0; 32]),
        Err(StorageError::ParentMismatch)
    );
    assert_eq!(
        decode_admitted(&authority, &package, &lookup, [1; 32]),
        Err(StorageError::DigestMismatch)
    );
    let mut trailing = package;
    trailing.push(0);
    assert_eq!(
        decode_admitted(&authority, &trailing, &lookup, [0; 32]),
        Err(StorageError::Trailing)
    );
}
#[test]
fn previous_state_storage_domain_is_explicitly_unsupported() {
    let foundation = opening(MichiganContentPreset::FourWeekStandard);
    let authority = OpeningRegister::from_opening(foundation.initial_register()).unwrap();
    let encoded = encode_register_with_opening(
        &authority,
        foundation.initial_register(),
        authority.lookup(),
    )
    .unwrap();
    let mut old = encoded.package;
    old[..DOMAIN.len()].copy_from_slice(b"babylon.state-storage.v2\0");
    assert_eq!(
        decode_admitted(&authority, &old, authority.lookup(), [0; 32]),
        Err(StorageError::Version)
    );
}
#[test]
fn opening_prefix_rehashed_references_still_refuse_future_and_wrong_identity_kind() {
    let old = prefix_inventory(8);
    let current = prefix_inventory(9);
    let base = prefix_section(10, &old, 8);
    for (index, expected) in [
        (u32::MAX, StorageError::LookupIndex),
        (1, StorageError::IdentityKind),
    ] {
        let (mut stored, lookup) = prefix_manual(&old, &current);
        let mut body = decompress_exact(
            &stored.encoded,
            stored.body_length,
            stored.body_digest,
            MAX_BYTES,
        )
        .unwrap();
        // The added row has no opening bytes: its site reference is literal.
        for (column, byte) in index.to_be_bytes().iter().enumerate() {
            body[column * 9 + 8] = *byte;
        }
        stored.body_digest = digest(&body);
        stored.encoded = compress_exact(&body, MAX_BYTES).unwrap();
        assert_eq!(
            restore_section(
                &stored,
                Some((&base, &old)),
                &lookup,
                lookup.entries().len()
            ),
            Err(expected)
        );
    }
    let (stored, lookup) = prefix_manual(&old, &prefix_inventory(0));
    assert_eq!(
        restore_section(
            &stored,
            Some((&base, &old)),
            &lookup,
            lookup.entries().len()
        ),
        Err(StorageError::Count)
    );
    assert!(matches!(
        stored_section(&mut Cursor::new(&[0, 10, 5])),
        Err(StorageError::Framing)
    ));
}
#[test]
fn opening_prefix_equal_frame_keeps_full_columns() {
    let mut old = 1_u32.to_be_bytes().to_vec();
    old.extend_from_slice(&[7; 32]);
    old.extend_from_slice(&[0; 16]);
    let mut current = 2_u32.to_be_bytes().to_vec();
    current.extend_from_slice(&old[4..]);
    current.extend_from_slice(&[8; 32]);
    current.extend_from_slice(&[0; 16]);
    let shape = layout(14).unwrap();
    let mut lookup = TypedLookup::default();
    let previous = normalize(&old, shape, &mut lookup, true).unwrap();
    assert!(previous.bytes.iter().all(|byte| *byte == 0));
    let next = normalize(&current, shape, &mut lookup, true).unwrap();
    let delta = next
        .bytes
        .iter()
        .enumerate()
        .map(|(index, byte)| byte ^ previous.bytes.get(index).copied().unwrap_or(0))
        .collect::<Vec<_>>();
    assert_eq!(delta, next.bytes);
    let selected = block(
        &current,
        &prefix_section(14, &current, 2),
        Some((&prefix_section(14, &old, 1), &old)),
        &mut lookup,
    )
    .unwrap();
    assert_eq!(selected.mode, 2);
}
