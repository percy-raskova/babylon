//! Lossless storage of the one current complete V17 receipt format.
//! Canonical identities/hashes remain the authoritative evidence; this is a storage codec.
mod amount;
mod layout;
mod numeric;
use crate::state_storage::{StorageError, TypedLookup};
use crate::storage_compression::{compress_exact, decompress_exact, StorageCompressionError};
use babylon_kernel::content_digest::sha256_of;
use babylon_tick::material_world::{
    decode_material_receipts, receipt_row_limit, MaterialTickReceipts,
    MAX_MATERIAL_TICK_RECEIPT_BYTES, RECEIPT_FAMILY_COUNT, RECEIPT_ROW_BYTES,
};
const DOMAIN: &[u8] = b"BabylonReceiptStorageV2\0";
const CANONICAL_DOMAIN: &[u8] = b"babylon.material-tick-receipts.v17\0";
pub(crate) const MAX_RECEIPT_STORAGE_BYTES: usize =
    MAX_MATERIAL_TICK_RECEIPT_BYTES + DOMAIN.len() + 88 + RECEIPT_FAMILY_COUNT * 59;
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    Canonical,
    Tick,
    CollectionJoin,
    Domain,
    Family,
    Count,
    IdentityTag,
    Lookup(StorageError),
    Padding,
    Truncated,
    Trailing,
    Arithmetic,
    Allocation,
    Compression(StorageCompressionError),
    Hash,
    Width,
    Mode,
    LookupPrefix,
    AmountOrder,
    AmountIndex,
    UnusedAmount,
}
type Result<T> = std::result::Result<T, Error>;
fn buffer(n: usize) -> Result<Vec<u8>> {
    let mut v = Vec::new();
    v.try_reserve_exact(n).map_err(|_| Error::Allocation)?;
    Ok(v)
}
struct Cursor<'a> {
    bytes: &'a [u8],
    pos: usize,
}
impl<'a> Cursor<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        let end = self.pos.checked_add(n).ok_or(Error::Arithmetic)?;
        let b = self.bytes.get(self.pos..end).ok_or(Error::Truncated)?;
        self.pos = end;
        Ok(b)
    }
    fn u64(&mut self) -> Result<u64> {
        Ok(u64::from_be_bytes(
            self.take(8)?.try_into().map_err(|_| Error::Truncated)?,
        ))
    }
    fn u32(&mut self) -> Result<u32> {
        Ok(u32::from_be_bytes(
            self.take(4)?.try_into().map_err(|_| Error::Truncated)?,
        ))
    }
    fn byte(&mut self) -> Result<u8> {
        Ok(self.take(1)?[0])
    }
    fn done(&self) -> Result<()> {
        if self.pos == self.bytes.len() {
            Ok(())
        } else {
            Err(Error::Trailing)
        }
    }
}
fn transpose(bytes: &[u8], count: usize, width: usize, inverse: bool) -> Result<Vec<u8>> {
    let n = count.checked_mul(width).ok_or(Error::Arithmetic)?;
    if n != bytes.len() {
        return Err(Error::Width);
    }
    let mut out = buffer(n)?;
    out.resize(n, 0);
    for row in 0..count {
        for col in 0..width {
            let a = row * width + col;
            let b = col * count + row;
            if inverse {
                out[a] = bytes[b];
            } else {
                out[b] = bytes[a];
            }
        }
    }
    Ok(out)
}
fn pack_row(tag: u8, row: &[u8], lookup: &mut TypedLookup) -> Result<Vec<u8>> {
    let fields = layout::fields(tag)?;
    let mut out = buffer(row.len())?;
    let mut pos = 0;
    for f in fields {
        if f.offset < pos {
            return Err(Error::Width);
        }
        out.extend_from_slice(row.get(pos..f.offset).ok_or(Error::Width)?);
        let raw: [u8; 32] = row
            .get(f.offset..f.offset + 32)
            .ok_or(Error::Width)?
            .try_into()
            .map_err(|_| Error::Width)?;
        let reference = if let Some(kind) = layout::resolve_kind(f.kind, row)? {
            lookup
                .intern(kind, raw)
                .map_err(Error::Lookup)?
                .checked_add(1)
                .ok_or(Error::Arithmetic)?
        } else {
            if raw != [0; 32] {
                return Err(Error::Padding);
            }
            0
        };
        out.extend_from_slice(&reference.to_be_bytes());
        pos = f.offset + 32;
    }
    out.extend_from_slice(row.get(pos..).ok_or(Error::Width)?);
    Ok(out)
}
fn unpack_row(tag: u8, bytes: &[u8], lookup: &TypedLookup, prefix: usize) -> Result<Vec<u8>> {
    let fields = layout::fields(tag)?;
    let mut out = buffer(RECEIPT_ROW_BYTES[usize::from(tag) - 1])?;
    let mut pos = 0;
    let mut cursor = Cursor { bytes, pos: 0 };
    for f in fields {
        out.extend_from_slice(cursor.take(f.offset.checked_sub(pos).ok_or(Error::Width)?)?);
        let reference =
            u32::from_be_bytes(cursor.take(4)?.try_into().map_err(|_| Error::Truncated)?);
        let kind = layout::resolve_kind(f.kind, &out)?;
        let raw = match (kind, reference) {
            (Some(k), r) if r != 0 && usize::try_from(r).is_ok_and(|n| n <= prefix) => {
                lookup.resolve(r - 1, k).map_err(Error::Lookup)?
            }
            (None, 0) => [0; 32],
            _ => return Err(Error::Padding),
        };
        out.extend_from_slice(&raw);
        pos = f.offset + 32;
    }
    out.extend_from_slice(cursor.take(bytes.len() - cursor.pos)?);
    cursor.done()?;
    if out.len() != RECEIPT_ROW_BYTES[usize::from(tag) - 1] {
        return Err(Error::Width);
    }
    Ok(out)
}
// Uncompressed column bodies are transient; retain only their authenticated
// digest, chosen raw-or-zstd payload and physical interpretation metadata.
struct FamilyPayload {
    mode: u8,
    width: usize,
    amount_count: u32,
    compression: u8,
    digest: [u8; 32],
    payload: Vec<u8>,
}
fn stored_family(
    mode: u8,
    width: usize,
    amount_count: u32,
    columns: Vec<u8>,
) -> Result<FamilyPayload> {
    let digest = sha256_of(&columns);
    let compressed =
        compress_exact(&columns, MAX_MATERIAL_TICK_RECEIPT_BYTES).map_err(Error::Compression)?;
    let (compression, payload) = if compressed.len() < columns.len() {
        (1, compressed)
    } else {
        (0, columns)
    };
    Ok(FamilyPayload {
        mode,
        width,
        amount_count,
        compression,
        digest,
        payload,
    })
}
fn prefer_family(selected: FamilyPayload, candidate: FamilyPayload) -> FamilyPayload {
    if candidate.payload.len() < selected.payload.len() {
        candidate
    } else {
        selected
    }
}
fn encode_columns(
    tag: u8,
    rows: Vec<u8>,
    count: usize,
    packed_width: usize,
    tick: u64,
) -> Result<FamilyPayload> {
    let (mode, width, retained) = numeric::pack_family(tag, &rows, count, packed_width, tick)?;
    drop(rows);
    let selected = stored_family(mode, width, 0, transpose(&retained, count, width, false)?)?;
    if tag == 11 && mode == 1 {
        if let Some(packed) = amount::pack(&retained, count)? {
            let candidate = stored_family(
                2,
                amount::ROW_WIDTH,
                packed.dictionary_count,
                packed.columns,
            )?;
            return Ok(prefer_family(selected, candidate));
        }
    }
    Ok(selected)
}

