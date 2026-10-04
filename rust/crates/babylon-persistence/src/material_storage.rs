//! Atomic staging of the current state and complete receipt storage codecs.
//! Lookup bytes are storage dependencies; canonical engine bytes remain unchanged.
mod descriptors;
pub use descriptors::Error as DescriptorError;

use crate::receipt_storage;
use crate::state_storage::{self, IdentityEntry, StorageError};
pub use crate::state_storage::{OpeningRegister, TypedLookup};
use crate::storage_compression::{compress_exact, decompress_exact, StorageCompressionError};
use babylon_kernel::content_digest::sha256_of;
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};

pub(crate) const LOOKUP_DOMAIN: &[u8] = b"BabylonPeriodLookupV3\0";
const LOOKUP_VERSION: u16 = 3;
/// Designed logical storage limit, matching the current register/lookup allowance.
pub(crate) const MAX_LOOKUP_BYTES: usize = 1_000_000_000;
// Includes zstd's compressBound allowance plus this wrapper's complete metadata.
pub(crate) const MAX_LOOKUP_PACKAGE_BYTES: usize = MAX_LOOKUP_BYTES + MAX_LOOKUP_BYTES / 256 + 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    State(StorageError),
    Receipt(receipt_storage::Error),
    Compression(StorageCompressionError),
    Domain,
    Version,
    Truncated,
    Trailing,
    Bounds,
    LookupPrefix,
    Opening,
    Tick,
    LookupChain,
    Allocation,
    Descriptor(DescriptorError),
    CollectionJoin,
}
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "material storage refused: {self:?}")
    }
}
impl std::error::Error for Error {}
impl From<StorageError> for Error {
    fn from(error: StorageError) -> Self {
        Self::State(error)
    }
}
impl From<receipt_storage::Error> for Error {
    fn from(error: receipt_storage::Error) -> Self {
        match error {
            receipt_storage::Error::Tick => Self::Tick,
            receipt_storage::Error::CollectionJoin => Self::CollectionJoin,
            error => Self::Receipt(error),
        }
    }
}
impl From<StorageCompressionError> for Error {
    fn from(error: StorageCompressionError) -> Self {
        Self::Compression(error)
    }
}
type Result<T> = std::result::Result<T, Error>;

#[derive(Debug, Clone)]
pub struct EncodedMaterial {
    pub register_storage_bytes: Vec<u8>,
    pub receipt_storage_bytes: Vec<u8>,
    pub lookup_delta_bytes: Vec<u8>,
    pub lookup: TypedLookup,
    pub lookup_chain: [u8; 32],
}

/// Admit and cache the immutable opening once for standalone codec consumers.
/// Production callers use `OpeningRegister::from_opening` on their admitted register.
/// # Errors
/// Refuses invalid or non-opening canonical state and typed identity bounds.
pub fn seed(base: &[u8]) -> Result<OpeningRegister> {
    Ok(OpeningRegister::from_canonical(base)?)
}

/// Exact identity of the period-local table, independent of historical table ownership.
/// # Errors
/// Refuses unrepresentable counts or invalid prefixes.
pub fn lookup_identity(lookup: &TypedLookup) -> Result<(usize, [u8; 32])> {
    let count = lookup.entries().len();
    Ok((count, lookup.prefix_digest(count)?))
}

/// An anchor from previously authenticated caller state, never an unverified header.
#[derive(Debug, Clone, Copy)]
pub enum LookupAnchor {
    Previous([u8; 32]),
    Current([u8; 32]),
}
#[derive(Debug, Clone)]
pub struct DecodedPeriodLookup {
    pub lookup: TypedLookup,
    pub previous_chain: [u8; 32],
    pub chain: [u8; 32],
}
const INITIAL_CHAIN_DOMAIN: &[u8] = b"BabylonOpeningLookupChainV1\0";
const PERIOD_CHAIN_DOMAIN: &[u8] = b"BabylonPeriodLookupChainV1\0";

