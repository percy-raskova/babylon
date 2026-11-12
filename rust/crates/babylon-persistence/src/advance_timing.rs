//! Private nested observations for a successful material Advance publication.
//!
//! Durations never enter canonical bytes, state, errors, or the runtime protocol.
//! Preparation children nest inside `preparation_us`; schema children nest inside
//! `schema_verify_us`. Publication children nest inside `write_publish_us`. Optional
//! commit durations distinguish tail reconciliation from an attempted COMMIT.
//! Graph/event/choice, material state, second checkpoint and Archive receipt nest
//! inside `report_families`; `second_checkpoint_source` and `second_checkpoint_rows`
//! nest inside `second_checkpoint`. The publication `full_checkpoint` duration nests
//! inside `typed_families`. These children are not additive to their parents.

use std::time::Duration;

#[derive(Debug, Default)]
pub(crate) struct PreparationTiming {
    pub(crate) diagnostic_choices: Duration,
    pub(crate) full_checkpoint: Duration,
    pub(crate) report_families: Duration,
    pub(crate) graph_event_choice: Duration,
    pub(crate) material_state: Duration,
    pub(crate) second_checkpoint: Duration,
    pub(crate) second_checkpoint_source: Duration,
    pub(crate) second_checkpoint_rows: Duration,
    pub(crate) archive_receipt: Duration,
    pub(crate) envelope_families: Duration,
    pub(crate) envelope: Duration,
    pub(crate) material_encode: Duration,
}

#[derive(Debug, Default)]
pub(crate) struct CensusTiming {
    pub(crate) query_fetch: Duration,
    pub(crate) decode: Duration,
}

#[derive(Debug, Default)]
pub(crate) struct SchemaTiming {
    pub(crate) settings_owner_sentinels: Duration,
    pub(crate) census: CensusTiming,
    pub(crate) fixture_match: Duration,
    pub(crate) source_identity: Duration,
}

#[derive(Debug, Default)]
pub(crate) struct PublicationTiming {
    pub(crate) tail_admission: Duration,
    pub(crate) typed_families: Duration,
    pub(crate) full_checkpoint: Duration,
    pub(crate) material_register_receipt: Duration,
    pub(crate) organizer: Duration,
    pub(crate) catalog: Duration,
    pub(crate) marker: Option<Duration>,
    pub(crate) commit_ack: Option<Duration>,
    pub(crate) reconciliation: Option<Duration>,
}

#[derive(Debug, Default)]
pub(crate) struct AdvanceTiming {
    pub(crate) preparation: PreparationTiming,
    pub(crate) schema: SchemaTiming,
    pub(crate) publication: PublicationTiming,
}
