//! Immutable typed receipts bound only after complete storage admission.
use super::{Error, Result, TypedLookup};
use crate::receipt_storage;
use babylon_kernel::content_digest;
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};
use std::sync::Arc;

#[derive(Clone)]
pub(crate) struct AdmittedReceiptWitness {
    receipts: Arc<MaterialTickReceipts>,
    storage_digest: [u8; 32],
    lookup_identity: (usize, [u8; 32]),
    lookup_chain: [u8; 32],
}

impl AdmittedReceiptWitness {
    pub(super) fn new(
        receipts: Arc<MaterialTickReceipts>,
        package: &[u8],
        lookup: &TypedLookup,
        lookup_chain: [u8; 32],
    ) -> Result<Self> {
        Ok(Self {
            receipts,
            storage_digest: content_digest::sha256_of(package),
            lookup_identity: super::lookup_identity(lookup)?,
            lookup_chain,
        })
    }

    pub(super) fn restore(
        &self,
        tick: u64,
        package: &[u8],
        lookup: &TypedLookup,
        chain: [u8; 32],
    ) -> Result<(Vec<u8>, Arc<MaterialTickReceipts>)> {
        if self.receipts.resolve_tick != tick {
            return Err(Error::Tick);
        }
        if self.lookup_chain != chain || self.lookup_identity != super::lookup_identity(lookup)? {
            return Err(Error::LookupChain);
        }
        if self.storage_digest != content_digest::sha256_of(package) {
            return Err(Error::ReceiptWitness);
        }
        // Every frame, bound, compressed family and canonical digest is checked
        // afresh. Exact input equality permits reuse of its admitted typed owner.
        let canonical = receipt_storage::restore_canonical(package, lookup)?;
        Ok((canonical, Arc::clone(&self.receipts)))
    }
}

#[derive(Clone, Copy, Default)]
pub(crate) struct MaterialStorageWitnesses<'a> {
    pub(crate) register: Option<&'a MaterialWorldRegister>,
    pub(crate) receipt: Option<&'a AdmittedReceiptWitness>,
}