/// Constant-size starting attestation derived from the admitted opening and seed.
/// # Errors
/// Refuses an unrepresentable seed count or invalid lookup prefix.
pub fn initial_lookup_chain(opening: &OpeningRegister) -> Result<[u8; 32]> {
    let count = u32::try_from(opening.lookup().entries().len()).map_err(|_| Error::Bounds)?;
    let mut bytes = INITIAL_CHAIN_DOMAIN.to_vec();
    bytes.extend_from_slice(&opening.digest());
    bytes.extend_from_slice(&count.to_be_bytes());
    bytes.extend_from_slice(&opening.lookup().prefix_digest(count as usize)?);
    Ok(sha256_of(&bytes))
}
fn period_lookup_chain(
    opening: &OpeningRegister,
    tick: u64,
    previous: [u8; 32],
    packed_digest: [u8; 32],
) -> [u8; 32] {
    let mut bytes = PERIOD_CHAIN_DOMAIN.to_vec();
    bytes.extend_from_slice(&opening.digest());
    bytes.extend_from_slice(&tick.to_be_bytes());
    bytes.extend_from_slice(&previous);
    bytes.extend_from_slice(&packed_digest);
    sha256_of(&bytes)
}

fn admitted_count(opening_count: usize, addition_count: usize) -> Result<usize> {
    if addition_count
        .checked_mul(33)
        .and_then(|bytes| bytes.checked_add(4))
        .is_none_or(|bytes| bytes > MAX_LOOKUP_BYTES)
    {
        return Err(Error::Bounds);
    }
    let count = opening_count
        .checked_add(addition_count)
        .ok_or(Error::Bounds)?;
    if count > u32::MAX as usize {
        return Err(Error::Bounds);
    }
    Ok(count)
}

fn appended(prior: &TypedLookup, additions: &[IdentityEntry]) -> Result<TypedLookup> {
    let count = admitted_count(prior.entries().len(), additions.len())?;
    let mut entries = Vec::new();
    entries
        .try_reserve_exact(count)
        .map_err(|_| Error::Allocation)?;
    entries.extend_from_slice(prior.entries());
    entries.extend_from_slice(additions);
    // Unlike intern(), this refuses any duplicate across prior and appended entries.
    Ok(TypedLookup::from_entries(entries)?)
}

fn encode_period_lookup(
    opening: &OpeningRegister,
    tick: u64,
    previous_chain: [u8; 32],
    additions: &[IdentityEntry],
) -> Result<(Vec<u8>, [u8; 32])> {
    if tick == 0 {
        return Err(Error::Tick);
    }
    admitted_count(opening.lookup().entries().len(), additions.len())?;
    let packed = state_storage::encode_lookup(additions)?;
    let descriptors = descriptors::encode(opening, tick, additions)?;
    let compressed = compress_exact(&descriptors, MAX_LOOKUP_BYTES)?;
    let mut bytes = LOOKUP_DOMAIN.to_vec();
    bytes.extend_from_slice(&LOOKUP_VERSION.to_be_bytes());
    bytes.extend_from_slice(&opening.digest());
    bytes.extend_from_slice(&tick.to_be_bytes());
    bytes.extend_from_slice(&previous_chain);
    bytes.extend_from_slice(&(packed.len() as u64).to_be_bytes());
    bytes.extend_from_slice(&sha256_of(&packed));
    bytes.extend_from_slice(&(descriptors.len() as u64).to_be_bytes());
    bytes.extend_from_slice(&sha256_of(&descriptors));
    bytes.extend_from_slice(&(compressed.len() as u64).to_be_bytes());
    bytes.extend_from_slice(&compressed);
    if bytes.len() > MAX_LOOKUP_PACKAGE_BYTES {
        return Err(Error::Bounds);
    }
    let chain = period_lookup_chain(opening, tick, previous_chain, sha256_of(&packed));
    Ok((bytes, chain))
}

/// Stage state additions first, then receipt-only identities, without changing any input owner.
/// # Errors
/// Refuses invalid canonical inputs, lookup prefixes, arithmetic or package bounds.
pub fn encode(
    current: &MaterialWorldRegister,
    receipts: &[u8],
    opening: &OpeningRegister,
    previous_chain: [u8; 32],
) -> Result<EncodedMaterial> {
    if current.completed_tick() == 0 {
        return Err(Error::Tick);
    }
    let admitted_receipts = receipt_storage::AdmittedReceipts::new(receipts, Some(current))?;
    if admitted_receipts.resolve_tick() != current.completed_tick() {
        return Err(Error::Tick);
    }
    let mut state =
        state_storage::encode_register_with_opening(opening, current, opening.lookup())?;
    let mut staged = appended(opening.lookup(), &state.lookup_delta)?;
    let receipt_storage_bytes = receipt_storage::encode(&admitted_receipts, &mut staged)?;
    if staged.entries().get(..opening.lookup().entries().len()) != Some(opening.lookup().entries())
    {
        return Err(Error::LookupPrefix);
    }
    let additions = &staged.entries()[opening.lookup().entries().len()..];
    let (lookup_delta_bytes, lookup_chain) =
        encode_period_lookup(opening, current.completed_tick(), previous_chain, additions)?;
    state.bind_lookup_chain(lookup_chain)?;
    Ok(EncodedMaterial {
        register_storage_bytes: state.package,
        receipt_storage_bytes,
        lookup_delta_bytes,
        lookup: staged,
        lookup_chain,
    })
}

