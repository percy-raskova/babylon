//! Atomic transport into an operator-provisioned, current, otherwise empty campaign database.
use super::rows::Transfer;
use super::source;
use crate::current_schema;
use crate::economic_content::{EconomicContentAdmission, EconomicContentHandle};
use crate::identity::CampaignId;
use crate::material_runtime::{self, CapturedMaterialFoundation, FoundationReadSource};
use crate::{observer_material, postgres_catalog};
use postgres::{Config, IsolationLevel, NoTls, Transaction};
use serde::Serialize;
use std::fmt::{Display, Formatter, Result as FmtResult};

#[derive(Debug, PartialEq, Eq)]
pub enum InspectionCopyError {
    ConnectionTarget,
    SourceConnection,
    DestinationConnection,
    SourceSchema,
    DestinationSchema,
    CampaignAbsent,
    DestinationOccupied,
    Foundation,
    Markers,
    Table(&'static str),
    TableColumns(&'static str),
    Components(i64),
    DestinationCommit,
}
impl Display for InspectionCopyError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "inspection copy refused: {self:?}")
    }
}
impl std::error::Error for InspectionCopyError {}

/// The old capture's unchanged identifying fields, verified before publishing the inspection copy.
#[derive(Debug, Serialize)]
pub struct InspectionCopy {
    pub campaign: String,
    pub source_schema: &'static str,
    pub foundation_sha256: String,
    pub committed_periods: u64,
    pub final_tick_content_hash: Option<String>,
}

fn capture(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
) -> Result<([u8; 32], i64), InspectionCopyError> {
    let id = campaign.as_uuid();
    let row=tx.query_opt("SELECT foundation_sha256 FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1",&[id]).map_err(|_|InspectionCopyError::Foundation)?.ok_or(InspectionCopyError::CampaignAbsent)?;
    let foundation = row
        .try_get::<_, Vec<u8>>(0)
        .map_err(|_| InspectionCopyError::Foundation)?
        .try_into()
        .map_err(|_| InspectionCopyError::Foundation)?;
    let row=tx.query_one("SELECT count(*),coalesce(max(resolve_tick),0),coalesce(bool_and(envelope_layout_version=3),true),(SELECT count(*) FROM babylon_state.material_tick_v3 WHERE campaign_id=$1) FROM babylon_state.tick_commit WHERE campaign_id=$1",&[id]).map_err(|_|InspectionCopyError::Markers)?;
    let n: i64 = row.try_get(0).map_err(|_| InspectionCopyError::Markers)?;
    if n != row
        .try_get::<_, i64>(1)
        .map_err(|_| InspectionCopyError::Markers)?
        || !row
            .try_get::<_, bool>(2)
            .map_err(|_| InspectionCopyError::Markers)?
        || n != row
            .try_get::<_, i64>(3)
            .map_err(|_| InspectionCopyError::Markers)?
    {
        return Err(InspectionCopyError::Markers);
    }
    Ok((foundation, n))
}

fn verify_copy(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    foundation: [u8; 32],
    tip: i64,
) -> Result<Option<String>, InspectionCopyError> {
    let captured = material_runtime::capture_material_foundation_components(
        tx,
        campaign,
        foundation,
        FoundationReadSource::Runtime,
    )
    .and_then(CapturedMaterialFoundation::admit)
    .map_err(|_| InspectionCopyError::Foundation)?;
    let admitted = EconomicContentAdmission::from_foundation(captured)
        .map_err(|_| InspectionCopyError::Foundation)?;
    let handle = EconomicContentHandle::new(admitted);
    let mut cursor = None;
    let mut last = None;
    for tick in 1..=tip {
        let period = u64::try_from(tick).map_err(|_| InspectionCopyError::Markers)?;
        let source =
            observer_material::committed_receipts(tx, campaign, period, &handle, &mut cursor, None)
                .map_err(|_| InspectionCopyError::Components(tick))?;
        last = Some(crate::qualification_audit::trade::hex(
            source.identity.tick_content_hash().as_bytes(),
        ));
    }
    Ok(last)
}

