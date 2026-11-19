//! Normalize the immutable, admitted opening ownership once per campaign.
use super::rows::{Claim, Member, Parent, Source};
use crate::money_journal::payment_storage::Admission;
use crate::money_journal::statement_storage::{self, Batch, JournalPeriodSource, Table};
use crate::money_journal::JournalError;
use crate::national_economy::companies::{CompanyCapture, CompanyFinances};
use postgres::Transaction;
use serde::Serialize;
use std::collections::BTreeMap;
use uuid::Uuid;

struct CompanyDirectory<'a> {
    roster: &'a CompanyCapture,
    finances: &'a CompanyFinances,
}

#[derive(Serialize)]
struct Bound<'a, T> {
    campaign_id: &'a str,
    foundation_sha256: &'a str,
    #[serde(flatten)]
    row: T,
}

struct Binding {
    campaign: String,
    digest: String,
}
impl Binding {
    fn row<T>(&self, row: T) -> Bound<'_, T> {
        Bound {
            campaign_id: &self.campaign,
            foundation_sha256: &self.digest,
            row,
        }
    }
}

impl CompanyDirectory<'_> {
    fn counts(&self) -> [usize; 3] {
        [
            self.roster.companies.len(),
            self.roster.members.len(),
            self.finances.sources.len(),
        ]
    }
    fn stage(
        &self,
        batch: &mut Batch<'_, '_>,
        key: &Binding,
        campaign: &Uuid,
    ) -> Result<(), JournalError> {
        let treasury: BTreeMap<_, _> = self
            .finances
            .treasuries
            .iter()
            .map(|r| (r.company, r))
            .collect();
        let funding: BTreeMap<_, _> = self.finances.members.iter().map(|r| (r.site, r)).collect();
        if treasury.len() != self.roster.companies.len()
            || funding.len() != self.roster.members.len()
        {
            return Err(JournalError::Projection);
        }
        let parents = self
            .roster
            .companies
            .iter()
            .map(|r| {
                let t = treasury.get(&r.key.id()).ok_or(JournalError::Projection)?;
                Ok(key.row(Parent::new(r, t)))
            })
            .collect::<Result<Vec<_>, JournalError>>()?;
        batch.stage(Table::Company, parents.into_iter())?;
        for members in self.roster.members.chunks(256) {
            let rows = members
                .iter()
                .map(|r| {
                    let f = funding
                        .get(&r.site)
                        .filter(|f| f.company == r.company.id())
                        .ok_or(JournalError::Projection)?;
                    Ok(key.row(Member::new(r, f)))
                })
                .collect::<Result<Vec<_>, JournalError>>()?;
            batch.stage(Table::CompanyMember, rows.into_iter())?;
        }
        if batch.admission != Admission::Verify {
            batch.stage(
                Table::CompanyClaimSource,
                self.finances
                    .sources
                    .iter()
                    .map(|r| key.row(Source::from(r))),
            )?;
        }
        // A single ordered scan compares every recovered field, including share totals,
        // original carrying value, exact beneficial weights and the captured foundation.
        super::verification::verify(
            batch.tx,
            Table::CompanyClaimSource,
            campaign,
            self.finances
                .sources
                .iter()
                .map(|r| key.row(Source::from(r))),
        )?;
        super::verification::verify(
            batch.tx,
            Table::CompanyClaim,
            campaign,
            self.finances.claims.iter().map(|r| key.row(Claim::from(r))),
        )
    }
}

pub(in crate::money_journal) fn publish(
    tx: &mut Transaction<'_>,
    source: &JournalPeriodSource,
    mode: Admission,
) -> Result<(), JournalError> {
    let catalog = source
        .foundation
        .foundation()
        .graph_foundation()
        .content_bundle()
        .economic_catalog()
        .ok_or(JournalError::Projection)?;
    let directory = match (
        catalog.national_companies(),
        catalog.national_company_finances(),
    ) {
        (Some(roster), Some(finances)) => Some(CompanyDirectory { roster, finances }),
        (None, None) => None,
        _ => return Err(JournalError::Projection),
    };
    let payments = &source.payments.source;
    let id = payments.campaign_id.as_uuid();
    let admission = if mode == Admission::Rebuild {
        tx.execute(
            "DELETE FROM babylon_state.economic_company_v1 WHERE campaign_id=$1",
            &[id],
        )
        .map_err(|_| JournalError::Database)?;
        Admission::Insert
    } else {
        let count_sql = "SELECT ARRAY[
            (SELECT count(*) FROM babylon_state.economic_company_v1 WHERE campaign_id=$1),
            (SELECT count(*) FROM babylon_state.economic_company_member_key_v1 WHERE campaign_id=$1),
            (SELECT count(*) FROM babylon_state.economic_company_original_share_v1 WHERE campaign_id=$1)]";
        let row = tx
            .query_one(count_sql, &[id])
            .map_err(|_| JournalError::Database)?;
        let stored: Vec<i64> = row.try_get(0).map_err(|_| JournalError::Projection)?;
        let expected = directory.as_ref().map_or([0; 3], CompanyDirectory::counts);
        let counts = stored
            .into_iter()
            .map(|n| usize::try_from(n).map_err(|_| JournalError::Range))
            .collect::<Result<Vec<_>, _>>()?;
        match mode {
            Admission::Insert if counts == [0; 3] => Admission::Insert,
            _ if counts == expected => Admission::Verify,
            _ => return Err(JournalError::Projection),
        }
    };
    if let Some(directory) = &directory {
        let key = Binding {
            campaign: id.to_string(),
            digest: statement_storage::bytea(&payments.identity.foundation_digest()),
        };
        directory.stage(&mut Batch { tx, admission }, &key, id)?;
    }
    Ok(())
}