struct Cursor<'a> {
    bytes: &'a [u8],
    position: usize,
}
impl<'a> Cursor<'a> {
    fn take(&mut self, count: usize) -> Result<&'a [u8]> {
        let end = self.position.checked_add(count).ok_or(Error::Bounds)?;
        let bytes = self.bytes.get(self.position..end).ok_or(Error::Truncated)?;
        self.position = end;
        Ok(bytes)
    }
    fn array<const N: usize>(&mut self) -> Result<[u8; N]> {
        self.take(N)?.try_into().map_err(|_| Error::Truncated)
    }
    fn number(&mut self) -> Result<usize> {
        usize::try_from(u64::from_be_bytes(self.array()?)).map_err(|_| Error::Bounds)
    }
    fn done(&self) -> Result<()> {
        if self.position == self.bytes.len() {
            Ok(())
        } else {
            Err(Error::Trailing)
        }
    }
}

/// Decode one independent period lookup against its immutable opening authority.
/// No preceding or future period entries are admitted or retained.
/// # Errors
/// Refuses wrong opening/tick, framing, bounds, compression, duplicate or unknown identities.
pub fn read_period_lookup(
    opening: &OpeningRegister,
    tick: u64,
    encoded_delta: &[u8],
    anchor: LookupAnchor,
) -> Result<DecodedPeriodLookup> {
    if tick == 0 {
        return Err(Error::Tick);
    }
    if encoded_delta.len() > MAX_LOOKUP_PACKAGE_BYTES {
        return Err(Error::Bounds);
    }
    let mut cursor = Cursor {
        bytes: encoded_delta,
        position: 0,
    };
    if cursor.take(LOOKUP_DOMAIN.len())? != LOOKUP_DOMAIN {
        return Err(Error::Domain);
    }
    if u16::from_be_bytes(cursor.array()?) != LOOKUP_VERSION {
        return Err(Error::Version);
    }
    if cursor.array::<32>()? != opening.digest() {
        return Err(Error::Opening);
    }
    if u64::from_be_bytes(cursor.array()?) != tick {
        return Err(Error::Tick);
    }
    let previous_chain: [u8; 32] = cursor.array()?;
    if let LookupAnchor::Previous(expected) = anchor {
        if previous_chain != expected {
            return Err(Error::LookupChain);
        }
    }
    let length = cursor.number()?;
    if length > MAX_LOOKUP_BYTES {
        return Err(Error::Bounds);
    }
    if length < 4 || (length - 4) % 33 != 0 {
        return Err(Error::State(StorageError::Framing));
    }
    let expected_count = (length - 4) / 33;
    admitted_count(opening.lookup().entries().len(), expected_count)?;
    let digest = cursor.array()?;
    let descriptor_length = cursor.number()?;
    if descriptor_length > MAX_LOOKUP_BYTES {
        return Err(Error::Bounds);
    }
    if descriptor_length > length
        || descriptor_length
            < expected_count
                .checked_mul(5)
                .and_then(|n| n.checked_add(4))
                .ok_or(Error::Bounds)?
    {
        return Err(Error::Descriptor(DescriptorError::Framing));
    }
    let descriptor_digest = cursor.array()?;
    let encoded_length = cursor.number()?;
    if encoded_length > MAX_LOOKUP_PACKAGE_BYTES {
        return Err(Error::Bounds);
    }
    let encoded = cursor.take(encoded_length)?;
    cursor.done()?;
    let descriptor_bytes = decompress_exact(
        encoded,
        descriptor_length,
        descriptor_digest,
        MAX_LOOKUP_BYTES,
    )?;
    let additions = descriptors::decode(opening, tick, &descriptor_bytes, expected_count)?;
    let packed = state_storage::encode_lookup(&additions)?;
    if packed.len() != length || sha256_of(&packed) != digest {
        return Err(Error::State(StorageError::DigestMismatch));
    }
    let lookup = appended(opening.lookup(), &additions)?;
    let chain = period_lookup_chain(opening, tick, previous_chain, sha256_of(&packed));
    if let LookupAnchor::Current(expected) = anchor {
        if chain != expected {
            return Err(Error::LookupChain);
        }
    }
    Ok(DecodedPeriodLookup {
        lookup,
        previous_chain,
        chain,
    })
}

