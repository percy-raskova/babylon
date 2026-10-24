//! Resolve frozen citations through exact campaign-owned physical definitions.
use postgres::GenericClient;

use crate::identity::CampaignId;
use crate::{ArchiveCitation, SemanticArchiveError};

pub(crate) fn resolve_ordered(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    citations: &[&ArchiveCitation],
) -> Result<Vec<i32>, SemanticArchiveError> {
    let sources = citations
        .iter()
        .map(|citation| citation.source_id())
        .collect::<Vec<_>>();
    let locators = citations
        .iter()
        .map(|citation| citation.locator())
        .collect::<Vec<_>>();
    let row = client
        .query_one(
            "SELECT ARRAY(SELECT CASE WHEN count(provenance.provenance_ref)=1 \
             THEN min(provenance.provenance_ref) ELSE 0 END \
         FROM unnest($2::text[],$3::text[]) WITH ORDINALITY member(source,location,position) \
         LEFT JOIN babylon_meta.archive_provenance_v1 provenance \
           ON provenance.campaign_id=$1::uuid \
          AND (ARRAY[provenance.source_id,provenance.locator] COLLATE \"C\") \
            =(ARRAY[member.source,member.location] COLLATE \"C\") \
          AND provenance.source_id=member.source COLLATE \"C\" \
          AND provenance.locator=member.location COLLATE \"C\" \
         GROUP BY member.position ORDER BY member.position)",
            &[campaign.as_uuid(), &sources, &locators],
        )
        .map_err(|error| {
            crate::archive::database("resolve ordered exact Archive provenance", &error)
        })?;
    let references: Vec<i32> = row
        .try_get(0)
        .map_err(|error| crate::archive::database("read Archive provenance references", &error))?;
    if references.len() != citations.len() || references.iter().any(|reference| *reference <= 0) {
        return Err(SemanticArchiveError::StoredPageMismatch);
    }
    Ok(references)
}
