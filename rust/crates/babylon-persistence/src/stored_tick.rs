//! Canonical typed-row reader shared by retry reconciliation and restart.

mod source;

pub(crate) use source::{StoredTickReadSource, StoredTickRelation};

#[path = "stored_tick/rows.rs"]
mod rows;

#[allow(unused_imports)]
use rows::{
    database, decode_column, decode_decimal, decode_digest, decode_graph_edge_f64,
    decode_graph_edges, decode_graph_hyperedge_f64, decode_graph_hyperedges,
    decode_graph_node_currency, decode_graph_node_f64, decode_graph_nodes, decode_organizations,
    decode_territories, encode_stored_event, graph_row_count, require_i64_position,
    require_position, unsigned_bits, GraphEdgeF64Rows, GraphEdgeRows, GraphHyperedgeF64Rows,
    GraphHyperedgeRows, GraphNodeCurrencyRows, GraphNodeF64Rows, GraphNodeRows, NamedStableValues,
    StableKeyLists,
};
#[allow(unused_imports)]
pub(crate) use rows::{
    decode_bsl_value, decode_stable_key, CapturedArchiveReceiptRows, CapturedCheckpointRows,
    CapturedChoiceReceiptRows, CapturedEventRows, CapturedGraphState, CapturedMaterialRows,
    CheckpointSectionSources, CheckpointSections, StoredEvent, StoredEventRows,
};

#[allow(unused_imports)]
use crate::committed_tick_envelope::CommittedTickRow;
#[allow(unused_imports)]
use crate::identity::CampaignId;
#[allow(unused_imports)]
use crate::runtime::RustPersistenceRuntimeError;
#[allow(unused_imports)]
use crate::semantic_codec;
#[allow(unused_imports)]
use babylon_bsl::identity_codec::StableBslValue;
#[allow(unused_imports)]
use babylon_graph::stable_element::StableElementKey;
#[allow(unused_imports)]
use babylon_graph::stable_state::{
    compose_stable_graph_state_from_rows, StableGraphState, StableGraphStateRowsInput,
};
#[allow(unused_imports)]
use babylon_kernel::{content_digest::sha256_of, H3CellId};
#[allow(unused_imports)]
use babylon_tick::h3_runtime::MichiganDynamicHexValueBits;
#[allow(unused_imports)]
use babylon_tick::material_state::{
    DynamicHexStateRow, MaterialStateRows, MaterialStateRowsInput, OrganizationStateRow,
    TerritoryStateRow, WorldRegisterRow,
};
#[allow(unused_imports)]
use postgres::{GenericClient, Row};
#[allow(unused_imports)]
use std::collections::BTreeMap;