/// Reconstruct both complete canonical sequences using each codec's exact authenticated prefix.
/// # Errors
/// Refuses invalid base state, package framing, lengths, kinds, references or hashes.
pub fn decode(
    opening: &OpeningRegister,
    tick: u64,
    state_package: &[u8],
    receipt_package: &[u8],
    lookup: &TypedLookup,
    lookup_chain: [u8; 32],
) -> Result<(Vec<u8>, Vec<u8>)> {
    let admitted = decode_typed(
        opening,
        tick,
        state_package,
        receipt_package,
        lookup,
        lookup_chain,
    )?;
    Ok((admitted.register_bytes, admitted.receipt_bytes))
}

/// Typed values produced by complete canonical admission, never by framing alone.
pub(crate) struct DecodedMaterial<R = MaterialWorldRegister> {
    pub(crate) register_bytes: Vec<u8>,
    pub(crate) receipt_bytes: Vec<u8>,
    pub(crate) register: R,
    pub(crate) receipts: MaterialTickReceipts,
}

pub(crate) fn decode_typed(
    opening: &OpeningRegister,
    tick: u64,
    state_package: &[u8],
    receipt_package: &[u8],
    lookup: &TypedLookup,
    lookup_chain: [u8; 32],
) -> Result<DecodedMaterial> {
    if tick == 0 {
        return Err(Error::Tick);
    }
    let (register_bytes, register) =
        state_storage::decode_admitted(opening, state_package, lookup, lookup_chain)?;
    let (receipt_bytes, receipts) = receipt_storage::decode_admitted(receipt_package, lookup)?;
    if register.completed_tick() != tick || receipts.resolve_tick != tick {
        return Err(Error::Tick);
    }
    babylon_tick::material_world::validate_retained_collection(&register, &receipts)
        .map_err(|_| Error::CollectionJoin)?;
    Ok(DecodedMaterial {
        register_bytes,
        receipt_bytes,
        register,
        receipts,
    })
}

// A borrowed witness is usable only after the complete restored canonical
// package is byte-identical to its already admitted register.
pub(crate) fn decode_typed_with_witness<'w>(
    opening: &OpeningRegister,
    tick: u64,
    state_package: &[u8],
    receipt_package: &[u8],
    lookup: &TypedLookup,
    lookup_chain: [u8; 32],
    witness: Option<&'w MaterialWorldRegister>,
) -> Result<DecodedMaterial<std::borrow::Cow<'w, MaterialWorldRegister>>> {
    let Some(witness) = witness else {
        let admitted = decode_typed(
            opening,
            tick,
            state_package,
            receipt_package,
            lookup,
            lookup_chain,
        )?;
        return Ok(DecodedMaterial {
            register_bytes: admitted.register_bytes,
            receipt_bytes: admitted.receipt_bytes,
            register: std::borrow::Cow::Owned(admitted.register),
            receipts: admitted.receipts,
        });
    };
    if tick == 0 {
        return Err(Error::Tick);
    }
    let register_bytes = state_storage::decode_against_admitted(
        opening,
        state_package,
        lookup,
        lookup_chain,
        witness,
    )?;
    let (receipt_bytes, receipts) = receipt_storage::decode_admitted(receipt_package, lookup)?;
    if witness.completed_tick() != tick || receipts.resolve_tick != tick {
        return Err(Error::Tick);
    }
    babylon_tick::material_world::validate_retained_collection(witness, &receipts)
        .map_err(|_| Error::CollectionJoin)?;
    Ok(DecodedMaterial {
        register_bytes,
        receipt_bytes,
        register: std::borrow::Cow::Borrowed(witness),
        receipts,
    })
}

#[cfg(test)]
mod tests;

#[cfg(test)]
mod descriptor_controls;

#[cfg(test)]
mod descriptor_guard_controls;

