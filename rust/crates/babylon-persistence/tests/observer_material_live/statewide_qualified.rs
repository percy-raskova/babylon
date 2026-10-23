//! Opt-in qualification of the actual captured statewide sources on owned `PostgreSQL`.
//! The ordinary reader focus excludes this full four-preset, sixteen-period run.

#[path = "statewide_qualified/maintenance.rs"]
mod maintenance;

#[path = "statewide_qualified/support.rs"]
mod support;

#[allow(unused_imports)]
use support::{
    actual_statewide_sources_survive_four_persisted_sixteen_period_campaigns, advance_pair,
    assert_capacity, assert_final_demand, assert_goods_conserved, assert_history_and_preview,
    assert_merchant, assert_qualified_totals, assert_qualified_witness,
    assert_same_foundation_bytes, assert_stock, assert_workforce, inventory_and_transit,
    maximum_rows, observe, outbound_quantity, qualify_preset, reopen_runtime, witnessed_output,
    Goods, Measurements, Session, SourceCopies, SOURCE_FILES,
};

#[allow(unused_imports)]
use super::{
    advance_material_period, identity_hex, install_reader_role, provision_observer_role,
    CampaignId, CollectingSink, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset,
    MichiganDeliveryPreset, NoTls, ObserverEconomyReader, ObserverVisibility,
    OrderedPracticeActionBatch, Uuid,
};
#[allow(unused_imports)]
use babylon_graph::hypergraph_store::HypergraphStore;
#[allow(unused_imports)]
use babylon_material_circuit::{GoodId, MaterialCircuitState, UnitId};
#[allow(unused_imports)]
use babylon_persistence::{
    material_runtime::{MaterialRuntimeFoundation, MAX_MATERIAL_FOUNDATION_BYTES},
    michigan_material::{MichiganMaterialCatalog, MAX_MICHIGAN_SOURCE_BYTES},
    production_observation::ProductionCapacityKind,
    production_observation::ProductionOutboundKind,
    production_observation::ProductionSnapshot,
    ProductionEvidenceDigest,
};
#[allow(unused_imports)]
use babylon_tick::{
    material_replay::MaterialReplaySession,
    material_world::{
        decode_material_receipts, MaterialTickReceipts, MAX_MATERIAL_TICK_RECEIPT_BYTES,
        MAX_MATERIAL_WORLD_REGISTER_BYTES,
    },
    replay_session::ReplayCommitDisposition,
};
#[allow(unused_imports)]
use std::{
    collections::{BTreeMap, BTreeSet},
    io::Write,
    path::{Path, PathBuf},
    time::{Duration, Instant},
};