fn family_length(
    tag: u8,
    mode: u8,
    width: usize,
    amount_count: u32,
    count: usize,
    packed_width: usize,
) -> Result<usize> {
    if mode == 2 {
        if tag != 11 {
            return Err(Error::Mode);
        }
        if width != amount::ROW_WIDTH {
            return Err(Error::Width);
        }
        return amount::decoded_length(count, amount_count);
    }
    if amount_count != 0 {
        return Err(Error::Count);
    }
    if width != numeric::retained_width(tag, mode, packed_width)? {
        return Err(Error::Width);
    }
    count.checked_mul(width).ok_or(Error::Arithmetic)
}

/// Borrowed proof of complete typed canonical receipt admission.
/// Private fields prevent callers from supplying unchecked bytes or a guessed tick.
pub(crate) struct AdmittedReceipts<'a> {
    canonical: &'a [u8],
    resolve_tick: u64,
}
impl<'a> AdmittedReceipts<'a> {
    pub(crate) fn new(
        canonical: &'a [u8],
        register: Option<&babylon_tick::material_world::MaterialWorldRegister>,
    ) -> Result<Self> {
        let decoded = decode_material_receipts(canonical).map_err(|_| Error::Canonical)?;
        if let Some(register) = register {
            if decoded.resolve_tick != register.completed_tick() {
                return Err(Error::Tick);
            }
            babylon_tick::material_world::validate_retained_collection(register, &decoded)
                .map_err(|_| Error::CollectionJoin)?;
        }
        let resolve_tick = decoded.resolve_tick;
        // Keep only the immutable original bytes and admitted tick, not decoded rows.
        drop(decoded);
        Ok(Self {
            canonical,
            resolve_tick,
        })
    }
    pub(crate) const fn resolve_tick(&self) -> u64 {
        self.resolve_tick
    }
}