#[cfg(test)]
mod typed_decode_controls {
    use super::*;
    use crate::organizer_aid_fixture as fixture;
    use babylon_practice_contract::OrganizerChoice;
    use babylon_tick::material_world::decode_material_receipts;

    #[test]
    fn actual_collection_restarts_through_owned_and_borrowed_storage_with_exact_original_join() {
        use babylon_material_circuit::CircuitAccounting;
        let foundation = crate::michigan_dynamic_hex_foundation().unwrap();
        let base = fixture::authored_session(foundation, fixture::config(), false, false);
        let mut state = base.material().state().clone();
        let CircuitAccounting::Monetary(e) = &mut state.accounting else {
            unreachable!()
        };
        e.recurring.as_mut().unwrap().household_purchases[0].target_closing_stock = 4;
        let aid = &e.aid.mandates[0];
        let mut cfg = serde_json::to_value(fixture::config()).unwrap();
        let babylon_material_circuit::AccountId::Organization(payer) = aid.payer else {
            unreachable!()
        };
        cfg["collection"] = serde_json::json!({
            "mandate_id":([93_u8;32].to_vec()),"source_hash":([94_u8;32].to_vec()),
            "actor_id":aid.donor_actor,"contributor_id":aid.donor_contributor_id,
            "household_principal_id":aid.donor.as_bytes().to_vec(),"organization_account_id":payer.as_bytes().to_vec(),
            "social_class_target":([98_u8;32].to_vec()),"labor_unit_id":aid.labor_unit_id.as_bytes().to_vec(),
            "cash_consent":"accept","maximum_cash_micros":"2","protected_cash_floor_micros":"0","collection_hours":2
        });
        let session = fixture::try_session(
            foundation,
            &format!(
                "{}\n{}\n{}",
                fixture::MATERIAL,
                fixture::PRODUCTS,
                fixture::PRACTICE
            ),
            state,
            serde_json::from_value(cfg).unwrap(),
        )
        .unwrap();
        let opening = OpeningRegister::from_opening(session.material()).unwrap();
        let chain = initial_lookup_chain(&opening).unwrap();
        let accepted = fixture::commitment(&session, serde_json::from_str("\"collect\"").unwrap());
        let candidate = fixture::prepare(&session, Some(&accepted));
        let current = candidate.material().register();
        let bytes = candidate.material().receipt_bytes();
        let encoded = encode(current, bytes, &opening, chain).unwrap();
        let loaded = read_period_lookup(
            &opening,
            1,
            &encoded.lookup_delta_bytes,
            LookupAnchor::Previous(chain),
        )
        .unwrap();
        for witness in [None, Some(current)] {
            let actual = decode_typed_with_witness(
                &opening,
                1,
                &encoded.register_storage_bytes,
                &encoded.receipt_storage_bytes,
                &loaded.lookup,
                loaded.chain,
                witness,
            )
            .unwrap();
            assert_eq!(actual.register.as_ref(), current);
            assert_eq!(actual.register_bytes, current.canonical_bytes());
            assert_eq!(actual.receipt_bytes, bytes);
            assert_eq!(actual.receipts.collections.len(), 1);
            let row = &actual.receipts.collections[0];
            assert_eq!(row.original_commitment_id, accepted.commitment_id);
            assert_eq!(row.command_nonce, accepted.command.nonce);
            assert_eq!(row.collected.micro_units(), 2);
            assert_eq!(row.performed_hours, 2);
        }
        let held = fixture::prepare(&session, None);
        assert!(encode(current, held.material().receipt_bytes(), &opening, chain).is_err());
        assert_eq!(session.material().completed_tick(), 0);
    }

