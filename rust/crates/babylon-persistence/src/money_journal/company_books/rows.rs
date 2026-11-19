//! Fixed statement sections become typed SQL columns. Only stable native units cross this boundary.
use crate::company_statements::{CompanyEntry, CompanyPeriod};
use crate::identity::CampaignId;
use crate::money_journal::statement_storage::{Batch, Table};
use crate::money_journal::JournalError;
use babylon_tick::material_replay::IdentifiedMaterialTick;
use serde::Serialize;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

pub(super) fn fingerprint(
    campaign: CampaignId,
    id: &IdentifiedMaterialTick,
    companies: &[CompanyPeriod],
) -> Result<[u8; 32], JournalError> {
    let mut hash = Sha256::new();
    hash.update(b"babylon.company-statements.sql.v1\0");
    hash.update(campaign.canonical_bytes());
    hash.update(id.canonical_bytes());
    for c in companies {
        let bytes = serde_json::to_vec(c).map_err(|_| JournalError::Projection)?;
        hash.update(
            u64::try_from(bytes.len())
                .map_err(|_| JournalError::Range)?
                .to_be_bytes(),
        );
        hash.update(bytes);
    }
    Ok(hash.finalize().into())
}
fn fields(value: &impl Serialize) -> Result<Map<String, Value>, JournalError> {
    match serde_json::to_value(value).map_err(|_| JournalError::Projection)? {
        Value::Object(map) => Ok(map),
        _ => Err(JournalError::Projection),
    }
}
fn section(
    scope: &str,
    boundary: Option<&str>,
    lines: &impl Serialize,
) -> Result<Map<String, Value>, JournalError> {
    let mut row: Map<_, _> = fields(lines)?
        .into_iter()
        .map(|(k, v)| (format!("{k}_micros"), v))
        .collect();
    if !scope.is_empty() {
        row.insert("scope".into(), scope.into());
    }
    if let Some(side) = boundary {
        row.insert("boundary".into(), side.into());
    }
    Ok(row)
}
fn entry(e: &CompanyEntry) -> Result<Map<String, Value>, JournalError> {
    let mut data = fields(e)?;
    for key in ["from_id", "to_id"] {
        if let Some(id) = data.get(key).and_then(Value::as_str) {
            data.insert(key.into(), format!("\\x{id}").into());
        }
    }
    Ok(data)
}
#[derive(Serialize)]
struct Row<'a> {
    campaign_id: &'a str,
    resolve_tick: i64,
    company_id: &'a str,
    #[serde(flatten)]
    data: Map<String, Value>,
}
fn stage(
    batch: &mut Batch<'_, '_>,
    table: Table,
    campaign: &str,
    tick: i64,
    company: &str,
    rows: Vec<Map<String, Value>>,
) -> Result<(), JournalError> {
    batch.stage(
        table,
        rows.into_iter().map(|data| Row {
            campaign_id: campaign,
            resolve_tick: tick,
            company_id: company,
            data,
        }),
    )
}
pub(super) fn store(
    batch: &mut Batch<'_, '_>,
    campaign: &str,
    tick: i64,
    companies: &[CompanyPeriod],
) -> Result<(), JournalError> {
    // Feed the shared bulk writer across companies, then bound rare high-volume source entries separately.
    let mut balances = Vec::new();
    let mut incomes = Vec::new();
    let mut cash = Vec::new();
    let mut eliminations = Vec::new();
    for c in companies {
        let id = format!("\\x{}", c.company);
        let bind = |mut data: Map<String, Value>| {
            data.insert("campaign_id".into(), campaign.into());
            data.insert("resolve_tick".into(), tick.into());
            data.insert("company_id".into(), id.clone().into());
            data
        };
        for (scope, b) in [
            ("parent", &c.parent),
            ("subsidiaries", &c.subsidiaries),
            ("consolidated", &c.consolidated),
        ] {
            balances.push(bind(section(scope, Some("opening"), &b.opening)?));
            balances.push(bind(section(scope, Some("closing"), &b.closing)?));
            incomes.push(bind(section(scope, None, &b.income)?));
            cash.push(bind(section(scope, None, &b.cash_flow)?));
        }
        eliminations.push(bind(section("", None, &c.eliminations)?));
        for entries in c.entries.chunks(256) {
            let rows = entries.iter().map(entry).collect::<Result<Vec<_>, _>>()?;
            stage(batch, Table::CompanyEntry, campaign, tick, &id, rows)?;
        }
    }
    batch.stage(Table::CompanyBalance, balances.into_iter())?;
    batch.stage(Table::CompanyIncome, incomes.into_iter())?;
    batch.stage(Table::CompanyCash, cash.into_iter())?;
    batch.stage(Table::CompanyElimination, eliminations.into_iter())
}