/// Transport exactly one material campaign from a pinned earlier schema to a freshly
/// initialized current database. Bootstrap the target and provision its own roles separately.
/// Its existing reference cohort supplies the FK for a Michigan-control campaign.
///
/// # Errors
/// Refuses any other source schema, an occupied or unowned destination, missing material
/// foundation, malformed committed history, or any failed copy or deferred constraint.
pub fn copy_campaign(
    source_config: &Config,
    destination_config: &Config,
    campaign: CampaignId,
) -> Result<InspectionCopy, InspectionCopyError> {
    if source_config.get_dbname().is_none()
        || destination_config.get_dbname().is_none()
        || (source_config.get_hosts() == destination_config.get_hosts()
            && source_config.get_ports() == destination_config.get_ports()
            && source_config.get_dbname() == destination_config.get_dbname())
    {
        return Err(InspectionCopyError::ConnectionTarget);
    }
    for config in [source_config, destination_config] {
        postgres_catalog::validate_connection_target(config)
            .map_err(|_| InspectionCopyError::ConnectionTarget)?;
    }
    let mut source_client = current_schema::bounded_config(source_config)
        .connect(NoTls)
        .map_err(|_| InspectionCopyError::SourceConnection)?;
    let mut from = source_client
        .build_transaction()
        .isolation_level(IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()
        .map_err(|_| InspectionCopyError::SourceConnection)?;
    from.batch_execute(
        "SET LOCAL statement_timeout='120s'; SET LOCAL idle_in_transaction_session_timeout='120s'",
    )
    .map_err(|_| InspectionCopyError::SourceConnection)?;
    from.query_one(
        "SELECT pg_catalog.pg_advisory_xact_lock_shared($1)",
        &[&crate::SCHEMA_ADVISORY_LOCK_KEY],
    )
    .map_err(|_| InspectionCopyError::SourceSchema)?;
    let source_schema = source::check(&mut from)?;
    let (foundation, tip) = capture(&mut from, campaign)?;
    let mut destination_client = current_schema::bounded_config(destination_config)
        .connect(NoTls)
        .map_err(|_| InspectionCopyError::DestinationConnection)?;
    let mut to = destination_client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
        .map_err(|_| InspectionCopyError::DestinationConnection)?;
    to.batch_execute("SET LOCAL statement_timeout='120s'; SET LOCAL idle_in_transaction_session_timeout='120s'; SET LOCAL synchronous_commit=on").map_err(|_|InspectionCopyError::DestinationConnection)?;
    to.query_one(
        "SELECT pg_catalog.pg_advisory_xact_lock($1)",
        &[&crate::SCHEMA_ADVISORY_LOCK_KEY],
    )
    .map_err(|_| InspectionCopyError::DestinationSchema)?;
    current_schema::require_current_schema(&mut to)
        .map_err(|_| InspectionCopyError::DestinationSchema)?;
    to.batch_execute(
        "LOCK TABLE babylon_state.campaign,babylon_meta.campaign IN SHARE ROW EXCLUSIVE MODE",
    )
    .map_err(|_| InspectionCopyError::DestinationSchema)?;
    let occupied:bool=to.query_one("SELECT EXISTS(SELECT 1 FROM babylon_state.campaign) OR EXISTS(SELECT 1 FROM babylon_meta.campaign)",&[]).and_then(|r|r.try_get(0)).map_err(|_|InspectionCopyError::DestinationSchema)?;
    if occupied {
        return Err(InspectionCopyError::DestinationOccupied);
    }
    let mut transfer = Transfer::new(&mut from, &mut to, campaign)?;
    transfer.foundation()?;
    for tick in 1..=tip {
        transfer.period(tick)?;
    }
    transfer.history()?;
    from.commit()
        .map_err(|_| InspectionCopyError::SourceConnection)?;
    let last = verify_copy(&mut to, campaign, foundation, tip)?;
    to.commit()
        .map_err(|_| InspectionCopyError::DestinationCommit)?;
    Ok(InspectionCopy {
        campaign: campaign.as_uuid().to_string(),
        source_schema,
        foundation_sha256: crate::qualification_audit::trade::hex(&foundation),
        committed_periods: u64::try_from(tip).map_err(|_| InspectionCopyError::Markers)?,
        final_tick_content_hash: last,
    })
}