/// Encode fully admitted bytes against a detached lookup. Publish appended
/// identities only with the tick marker; failures preserve the caller's lookup.
pub(crate) fn encode(admitted: &AdmittedReceipts<'_>, lookup: &mut TypedLookup) -> Result<Vec<u8>> {
    let canonical = admitted.canonical;
    let mut cursor = Cursor {
        bytes: canonical,
        pos: 0,
    };
    if cursor.take(CANONICAL_DOMAIN.len())? != CANONICAL_DOMAIN {
        return Err(Error::Domain);
    }
    if cursor.take(4)? != 17_u32.to_be_bytes() {
        return Err(Error::Domain);
    }
    let tick = cursor.u64()?;
    // Stage a clone so any codec failure leaves the caller's lookup unchanged.
    let mut entries = Vec::new();
    entries
        .try_reserve_exact(lookup.entries().len())
        .map_err(|_| Error::Allocation)?;
    entries.extend_from_slice(lookup.entries());
    let mut staged = TypedLookup::from_entries(entries).map_err(Error::Lookup)?;
    let mut out = buffer(canonical.len().min(1_048_576))?;
    out.extend_from_slice(DOMAIN);
    out.extend_from_slice(&(canonical.len() as u64).to_be_bytes());
    out.extend_from_slice(&sha256_of(canonical));
    out.extend_from_slice(&tick.to_be_bytes());
    let prefix_offset = out.len();
    out.extend_from_slice(&[0; 40]);
    for (index, &canonical_width) in RECEIPT_ROW_BYTES.iter().enumerate() {
        let tag = u8::try_from(index + 1).map_err(|_| Error::Family)?;
        if cursor.byte()? != tag {
            return Err(Error::Family);
        }
        let count = usize::try_from(cursor.u64()?).map_err(|_| Error::Count)?;
        if count > receipt_row_limit(index) {
            return Err(Error::Count);
        }
        let width = canonical_width;
        let body = cursor.take(count.checked_mul(width).ok_or(Error::Arithmetic)?)?;
        let packed_width = width
            .checked_sub(28 * layout::fields(tag)?.len())
            .ok_or(Error::Width)?;
        let mut rows = buffer(count.checked_mul(packed_width).ok_or(Error::Arithmetic)?)?;
        for row in body.chunks_exact(width) {
            rows.extend(pack_row(tag, row, &mut staged)?);
        }
        let FamilyPayload {
            mode,
            width: retained_width,
            amount_count,
            compression,
            digest,
            payload,
        } = encode_columns(tag, rows, count, packed_width, tick)?;
        out.push(tag);
        out.extend_from_slice(&(count as u64).to_be_bytes());
        out.push(mode);
        out.push(compression);
        // V2 retains the 59-byte family header while making dictionary extent explicit.
        out.extend_from_slice(
            &u32::try_from(retained_width)
                .map_err(|_| Error::Width)?
                .to_be_bytes(),
        );
        out.extend_from_slice(&amount_count.to_be_bytes());
        out.extend_from_slice(&digest);
        out.extend_from_slice(&(payload.len() as u64).to_be_bytes());
        out.extend_from_slice(&payload);
    }
    cursor.done()?;
    let count = staged.entries().len();
    let digest = staged
        .prefix_digest(count)
        .map_err(|_| Error::LookupPrefix)?;
    out[prefix_offset..prefix_offset + 8].copy_from_slice(&(count as u64).to_be_bytes());
    out[prefix_offset + 8..prefix_offset + 40].copy_from_slice(&digest);
    *lookup = staged;
    Ok(out)
}
struct Header {
    length: usize,
    expected: [u8; 32],
    tick: u64,
    prefix: usize,
}
fn decode_header(cursor: &mut Cursor<'_>, lookup: &TypedLookup) -> Result<Header> {
    let overhead = DOMAIN.len() + 88 + RECEIPT_FAMILY_COUNT * 59;
    if cursor.bytes.len()
        > MAX_MATERIAL_TICK_RECEIPT_BYTES
            .checked_add(overhead)
            .ok_or(Error::Arithmetic)?
    {
        return Err(Error::Count);
    }
    if cursor.take(DOMAIN.len())? != DOMAIN {
        return Err(Error::Domain);
    }
    let length = usize::try_from(cursor.u64()?).map_err(|_| Error::Count)?;
    if length > MAX_MATERIAL_TICK_RECEIPT_BYTES {
        return Err(Error::Count);
    }
    let expected: [u8; 32] = cursor.take(32)?.try_into().map_err(|_| Error::Truncated)?;
    let tick = cursor.u64()?;
    if tick == 0 {
        return Err(Error::Canonical);
    }
    let prefix = usize::try_from(cursor.u64()?).map_err(|_| Error::LookupPrefix)?;
    let prefix_hash: [u8; 32] = cursor.take(32)?.try_into().map_err(|_| Error::Truncated)?;
    if lookup
        .prefix_digest(prefix)
        .map_err(|_| Error::LookupPrefix)?
        != prefix_hash
    {
        return Err(Error::LookupPrefix);
    }
    Ok(Header {
        length,
        expected,
        tick,
        prefix,
    })
}
/// Authenticate and reconstruct all canonical bytes before typed receipt validation.
pub(crate) fn decode_admitted(
    encoded: &[u8],
    lookup: &TypedLookup,
) -> Result<(Vec<u8>, MaterialTickReceipts)> {
    let mut cursor = Cursor {
        bytes: encoded,
        pos: 0,
    };
    let Header {
        length,
        expected,
        tick,
        prefix,
    } = decode_header(&mut cursor, lookup)?;
    let mut out = buffer(length)?;
    out.extend_from_slice(CANONICAL_DOMAIN);
    out.extend_from_slice(&17_u32.to_be_bytes());
    out.extend_from_slice(&tick.to_be_bytes());
    for (index, &canonical_width) in RECEIPT_ROW_BYTES.iter().enumerate() {
        let tag = u8::try_from(index + 1).map_err(|_| Error::Family)?;
        if cursor.byte()? != tag {
            return Err(Error::Family);
        }
        let count = usize::try_from(cursor.u64()?).map_err(|_| Error::Count)?;
        if count > receipt_row_limit(index) {
            return Err(Error::Count);
        }
        let canonical_body = count
            .checked_mul(canonical_width)
            .ok_or(Error::Arithmetic)?;
        if out
            .len()
            .checked_add(9)
            .and_then(|n| n.checked_add(canonical_body))
            .is_none_or(|n| n > length)
        {
            return Err(Error::Count);
        }
        let mode = cursor.byte()?;
        let compression = cursor.byte()?;
        let width = usize::try_from(cursor.u32()?).map_err(|_| Error::Width)?;
        let amount_count = cursor.u32()?;
        let packed_width = canonical_width
            .checked_sub(28 * layout::fields(tag)?.len())
            .ok_or(Error::Width)?;
        let n = family_length(tag, mode, width, amount_count, count, packed_width)?;
        let digest: [u8; 32] = cursor.take(32)?.try_into().map_err(|_| Error::Truncated)?;
        let payload_len = usize::try_from(cursor.u64()?).map_err(|_| Error::Count)?;
        if payload_len > MAX_MATERIAL_TICK_RECEIPT_BYTES {
            return Err(Error::Count);
        }
        let payload = cursor.take(payload_len)?;
        let columns = match compression {
            0 => {
                if payload.len() != n || sha256_of(payload) != digest {
                    return Err(Error::Hash);
                }
                payload.to_vec()
            }
            1 => decompress_exact(payload, n, digest, MAX_MATERIAL_TICK_RECEIPT_BYTES)
                .map_err(Error::Compression)?,
            _ => return Err(Error::Mode),
        };
        let (row_mode, row_width, rows) = if mode == 2 {
            (1, 30, amount::unpack(&columns, count, amount_count)?)
        } else {
            (mode, width, transpose(&columns, count, width, true)?)
        };
        out.push(tag);
        out.extend_from_slice(&(count as u64).to_be_bytes());
        for row in rows.chunks_exact(row_width) {
            let packed = numeric::unpack_row(tag, row_mode, row, tick, packed_width)?;
            out.extend(unpack_row(tag, &packed, lookup, prefix)?);
            if out.len() > length {
                return Err(Error::Count);
            }
        }
    }
    cursor.done()?;
    if out.len() != length || sha256_of(&out) != expected {
        return Err(Error::Hash);
    }
    let admitted = decode_material_receipts(&out).map_err(|_| Error::Canonical)?;
    Ok((out, admitted))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state_storage::IdentityKind;
    // Actual raw-input codec controls still perform the complete fallible admission.
    fn encode_raw(bytes: &[u8], lookup: &mut TypedLookup) -> Result<Vec<u8>> {
        encode(&AdmittedReceipts::new(bytes, None)?, lookup)
    }
    // Existing byte-level malformed/inverse controls need only canonical bytes.
    fn decode(encoded: &[u8], lookup: &TypedLookup) -> Result<Vec<u8>> {
        Ok(decode_admitted(encoded, lookup)?.0)
    }

    fn empty_receipts() -> Vec<u8> {
        let mut bytes = CANONICAL_DOMAIN.to_vec();
        bytes.extend_from_slice(&17_u32.to_be_bytes());
        bytes.extend_from_slice(&1_u64.to_be_bytes());
        for tag in 1..=36 {
            bytes.push(tag);
            bytes.extend_from_slice(&0_u64.to_be_bytes());
        }
        bytes
    }
    #[test]
    fn complete_empty_receipts_survive_later_lookup_appends() {
        let original = empty_receipts();
        let mut lookup = TypedLookup::default();
        lookup.intern(IdentityKind::Site, [1; 32]).unwrap();
        let encoded = encode_raw(&original, &mut lookup).unwrap();
        lookup.intern(IdentityKind::Site, [2; 32]).unwrap();
        assert_eq!(decode(&encoded, &lookup).unwrap(), original);
        let mut changed = TypedLookup::default();
        changed.intern(IdentityKind::Site, [3; 32]).unwrap();
        assert_eq!(decode(&encoded, &changed), Err(Error::LookupPrefix));
    }
    #[test]
    fn malformed_receipts_leave_lookup_unchanged_and_trailing_data_refuses() {
        let mut lookup = TypedLookup::default();
        lookup.intern(IdentityKind::PublicAccount, [7; 32]).unwrap();
        let before = lookup.entries().to_vec();
        let mut original = empty_receipts();
        original.push(0);
        assert!(encode_raw(&original, &mut lookup).is_err());
        assert_eq!(lookup.entries(), before);
        let mut encoded = encode_raw(&empty_receipts(), &mut lookup).unwrap();
        encoded.push(0);
        assert_eq!(decode(&encoded, &lookup), Err(Error::Trailing));
    }
    #[test]
    fn typed_references_cannot_read_beyond_authenticated_prefix() {
        let mut lookup = TypedLookup::default();
        let mut row = vec![0; RECEIPT_ROW_BYTES[0]];
        row[..32].fill(1);
        row[32..64].fill(2);
        let packed = pack_row(1, &row, &mut lookup).unwrap();
        assert_eq!(unpack_row(1, &packed, &lookup, 2).unwrap(), row);
        assert!(unpack_row(1, &packed, &lookup, 1).is_err());
        let mut wrong = TypedLookup::default();
        wrong.intern(IdentityKind::Site, [1; 32]).unwrap();
        wrong.intern(IdentityKind::Site, [2; 32]).unwrap();
        assert!(unpack_row(1, &packed, &wrong, 2).is_err());
    }
    fn authored_aid_row(routed: bool) -> Vec<u8> {
        let mut row = Vec::new();
        let commitment = babylon_material_circuit::aid_commitment_id([3; 32], 1);
        row.extend_from_slice(&commitment.as_bytes());
        row.extend_from_slice(&[3; 32]);
        row.extend_from_slice(&1_u64.to_be_bytes());
        row.extend_from_slice(&1_u64.to_be_bytes());
        row.push(if routed { 2 } else { 1 });
        for id in if routed { [9, 10, 11] } else { [0, 0, 0] } {
            row.extend_from_slice(&[id; 32]);
        }
        row.push(2);
        for id in [5, 5, 6, 8, 7] {
            row.extend_from_slice(&[id; 32]);
        }
        row.push(if routed { 2 } else { 3 });
        row.extend_from_slice(&2_u64.to_be_bytes());
        row.extend_from_slice(&7_i128.to_be_bytes());
        row.extend_from_slice(&10_i128.to_be_bytes());
        row.extend_from_slice(&4_u64.to_be_bytes());
        assert_eq!(row.len(), 387);
        row
    }

    #[test]
    fn nonempty_local_and_routed_aid_reconstruct_all_exact_bytes() {
        for routed in [false, true] {
            let row = authored_aid_row(routed);
            let mut lookup = TypedLookup::default();
            let packed = pack_row(35, &row, &mut lookup).unwrap();
            assert_eq!(packed.len(), 107);
            let prefix = lookup.entries().len();
            assert_eq!(prefix, if routed { 9 } else { 6 });
            assert_eq!(&packed[4..8], &2_u32.to_be_bytes());
            assert_eq!(lookup.entries()[1].kind, IdentityKind::AidMandate);
            if !routed {
                assert_eq!(&packed[25..37], &[0; 12]);
            }
            assert_eq!(unpack_row(35, &packed, &lookup, prefix).unwrap(), row);
            let mut envelope = empty_receipts();
            // Aid remains family35; current framing also contains empty family36.
            let count = CANONICAL_DOMAIN.len() + 4 + 8 + (35 - 1) * 9 + 1;
            assert_eq!(envelope[count - 1], 35);
            envelope[count..count + 8].copy_from_slice(&1_u64.to_be_bytes());
            envelope.splice(count + 8..count + 8, row);
            let encoded = encode_raw(&envelope, &mut lookup).unwrap();
            assert_eq!(decode(&encoded, &lookup).unwrap(), envelope);
            lookup.intern(IdentityKind::AidMandate, [12; 32]).unwrap();
            assert_eq!(decode(&encoded, &lookup).unwrap(), envelope);
        }
    }

    #[test]
    fn aid_refs_refuse_wrong_domain_absent_and_future_identities() {
        let row = authored_aid_row(true);
        let mut lookup = TypedLookup::default();
        let packed = pack_row(35, &row, &mut lookup).unwrap();
        let prefix = lookup.entries().len();
        let mut entries = lookup.entries().to_vec();
        entries[1].kind = IdentityKind::Order;
        let wrong = TypedLookup::from_entries(entries).unwrap();
        assert_eq!(
            unpack_row(35, &packed, &wrong, prefix),
            Err(Error::Lookup(StorageError::IdentityKind))
        );
        for reference in [0, u32::try_from(prefix + 1).unwrap(), u32::MAX] {
            let mut damaged = packed.clone();
            damaged[4..8].copy_from_slice(&reference.to_be_bytes());
            assert_eq!(
                unpack_row(35, &damaged, &lookup, prefix),
                Err(Error::Padding)
            );
        }
        assert_eq!(
            unpack_row(35, &packed, &lookup, prefix - 1),
            Err(Error::Padding)
        );
    }

    #[test]
    fn local_aid_padding_is_not_an_identity_or_a_hidden_route() {
        let row = authored_aid_row(false);
        let mut lookup = TypedLookup::default();
        let packed = pack_row(35, &row, &mut lookup).unwrap();
        let prefix = lookup.entries().len();
        for (raw_offset, packed_offset) in [(81, 25), (113, 29), (145, 33)] {
            let mut raw = row.clone();
            raw[raw_offset] = 1;
            assert_eq!(pack_row(35, &raw, &mut lookup), Err(Error::Padding));
            let mut damaged = packed.clone();
            damaged[packed_offset..packed_offset + 4].copy_from_slice(&1_u32.to_be_bytes());
            assert_eq!(
                unpack_row(35, &damaged, &lookup, prefix),
                Err(Error::Padding)
            );
        }
        let mut bad_transport = row;
        bad_transport[80] = 3;
        assert_eq!(
            pack_row(35, &bad_transport, &mut lookup),
            Err(Error::IdentityTag)
        );
    }

    fn amount_receipts(amounts: &[i128]) -> Vec<u8> {
        let mut bytes = CANONICAL_DOMAIN.to_vec();
        bytes.extend_from_slice(&17_u32.to_be_bytes());
        bytes.extend_from_slice(&7_u64.to_be_bytes());
        for tag in 1..=36 {
            bytes.push(tag);
            bytes
                .extend_from_slice(&if tag == 11 { amounts.len() as u64 } else { 0 }.to_be_bytes());
            if tag != 11 {
                continue;
            }
            for (index, amount) in amounts.iter().enumerate() {
                let purpose = u8::try_from(index % 10 + 1).unwrap();
                let (subtype, id, reserve_tag) = match purpose {
                    1..=3 => (1, [19; 32], 2),
                    4..=6 => (0, [20; 32], 3),
                    7 => (7, [0; 32], 0),
                    _ => (0, [21; 32], 4),
                };
                bytes.extend_from_slice(&[purpose, subtype]);
                bytes.extend_from_slice(&id);
                let mut cash = vec![1, 3];
                cash.extend_from_slice(&[9; 32]);
                let mut recipient = vec![1, 2];
                recipient.extend_from_slice(&[8; 32]);
                let mut reserve = vec![reserve_tag, u8::from(reserve_tag == 2)];
                reserve.extend_from_slice(&id);
                let (from, to) = if purpose == 7 {
                    (cash, recipient)
                } else if matches!(purpose, 1 | 4 | 8) {
                    (cash, reserve)
                } else {
                    (reserve, recipient)
                };
                bytes.extend(from);
                bytes.extend_from_slice(&(-amount).to_be_bytes());
                bytes.extend(to);
                bytes.extend_from_slice(&amount.to_be_bytes());
            }
        }
        bytes
    }

    fn money_family_offset() -> usize {
        DOMAIN.len() + 88 + 10 * 59
    }

    fn money_columns(encoded: &[u8]) -> (usize, u32, Vec<u8>) {
        let start = money_family_offset();
        assert_eq!(
            encoded[start + 9],
            2,
            "actual encoder must factor repeated amounts"
        );
        assert_eq!(&encoded[start + 11..start + 15], &18_u32.to_be_bytes());
        let count = usize::try_from(u64::from_be_bytes(
            encoded[start + 1..start + 9].try_into().unwrap(),
        ))
        .unwrap();
        let unique = u32::from_be_bytes(encoded[start + 15..start + 19].try_into().unwrap());
        let length = count * 18 + usize::try_from(unique).unwrap() * 16;
        let digest = encoded[start + 19..start + 51].try_into().unwrap();
        let payload_length = usize::try_from(u64::from_be_bytes(
            encoded[start + 51..start + 59].try_into().unwrap(),
        ))
        .unwrap();
        let payload = &encoded[start + 59..start + 59 + payload_length];
        let columns = if encoded[start + 10] == 1 {
            decompress_exact(payload, length, digest, MAX_MATERIAL_TICK_RECEIPT_BYTES).unwrap()
        } else {
            assert_eq!(sha256_of(payload), digest);
            payload.to_vec()
        };
        (count, unique, columns)
    }

    fn money_package_with_columns(encoded: &[u8], columns: &[u8]) -> Vec<u8> {
        let start = money_family_offset();
        let old_length = usize::try_from(u64::from_be_bytes(
            encoded[start + 51..start + 59].try_into().unwrap(),
        ))
        .unwrap();
        let mut out = encoded[..start + 59].to_vec();
        out[start + 10] = 0;
        out[start + 19..start + 51].copy_from_slice(&sha256_of(columns));
        out[start + 51..start + 59].copy_from_slice(&(columns.len() as u64).to_be_bytes());
        out.extend_from_slice(columns);
        out.extend_from_slice(&encoded[start + 59 + old_length..]);
        out
    }

    #[test]
    fn amount_dictionary_preserves_all_purposes_cash_bits_and_original_order() {
        let high = (1_i128 << 100) + 3;
        let amounts = [i128::MAX, 1, 1, i128::MAX, high, 1, i128::MAX, high, 1, 1];
        let original = amount_receipts(&amounts);
        let mut lookup = TypedLookup::default();
        let encoded = encode_raw(&original, &mut lookup).unwrap();
        let (count, unique, columns) = money_columns(&encoded);
        assert!(encoded.starts_with(b"BabylonReceiptStorageV2\0"));
        assert_eq!((count, unique), (10, 3));
        for (index, expected) in [1_i128, high, i128::MAX].into_iter().enumerate() {
            let mut exact = [0; 16];
            for (column, byte) in exact.iter_mut().enumerate() {
                *byte = columns[count * 14 + column * 3 + index];
            }
            assert_eq!(i128::from_be_bytes(exact), expected);
        }
        let (restored, typed) = decode_admitted(&encoded, &lookup).unwrap();
        assert_eq!(restored, original);
        assert_eq!(sha256_of(&restored), sha256_of(&original));
        assert_eq!(
            typed
                .money_transfers
                .iter()
                .map(|row| row.credit.delta.micro_units())
                .collect::<Vec<_>>(),
            amounts
        );
        assert_eq!(
            typed
                .money_transfers
                .iter()
                .map(|row| row.debit.delta.micro_units())
                .collect::<Vec<_>>(),
            amounts.map(|amount| -amount)
        );
        let mut independent = TypedLookup::default();
        assert_eq!(encode_raw(&original, &mut independent).unwrap(), encoded);
        lookup
            .intern(IdentityKind::PublicAccount, [99; 32])
            .unwrap();
        assert_eq!(decode(&encoded, &lookup).unwrap(), original);
    }

    #[test]
    fn unsupported_receipt_storage_domain_refuses_before_body() {
        let mut lookup = TypedLookup::default();
        let mut encoded = encode_raw(&empty_receipts(), &mut lookup).unwrap();
        encoded[..b"BabylonReceiptStorageV1\0".len()].copy_from_slice(b"BabylonReceiptStorageV1\0");
        assert_eq!(decode(&encoded, &lookup), Err(Error::Domain));
    }

    #[test]
    fn exact_money_rows_without_repetition_use_current_numeric_storage() {
        let original = amount_receipts(&[1, i128::MAX]);
        let mut lookup = TypedLookup::default();
        let encoded = encode_raw(&original, &mut lookup).unwrap();
        assert!(encoded.starts_with(b"BabylonReceiptStorageV2\0"));
        let start = money_family_offset();
        assert_eq!(encoded[start + 9], 1);
        assert_eq!(&encoded[start + 11..start + 15], &30_u32.to_be_bytes());
        assert_eq!(&encoded[start + 15..start + 19], &0_u32.to_be_bytes());
        assert_eq!(decode(&encoded, &lookup).unwrap(), original);
    }

    #[test]
    fn amount_dictionary_damaged_claims_refuse_through_complete_decoder() {
        let original = amount_receipts(&[1, 7, 1, 7, i128::MAX, 7, 1, 1, 1, 7]);
        let mut lookup = TypedLookup::default();
        let encoded = encode_raw(&original, &mut lookup).unwrap();
        let (count, unique, columns) = money_columns(&encoded);
        assert_eq!(unique, 3);
        let dictionary = count * 14;
        let references = dictionary + 3 * 16;
        for fault in 0..7 {
            let mut changed = columns.clone();
            match fault {
                0 => {
                    for column in 0..16 {
                        changed[dictionary + column * 3 + 1] = changed[dictionary + column * 3];
                    }
                }
                1 => {
                    for column in 0..16 {
                        changed.swap(dictionary + column * 3, dictionary + column * 3 + 1);
                    }
                }
                2 => {
                    for column in 0..16 {
                        changed[dictionary + column * 3] = 0;
                    }
                }
                3 => {
                    changed[dictionary] = 128;
                }
                4 => {
                    for (column, byte) in unique.to_be_bytes().into_iter().enumerate() {
                        changed[references + column * count] = byte;
                    }
                }
                5 => {
                    changed[references..].fill(0);
                }
                _ => {
                    changed[12 * count] = 1;
                }
            }
            // Updating the family digest cannot authenticate an invalid dictionary/context.
            let damaged = money_package_with_columns(&encoded, &changed);
            assert!(
                decode(&damaged, &lookup).is_err(),
                "dictionary/context fault {fault}"
            );
        }
        for claim in [0, u32::MAX] {
            let mut damaged = encoded.clone();
            let start = money_family_offset();
            damaged[start + 15..start + 19].copy_from_slice(&claim.to_be_bytes());
            assert!(decode(&damaged, &lookup).is_err());
        }
        let mut wrong_family = encoded.clone();
        let first = DOMAIN.len() + 88;
        wrong_family[first + 15..first + 19].copy_from_slice(&1_u32.to_be_bytes());
        assert!(decode(&wrong_family, &lookup).is_err());
        let mut appended = encoded.clone();
        appended.push(0);
        assert!(decode(&appended, &lookup).is_err());
        assert!(decode(&encoded[..encoded.len() - 1], &lookup).is_err());
    }

    fn selection_direct_gift_receipts(amounts: &[i128]) -> Vec<u8> {
        let mut bytes = amount_receipts(amounts);
        let start = CANONICAL_DOMAIN.len() + 12 + 10 * 9 + 9;
        let width = RECEIPT_ROW_BYTES[10];
        assert_eq!(width, 134);
        for (row, amount) in bytes[start..start + amounts.len() * width]
            .chunks_exact_mut(width)
            .zip(amounts)
        {
            row[..34].fill(0);
            row[0] = 7;
            row[1] = 7;
            row[34..68].fill(9);
            row[34..36].copy_from_slice(&[1, 3]);
            row[68..84].copy_from_slice(&(-amount).to_be_bytes());
            row[84..118].fill(8);
            row[84..86].copy_from_slice(&[1, 2]);
            row[118..134].copy_from_slice(&amount.to_be_bytes());
        }
        bytes
    }
    // Independently measure both complete physical bodies using the already
    // governed numeric/dictionary encodings and existing zstd3 frame primitive.
    fn selection_payload_lengths(canonical: &[u8], lookup: &TypedLookup) -> (usize, usize, u32) {
        let start = CANONICAL_DOMAIN.len() + 12 + 10 * 9;
        let count = usize::try_from(u64::from_be_bytes(
            canonical[start + 1..start + 9].try_into().unwrap(),
        ))
        .unwrap();
        let body = &canonical[start + 9..start + 9 + count * RECEIPT_ROW_BYTES[10]];
        let mut lookup = lookup.clone();
        let mut rows = Vec::new();
        for row in body.chunks_exact(RECEIPT_ROW_BYTES[10]) {
            rows.extend(pack_row(11, row, &mut lookup).unwrap());
        }
        let (_, width, retained) = numeric::pack_family(11, &rows, count, 50, 7).unwrap();
        let columns = transpose(&retained, count, width, false).unwrap();
        let numeric = columns.len().min(
            compress_exact(&columns, MAX_MATERIAL_TICK_RECEIPT_BYTES)
                .unwrap()
                .len(),
        );
        let dictionary = amount::pack(&retained, count).unwrap().unwrap();
        let candidate = dictionary.columns.len().min(
            compress_exact(&dictionary.columns, MAX_MATERIAL_TICK_RECEIPT_BYTES)
                .unwrap()
                .len(),
        );
        (numeric, candidate, dictionary.dictionary_count)
    }
    #[test]
    fn amount_selection_uses_actual_stored_payload_and_never_increases_compressible_families() {
        let mut fallbacks = 0;
        for count in [8, 16, 128, 1024] {
            let sequential = (1..=count / 2)
                .map(|amount| i128::try_from(amount).unwrap())
                .cycle()
                .take(count)
                .collect::<Vec<_>>();
            let repeated = vec![1_i128; count];
            for amounts in [sequential, repeated] {
                let original = selection_direct_gift_receipts(&amounts);
                let mut lookup = TypedLookup::default();
                let encoded = encode_raw(&original, &mut lookup).unwrap();
                let (numeric, candidate, unique) = selection_payload_lengths(&original, &lookup);
                let start = money_family_offset();
                let payload = usize::try_from(u64::from_be_bytes(
                    encoded[start + 51..start + 59].try_into().unwrap(),
                ))
                .unwrap();
                eprintln!("amount_selection rows={count} numeric_payload={numeric} dictionary_payload={candidate} selected_payload={payload} selected_mode={}", encoded[start+9]);
                assert_eq!(
                    payload,
                    numeric.min(candidate),
                    "actual payload increased for {count} rows"
                );
                if candidate < numeric {
                    assert_eq!(encoded[start + 9], 2);
                    assert_eq!(&encoded[start + 15..start + 19], &unique.to_be_bytes());
                } else {
                    fallbacks += 1;
                    assert_eq!(
                        encoded[start + 9],
                        1,
                        "smaller raw dictionary is not sufficient after compression"
                    );
                    assert_eq!(&encoded[start + 11..start + 15], &30_u32.to_be_bytes());
                    assert_eq!(&encoded[start + 15..start + 19], &0_u32.to_be_bytes());
                }
                assert_eq!(decode_admitted(&encoded, &lookup).unwrap().0, original);
            }
        }
        assert!(
            fallbacks > 0,
            "crafted compression-regression controls must exercise actual numeric fallback"
        );
        // The measured national distribution is separate. No candidate-win
        // frequency is asserted for these intentionally compressible fixtures.
    }
    #[test]
    fn amount_selection_reports_existing_all_purpose_fixture_payloads() {
        let high = (1_i128 << 100) + 3;
        for (name, amounts) in [
            (
                "exact_order_ten_rows",
                [i128::MAX, 1, 1, i128::MAX, high, 1, i128::MAX, high, 1, 1],
            ),
            (
                "dictionary_refusal_ten_rows",
                [1, 7, 1, 7, i128::MAX, 7, 1, 1, 1, 7],
            ),
        ] {
            let original = amount_receipts(&amounts);
            let mut lookup = TypedLookup::default();
            let encoded = encode_raw(&original, &mut lookup).unwrap();
            let (numeric, dictionary, _) = selection_payload_lengths(&original, &lookup);
            let start = money_family_offset();
            let payload = usize::try_from(u64::from_be_bytes(
                encoded[start + 51..start + 59].try_into().unwrap(),
            ))
            .unwrap();
            eprintln!("amount_selection fixture={name} rows=10 numeric_payload={numeric} dictionary_payload={dictionary} selected_payload={payload} selected_mode={}", encoded[start+9]);
            assert_eq!(payload, numeric.min(dictionary));
            assert_eq!(encoded[start + 9], if dictionary < numeric { 2 } else { 1 });
            assert_eq!(decode_admitted(&encoded, &lookup).unwrap().0, original);
        }
    }

    #[test]
    fn amount_selection_ties_keep_numeric_mode_and_raw_frame_ties_keep_raw() {
        let selected = stored_family(1, 30, 0, vec![]).unwrap();
        assert_eq!(selected.compression, 0);
        let candidate = stored_family(2, 18, 1, vec![]).unwrap();
        let winner = prefer_family(selected, candidate);
        assert_eq!(winner.mode, 1);
        assert_eq!(winner.amount_count, 0);
    }
}