    #[test]
    fn borrowed_register_witness_requires_exact_package_and_keeps_owned_fallback() {
        let session = fixture::authored_session(
            crate::michigan_dynamic_hex_foundation().unwrap(),
            fixture::config(),
            false,
            false,
        );
        let opening = OpeningRegister::from_opening(session.material()).unwrap();
        let chain = initial_lookup_chain(&opening).unwrap();
        let accepted = fixture::commitment(&session, OrganizerChoice::LocalAid);
        let candidate = fixture::prepare(&session, Some(&accepted));
        let current = candidate.material().register();
        let encoded = encode(
            current,
            candidate.material().receipt_bytes(),
            &opening,
            chain,
        )
        .unwrap();
        let loaded = read_period_lookup(
            &opening,
            1,
            &encoded.lookup_delta_bytes,
            LookupAnchor::Previous(chain),
        )
        .unwrap();
        let decode = |package: &[u8], witness| {
            decode_typed_with_witness(
                &opening,
                1,
                package,
                &encoded.receipt_storage_bytes,
                &loaded.lookup,
                loaded.chain,
                witness,
            )
        };
        let borrowed = decode(&encoded.register_storage_bytes, Some(current)).unwrap();
        assert!(matches!(borrowed.register, std::borrow::Cow::Borrowed(_)));
        assert!(std::ptr::eq(borrowed.register.as_ref(), current));
        assert_eq!(borrowed.register_bytes, current.canonical_bytes());
        assert!(!borrowed.receipts.aid.is_empty());
        let owned = decode(&encoded.register_storage_bytes, None).unwrap();
        assert!(matches!(owned.register, std::borrow::Cow::Owned(_)));
        assert_eq!(owned.register.as_ref(), current);
        assert_eq!(owned.receipt_bytes, borrowed.receipt_bytes);
        assert_eq!(owned.receipts, borrowed.receipts);
        assert_eq!(
            decode(&encoded.register_storage_bytes, Some(session.material())).err(),
            Some(Error::State(StorageError::Canonical))
        );
        let without_gift = fixture::prepare(&session, None);
        assert_eq!(
            decode(
                &encoded.register_storage_bytes,
                Some(without_gift.material().register())
            )
            .err(),
            Some(Error::State(StorageError::Canonical)),
        );
        let mut damaged = encoded.register_storage_bytes.clone();
        // Corrupt the package framing itself, not the borrowed typed witness.
        damaged[0] ^= 1;
        let borrowed_error = decode(&damaged, Some(current)).err().unwrap();
        assert_eq!(decode(&damaged, None).err(), Some(borrowed_error));
    }

    #[test]
    fn admitted_storage_values_keep_nonempty_aid_and_exact_canonical_inverse() {
        let session = fixture::authored_session(
            crate::michigan_dynamic_hex_foundation().unwrap(),
            fixture::config(),
            false,
            false,
        );
        let opening = OpeningRegister::from_opening(session.material()).unwrap();
        let chain = initial_lookup_chain(&opening).unwrap();
        let accepted = fixture::commitment(&session, OrganizerChoice::LocalAid);
        let candidate = fixture::prepare(&session, Some(&accepted));
        let current = candidate.material().register();
        let receipts = candidate.material().receipt_bytes();
        let encoded = encode(current, receipts, &opening, chain).unwrap();
        let loaded = read_period_lookup(
            &opening,
            1,
            &encoded.lookup_delta_bytes,
            LookupAnchor::Previous(chain),
        )
        .unwrap();
        let admitted = decode_typed(
            &opening,
            1,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes,
            &loaded.lookup,
            loaded.chain,
        )
        .unwrap();
        assert_eq!(admitted.register, *current);
        assert_eq!(admitted.register_bytes, current.canonical_bytes());
        assert_eq!(admitted.receipt_bytes, receipts);
        assert_eq!(
            admitted.receipts,
            decode_material_receipts(receipts).unwrap()
        );
        assert!(!admitted.receipts.aid.is_empty());
        assert_eq!(
            decode(
                &opening,
                1,
                &encoded.register_storage_bytes,
                &encoded.receipt_storage_bytes,
                &loaded.lookup,
                loaded.chain
            )
            .unwrap(),
            (admitted.register_bytes, admitted.receipt_bytes)
        );
        assert!(decode_typed(
            &opening,
            2,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes,
            &loaded.lookup,
            loaded.chain
        )
        .is_err());
        assert!(decode_typed(
            &opening,
            1,
            &encoded.register_storage_bytes[..encoded.register_storage_bytes.len() - 1],
            &encoded.receipt_storage_bytes,
            &loaded.lookup,
            loaded.chain
        )
        .is_err());
        assert!(decode_typed(
            &opening,
            1,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes[..encoded.receipt_storage_bytes.len() - 1],
            &loaded.lookup,
            loaded.chain
        )
        .is_err());
        assert!(decode_typed(
            &opening,
            1,
            &encoded.register_storage_bytes,
            &encoded.receipt_storage_bytes,
            &loaded.lookup,
            [0; 32]
        )
        .is_err());
    }
}
