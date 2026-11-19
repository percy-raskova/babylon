//! Site-local evidence held independently in the period marker's sorted directory.
use super::statement_lines::Lines;
use super::JournalError;
use crate::identity::CampaignId;
use crate::site_financial_statements::{SiteStatementSummary, SiteStockBalance, SiteStockPosition};
use babylon_material_circuit::SiteId;
use sha2::{Digest, Sha256};

pub(super) struct SiteEvidence {
    pub campaign: CampaignId,
    pub tick: u64,
    pub foundation: [u8; 32],
    pub content: [u8; 32],
    pub receipts: [u8; 32],
}

fn point(hash: &mut Sha256, position: Option<SiteStockPosition>) {
    if let Some(p) = position {
        hash.update([1]);
        hash.update(p.quantity.to_be_bytes());
        if let Some(cost) = p.carrying_cost {
            hash.update([1]);
            hash.update(cost.micro_units().to_be_bytes());
        } else {
            hash.update([0]);
        }
    } else {
        hash.update([0]);
    }
}

impl SiteEvidence {
    pub(super) fn fingerprint(
        &self,
        site: SiteId,
        statement: Option<&SiteStatementSummary>,
        stocks: &[SiteStockBalance],
    ) -> Result<[u8; 32], JournalError> {
        let mut hash = Sha256::new();
        hash.update(b"babylon.site-accounting.site.v1\0");
        hash.update(self.campaign.canonical_bytes());
        hash.update(self.tick.to_be_bytes());
        hash.update(self.foundation);
        hash.update(self.content);
        hash.update(self.receipts);
        hash.update(site.as_bytes());
        hash.update([u8::from(statement.is_some())]);
        if let Some(s) = statement {
            hash.update(
                serde_json::to_vec(&Lines::from_summary(s))
                    .map_err(|_| JournalError::Projection)?,
            );
        }
        hash.update([0]);
        for stock in stocks {
            hash.update(stock.good_id.as_bytes());
            hash.update(stock.unit_id.as_bytes());
            point(&mut hash, stock.opening);
            point(&mut hash, stock.closing);
        }
        Ok(hash.finalize().into())
    }
}

/// The ordinary point read checks just one 64-byte directory entry.
pub(super) fn matches(entry: &[u8], site: SiteId, digest: &[u8; 32]) -> bool {
    entry.len() == 64 && entry[..32] == site.as_bytes() && entry[32..] == digest[..]
}

/// Used only on a missing site row to distinguish an unknown site from corrupt storage.
pub(super) fn contains(
    directory: &[u8],
    expected: &[u8; 32],
    site: SiteId,
) -> Result<bool, JournalError> {
    let digest: [u8; 32] = Sha256::digest(directory).into();
    let (entries, remainder) = directory.as_chunks::<64>();
    if digest != *expected || !remainder.is_empty() {
        return Err(JournalError::Projection);
    }
    Ok(entries
        .binary_search_by(|entry| entry[..32].cmp(&site.as_bytes()))
        .is_ok())
}
