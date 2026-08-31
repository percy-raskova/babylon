//! Graph/event/archive semantic batch composition for the stopped Rust cutover.

use std::collections::TryReserveError;

use babylon_graph::stable_state::{StableGraphStateRowsV1, StableGraphStateV1};
use babylon_tick::material_state::{MaterialStateRowRefV1, MaterialStateRowsV1};
use babylon_tick::replay_session::{
    IdentifiedTickReportV1, SuccessfulEventBatchV1, SuccessfulEventV1,
};

use crate::committed_tick_envelope::{
    validate_committed_tick_envelope_bounds_v1, CommittedTickEnvelopeErrorV1,
    CommittedTickRowFamilyV1, CommittedTickRowV1, COMMITTED_TICK_ROW_FAMILY_COUNT_V1,
    MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
};
use crate::semantic_codec::{self, SemanticCodecErrorV1};

const ROW_LENGTH_BYTES: usize = 8;
const MINIMUM_NONEMPTY_ROW_BYTES: usize = ROW_LENGTH_BYTES + 1;

/// Source-owned proof that the stable graph contained no typed rows.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StableGraphRowsEmptyProofV1 {
    source_digest: [u8; 32],
}

/// Source-owned proof that the successful BSL event section contained no events.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SuccessfulEventBatchEmptyProofV1 {
    source_digest: [u8; 32],
}

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum SemanticBatchErrorV1 {
    Codec(SemanticCodecErrorV1),
    Envelope(CommittedTickEnvelopeErrorV1),
    CapacityOverflow {
        field: &'static str,
    },
    IntegerConversion {
        field: &'static str,
        value: usize,
    },
    Allocation {
        field: &'static str,
        requested: usize,
    },
}

impl From<SemanticCodecErrorV1> for SemanticBatchErrorV1 {
    fn from(value: SemanticCodecErrorV1) -> Self {
        Self::Codec(value)
    }
}

impl From<CommittedTickEnvelopeErrorV1> for SemanticBatchErrorV1 {
    fn from(value: CommittedTickEnvelopeErrorV1) -> Self {
        Self::Envelope(value)
    }
}

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum SemanticFamilyBatchV1<P> {
    Rows {
        rows: Vec<CommittedTickRowV1>,
        body_bytes: usize,
    },
    Empty(P),
}

impl<P> SemanticFamilyBatchV1<P> {
    fn into_rows(self) -> Option<(Vec<CommittedTickRowV1>, usize)> {
        match self {
            Self::Rows { rows, body_bytes } => Some((rows, body_bytes)),
            Self::Empty(_) => None,
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub(crate) struct GraphEventSemanticBatchesV1 {
    graph: SemanticFamilyBatchV1<StableGraphRowsEmptyProofV1>,
    event: SemanticFamilyBatchV1<SuccessfulEventBatchEmptyProofV1>,
    archive_dirty_receipt: CommittedTickRowV1,
}

impl GraphEventSemanticBatchesV1 {
    pub(crate) fn graph_row_count(&self) -> usize {
        match &self.graph {
            SemanticFamilyBatchV1::Rows { rows, .. } => rows.len(),
            SemanticFamilyBatchV1::Empty(_) => 0,
        }
    }

    pub(crate) fn event_row_count(&self) -> usize {
        match &self.event {
            SemanticFamilyBatchV1::Rows { rows, .. } => rows.len(),
            SemanticFamilyBatchV1::Empty(_) => 0,
        }
    }

    pub(crate) fn into_rows(self) -> (Vec<CommittedTickRowV1>, Vec<CommittedTickRowV1>) {
        let graph = self.graph.into_rows().map_or_else(Vec::new, |rows| rows.0);
        let event = self.event.into_rows().map_or_else(Vec::new, |rows| rows.0);
        (graph, event)
    }
}

pub(crate) fn compose_material_state_rows_v1(
    source: &MaterialStateRowsV1,
) -> Result<Vec<CommittedTickRowV1>, SemanticBatchErrorV1> {
    let mut rows = reserve_rows_v1("material state semantic rows", source.source_count())?;
    let mut body_bytes = 0_usize;
    for source_row in source.rows() {
        let row = match source_row {
            MaterialStateRowRefV1::WorldRegister(row) => {
                semantic_codec::encode_world_register(row.qname(), row.value())?
            }
            MaterialStateRowRefV1::Territory(row) => {
                let fields = row
                    .ordered_fields()
                    .iter()
                    .map(|(name, value)| (name.as_str(), value))
                    .collect::<Vec<_>>();
                semantic_codec::encode_territory_state(row.territory_id(), &fields)?
            }
            MaterialStateRowRefV1::DynamicHex(row) => {
                let values = row.value_bits().map(f64::from_bits);
                semantic_codec::encode_dynamic_hex_state(row.cell_id().as_u64(), &values)?
            }
            MaterialStateRowRefV1::Organization(row) => {
                let fields = row
                    .ordered_fields()
                    .iter()
                    .map(|(name, value)| (name.as_str(), value))
                    .collect::<Vec<_>>();
                semantic_codec::encode_organization_state(
                    row.organization_id(),
                    row.organization_kind(),
                    row.ordered_territory_ids(),
                    &fields,
                )?
            }
        };
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::State,
            &mut rows,
            &mut body_bytes,
            row,
        )?;
    }
    Ok(rows)
}

pub(crate) fn compose_graph_event_semantic_batches_v1(
    report: &IdentifiedTickReportV1,
) -> Result<GraphEventSemanticBatchesV1, SemanticBatchErrorV1> {
    compose_graph_event_sources_v1(
        report.result_stable_graph(),
        report.successful_event_batch(),
        *report.tick_content_hash().as_bytes(),
    )
}

fn compose_graph_event_sources_v1(
    graph_source: &StableGraphStateV1,
    event_source: &SuccessfulEventBatchV1,
    tick_content_hash: [u8; 32],
) -> Result<GraphEventSemanticBatchesV1, SemanticBatchErrorV1> {
    let graph_count = stable_graph_source_count_v1(graph_source.rows())?;
    let event_count = event_source.events().len();
    let archive_dirty_receipt = semantic_codec::encode_archive_dirty_receipt(&tick_content_hash)?;
    let archive_body_bytes = row_body_bytes_v1(&archive_dirty_receipt)?;
    preflight_graph_event_counts_v1(graph_count, event_count, archive_body_bytes)?;

    let (graph_rows, graph_body_bytes) = compose_graph_rows_with_encoder_v1(
        graph_source.rows(),
        &mut |row: StableGraphRowRefV1<'_>| row.encode(),
    )?;
    let (event_rows, event_body_bytes) = compose_event_rows_v1(event_source)?;
    preflight_graph_event_bounds_v1(
        graph_rows.len(),
        graph_body_bytes,
        event_rows.len(),
        event_body_bytes,
        archive_body_bytes,
    )?;

    let graph = if graph_rows.is_empty() {
        SemanticFamilyBatchV1::Empty(StableGraphRowsEmptyProofV1 {
            source_digest: graph_source.digest().into_bytes(),
        })
    } else {
        SemanticFamilyBatchV1::Rows {
            rows: graph_rows,
            body_bytes: graph_body_bytes,
        }
    };
    let event = if event_rows.is_empty() {
        SemanticFamilyBatchV1::Empty(SuccessfulEventBatchEmptyProofV1 {
            source_digest: event_source.source_digest(),
        })
    } else {
        SemanticFamilyBatchV1::Rows {
            rows: event_rows,
            body_bytes: event_body_bytes,
        }
    };
    Ok(GraphEventSemanticBatchesV1 {
        graph,
        event,
        archive_dirty_receipt,
    })
}

fn stable_graph_source_count_v1(
    source: &StableGraphStateRowsV1,
) -> Result<usize, SemanticBatchErrorV1> {
    let counts = [
        source.nodes().len(),
        source.node_f64().len(),
        source.edges().len(),
        source.hyperedges().len(),
        source.edge_f64().len(),
        source.node_currency().len(),
        source.hyperedge_f64().len(),
    ];
    checked_sum_v1(&counts, "stable graph source rows")
}

fn preflight_graph_event_counts_v1(
    graph_rows: usize,
    event_rows: usize,
    archive_body_bytes: usize,
) -> Result<(), SemanticBatchErrorV1> {
    let graph_minimum = graph_rows.checked_mul(MINIMUM_NONEMPTY_ROW_BYTES).ok_or(
        SemanticBatchErrorV1::CapacityOverflow {
            field: "stable graph minimum row bytes",
        },
    )?;
    let event_minimum = event_rows.checked_mul(MINIMUM_NONEMPTY_ROW_BYTES).ok_or(
        SemanticBatchErrorV1::CapacityOverflow {
            field: "successful event minimum row bytes",
        },
    )?;
    preflight_graph_event_bounds_v1(
        graph_rows,
        graph_minimum,
        event_rows,
        event_minimum,
        archive_body_bytes,
    )
    .map(|_| ())
}

pub(crate) fn preflight_graph_event_bounds_v1(
    graph_rows: usize,
    graph_body_bytes: usize,
    event_rows: usize,
    event_body_bytes: usize,
    archive_body_bytes: usize,
) -> Result<usize, SemanticBatchErrorV1> {
    let mut row_counts = [0_usize; COMMITTED_TICK_ROW_FAMILY_COUNT_V1];
    row_counts[0] = graph_rows;
    row_counts[2] = event_rows;
    row_counts[4] = 1;
    let mut body_bytes = [0_usize; COMMITTED_TICK_ROW_FAMILY_COUNT_V1];
    body_bytes[0] = graph_body_bytes;
    body_bytes[2] = event_body_bytes;
    body_bytes[4] = archive_body_bytes;
    validate_committed_tick_envelope_bounds_v1(row_counts, body_bytes).map_err(Into::into)
}

fn row_body_bytes_v1(row: &CommittedTickRowV1) -> Result<usize, SemanticBatchErrorV1> {
    ROW_LENGTH_BYTES
        .checked_add(row.key().len())
        .and_then(|value| value.checked_add(row.payload().len()))
        .ok_or(SemanticBatchErrorV1::CapacityOverflow {
            field: "semantic batch row body",
        })
}

pub(crate) enum StableGraphRowRefV1<'a> {
    Node(&'a str, &'a str),
    NodeF64(&'a str, &'a str, f64),
    Edge(&'a str, &'a str, &'a str, f64),
    Hyperedge(&'a str, &'a str, &'a [String]),
    EdgeF64(&'a str, &'a str, &'a str, &'a str, f64),
    NodeCurrency(&'a str, &'a str, i128),
    HyperedgeF64(&'a str, &'a str, f64),
}

impl StableGraphRowRefV1<'_> {
    pub(crate) fn encode(self) -> Result<CommittedTickRowV1, SemanticCodecErrorV1> {
        match self {
            Self::Node(local_name, node_type) => {
                semantic_codec::encode_stable_graph_node(local_name, node_type)
            }
            Self::NodeF64(local_name, qname, bits) => semantic_codec::encode_stable_graph_node_f64(
                local_name,
                qname,
                f64::from_bits(bits.to_bits()),
            ),
            Self::Edge(edge_type, source, target, strength) => {
                semantic_codec::encode_stable_graph_edge(edge_type, source, target, strength)
            }
            Self::Hyperedge(local_name, hyperedge_type, members) => {
                semantic_codec::encode_stable_graph_hyperedge(local_name, hyperedge_type, members)
            }
            Self::EdgeF64(edge_type, source, target, qname, value) => {
                semantic_codec::encode_stable_graph_edge_f64(
                    edge_type, source, target, qname, value,
                )
            }
            Self::NodeCurrency(local_name, qname, micro_units) => {
                semantic_codec::encode_stable_graph_node_currency(local_name, qname, micro_units)
            }
            Self::HyperedgeF64(local_name, qname, value) => {
                semantic_codec::encode_stable_graph_hyperedge_f64(local_name, qname, value)
            }
        }
    }
}

pub(crate) fn compose_graph_rows_with_encoder_v1(
    source: &StableGraphStateRowsV1,
    encode: &mut impl FnMut(StableGraphRowRefV1<'_>) -> Result<CommittedTickRowV1, SemanticCodecErrorV1>,
) -> Result<(Vec<CommittedTickRowV1>, usize), SemanticBatchErrorV1> {
    let count = stable_graph_source_count_v1(source)?;
    let mut rows = reserve_rows_v1("stable graph semantic rows", count)?;
    let mut body_bytes = 0_usize;
    for (local_name, node_type) in source.nodes() {
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Graph,
            &mut rows,
            &mut body_bytes,
            encode(StableGraphRowRefV1::Node(local_name, node_type))?,
        )?;
    }
    for (local_name, qname, bits) in source.node_f64() {
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Graph,
            &mut rows,
            &mut body_bytes,
            encode(StableGraphRowRefV1::NodeF64(
                local_name,
                qname,
                f64::from_bits(*bits),
            ))?,
        )?;
    }
    for (edge_type, source, target, strength_bits) in source.edges() {
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Graph,
            &mut rows,
            &mut body_bytes,
            encode(StableGraphRowRefV1::Edge(
                edge_type,
                source,
                target,
                f64::from_bits(*strength_bits),
            ))?,
        )?;
    }
    for (local_name, hyperedge_type, members) in source.hyperedges() {
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Graph,
            &mut rows,
            &mut body_bytes,
            encode(StableGraphRowRefV1::Hyperedge(
                local_name,
                hyperedge_type,
                members,
            ))?,
        )?;
    }
    for (edge_type, source, target, qname, bits) in source.edge_f64() {
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Graph,
            &mut rows,
            &mut body_bytes,
            encode(StableGraphRowRefV1::EdgeF64(
                edge_type,
                source,
                target,
                qname,
                f64::from_bits(*bits),
            ))?,
        )?;
    }
    for (local_name, qname, micro_units) in source.node_currency() {
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Graph,
            &mut rows,
            &mut body_bytes,
            encode(StableGraphRowRefV1::NodeCurrency(
                local_name,
                qname,
                *micro_units,
            ))?,
        )?;
    }
    for (local_name, qname, bits) in source.hyperedge_f64() {
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Graph,
            &mut rows,
            &mut body_bytes,
            encode(StableGraphRowRefV1::HyperedgeF64(
                local_name,
                qname,
                f64::from_bits(*bits),
            ))?,
        )?;
    }
    Ok((rows, body_bytes))
}

fn compose_event_rows_v1(
    source: &SuccessfulEventBatchV1,
) -> Result<(Vec<CommittedTickRowV1>, usize), SemanticBatchErrorV1> {
    let mut rows = reserve_rows_v1("successful event semantic rows", source.events().len())?;
    let mut body_bytes = 0_usize;
    for (index, event) in source.events().iter().enumerate() {
        let ordinal =
            u32::try_from(index).map_err(|_| SemanticBatchErrorV1::IntegerConversion {
                field: "successful event ordinal",
                value: index,
            })?;
        let row = encode_successful_event_v1(ordinal, event)?;
        push_encoded_row_v1(
            CommittedTickRowFamilyV1::Event,
            &mut rows,
            &mut body_bytes,
            row,
        )?;
    }
    Ok((rows, body_bytes))
}

fn encode_successful_event_v1(
    ordinal: u32,
    event: &SuccessfulEventV1,
) -> Result<CommittedTickRowV1, SemanticBatchErrorV1> {
    let mut fields = Vec::new();
    fields
        .try_reserve_exact(event.fields().len())
        .map_err(|_: TryReserveError| SemanticBatchErrorV1::Allocation {
            field: "successful event semantic fields",
            requested: event.fields().len(),
        })?;
    for (name, value) in event.fields() {
        fields.push((name.as_str(), value));
    }
    semantic_codec::encode_successful_event(ordinal, event.event_type(), &fields)
        .map_err(Into::into)
}

fn reserve_rows_v1(
    field: &'static str,
    count: usize,
) -> Result<Vec<CommittedTickRowV1>, SemanticBatchErrorV1> {
    let mut rows = Vec::new();
    rows.try_reserve_exact(count)
        .map_err(|_: TryReserveError| SemanticBatchErrorV1::Allocation {
            field,
            requested: count,
        })?;
    Ok(rows)
}

fn push_encoded_row_v1(
    family: CommittedTickRowFamilyV1,
    rows: &mut Vec<CommittedTickRowV1>,
    body_bytes: &mut usize,
    row: CommittedTickRowV1,
) -> Result<(), SemanticBatchErrorV1> {
    let next_body_bytes = body_bytes
        .checked_add(ROW_LENGTH_BYTES)
        .and_then(|value| value.checked_add(row.key().len()))
        .and_then(|value| value.checked_add(row.payload().len()))
        .ok_or(SemanticBatchErrorV1::CapacityOverflow {
            field: "semantic batch row body",
        })?;
    if next_body_bytes > MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1 {
        return Err(SemanticBatchErrorV1::Envelope(
            CommittedTickEnvelopeErrorV1::BatchBytes {
                family,
                actual: next_body_bytes,
                maximum: MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
            },
        ));
    }
    *body_bytes = next_body_bytes;
    rows.push(row);
    Ok(())
}

fn checked_sum_v1(values: &[usize], field: &'static str) -> Result<usize, SemanticBatchErrorV1> {
    values.iter().try_fold(0_usize, |total, value| {
        total
            .checked_add(*value)
            .ok_or(SemanticBatchErrorV1::CapacityOverflow { field })
    })
}

#[cfg(test)]
mod tests {
    use std::cell::Cell;

    use babylon_bsl::rule_pipeline::split_content;
    use babylon_bsl::rules_hash_of;
    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_graph::hypergraph_store::HypergraphStore;
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
    use babylon_kernel::tick_content_hash::{RefDigestV1, TickContentHashV1};
    use babylon_kernel::ContentDigest;
    use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
    use babylon_tick::material_state::MaterialStateV1;
    use babylon_tick::replay_session::{IdentifiedTickReportV1, ReplayTickSession};

    use crate::committed_tick_envelope::{
        CommittedTickEnvelopeErrorV1, CommittedTickEnvelopeV1, CommittedTickRowFamiliesV1,
        CommittedTickRowFamilyV1, CommittedTickRowV1, MAX_COMMITTED_TICK_ROWS_V1,
        MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
    };
    use crate::identity::CampaignId;
    use crate::michigan_dynamic_hex_foundation_v1;
    use crate::semantic_codec::SemanticCodecErrorV1;
    use crate::tick_commit_claim::TickCommitClaimV1;

    use super::{
        compose_graph_event_semantic_batches_v1, compose_graph_rows_with_encoder_v1,
        preflight_graph_event_bounds_v1, push_encoded_row_v1, SemanticBatchErrorV1,
        SemanticFamilyBatchV1, StableGraphRowRefV1, StableGraphRowsEmptyProofV1,
        SuccessfulEventBatchEmptyProofV1,
    };

    const SCENARIO: &str = r"
(scenario demo/persistence-batches
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/draw coefficient extensive)
  (node class-a NodeType/SOCIAL_CLASS (social-class/draw 0.0c))
  (node class-b NodeType/SOCIAL_CLASS (social-class/draw 0.0c)))
";
    const EMPTY_SCENARIO: &str = r"
(scenario demo/persistence-batches-empty
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/draw coefficient extensive))
";
    const RULE: &str = r#"
(rule production/typed-batch
  :role mechanic
  :evidence derived
  :material-basis "graph/event semantic batch composition law"
  :fuel 32
  (bindings (binding draw :field social-class/draw))
  (when #t)
  (effects
    (update-node self social-class/draw (set 0.25c))
    (emit EventType/PERSISTENCE_BATCH (subject self))))
"#;

    fn report_for(scenario: &str, session_name: &str) -> IdentifiedTickReportV1 {
        let (_, rules) = split_content(RULE).expect("test rule parses");
        let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
        let content = ContentDigest {
            defines_hash: [0x21; 32],
            rules_hash: rules_hash_of(&forms).expect("test rule hashes"),
        };
        let session_id = ReplaySessionIdV1::try_from(session_name).expect("test session id");
        let foundation =
            michigan_dynamic_hex_foundation_v1().expect("governed foundation must decode once");
        let mut session = ReplayTickSession::new(
            scenario,
            None,
            RULE,
            HypergraphStore::new(),
            session_id.clone(),
            ReplaySeed::new(41),
            content,
            RefDigestV1::from_bytes(foundation.reference_bundle_digest()),
            MaterialStateV1::try_new(foundation)
                .expect("test material state requires the exact governed dynamic-H3 foundation"),
        )
        .expect("test replay prepares");
        let actions =
            OrderedPracticeActionBatchV1::empty(session_id, 1).expect("test empty action batch");
        session
            .advance(&mut CollectingSink::default(), &actions)
            .expect("test replay advances")
    }

    fn report() -> IdentifiedTickReportV1 {
        report_for(SCENARIO, "per281/semantic-batches")
    }

    #[test]
    fn proof_types_are_send_and_only_true_empty_sources_produce_them() {
        fn assert_send<T: Send>() {}
        assert_send::<StableGraphRowsEmptyProofV1>();
        assert_send::<SuccessfulEventBatchEmptyProofV1>();

        let empty_report = report_for(EMPTY_SCENARIO, "per281/semantic-batches-empty");
        let empty = compose_graph_event_semantic_batches_v1(&empty_report)
            .expect("true typed empty sources compose");
        let SemanticFamilyBatchV1::Empty(graph_proof) = empty.graph else {
            panic!("true empty graph source must produce its typed proof")
        };
        assert_eq!(
            graph_proof.source_digest,
            empty_report.result_stable_graph().digest().into_bytes()
        );
        let SemanticFamilyBatchV1::Empty(event_proof) = empty.event else {
            panic!("true empty event source must produce its typed proof")
        };
        assert_eq!(
            event_proof.source_digest,
            empty_report.successful_event_batch().source_digest()
        );

        let nonempty = compose_graph_event_semantic_batches_v1(&report())
            .expect("real report composes graph and event rows");
        assert!(matches!(nonempty.graph, SemanticFamilyBatchV1::Rows { .. }));
        assert!(matches!(nonempty.event, SemanticFamilyBatchV1::Rows { .. }));
    }

    #[test]
    fn preflight_accepts_exact_count_body_and_aggregate_bounds_and_refuses_plus_one() {
        let minimum_body = MAX_COMMITTED_TICK_ROWS_V1 * 9;
        preflight_graph_event_bounds_v1(MAX_COMMITTED_TICK_ROWS_V1 - 1, minimum_body - 9, 0, 0, 9)
            .expect("exact aggregate row ceiling");
        assert!(matches!(
            preflight_graph_event_bounds_v1(MAX_COMMITTED_TICK_ROWS_V1, minimum_body, 0, 0, 9),
            Err(SemanticBatchErrorV1::Envelope(
                CommittedTickEnvelopeErrorV1::AggregateRows { .. }
            ))
        ));
        preflight_graph_event_bounds_v1(1, MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1, 0, 0, 9)
            .expect("exact graph body ceiling");
        assert!(matches!(
            preflight_graph_event_bounds_v1(1, MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1 + 1, 0, 0, 9,),
            Err(SemanticBatchErrorV1::Envelope(
                CommittedTickEnvelopeErrorV1::BatchBytes { .. }
            ))
        ));
    }

    #[test]
    fn incremental_family_byte_plus_one_refuses_before_row_publication() {
        let row = crate::semantic_codec::encode_stable_graph_node("class-a", "SOCIAL_CLASS")
            .expect("small graph row encodes");
        let row_bytes = row_body_bytes(&row);
        let mut body_bytes = MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1 - row_bytes + 1;
        let body_before = body_bytes;
        let mut rows = Vec::new();

        assert_eq!(
            push_encoded_row_v1(
                CommittedTickRowFamilyV1::Graph,
                &mut rows,
                &mut body_bytes,
                row,
            ),
            Err(SemanticBatchErrorV1::Envelope(
                CommittedTickEnvelopeErrorV1::BatchBytes {
                    family: CommittedTickRowFamilyV1::Graph,
                    actual: MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1 + 1,
                    maximum: MAX_COMMITTED_TICK_ROW_BATCH_BYTES_V1,
                }
            ))
        );
        assert!(rows.is_empty());
        assert_eq!(body_bytes, body_before);
    }

    #[test]
    fn second_row_codec_refusal_returns_only_error_without_partial_batch() {
        let report = report();
        let calls = Cell::new(0_usize);
        let result = compose_graph_rows_with_encoder_v1(
            report.result_stable_graph().rows(),
            &mut |row: StableGraphRowRefV1<'_>| {
                let call = calls.get();
                calls.set(call + 1);
                if call == 1 {
                    return Err(SemanticCodecErrorV1::Invalid("injected second row"));
                }
                row.encode()
            },
        );
        assert_eq!(calls.get(), 2);
        assert_eq!(
            result,
            Err(SemanticBatchErrorV1::Codec(SemanticCodecErrorV1::Invalid(
                "injected second row"
            )))
        );
    }

    #[test]
    fn real_report_rows_are_vector_compatible_ordered_and_envelope_accepted() {
        let report = report();
        let batches =
            compose_graph_event_semantic_batches_v1(&report).expect("real report semantic batches");
        let (graph, graph_body_bytes) = batches.graph.into_rows().expect("graph rows");
        let (event, event_body_bytes) = batches.event.into_rows().expect("event rows");
        let archive_dirty_receipt = batches.archive_dirty_receipt;
        assert!(!graph.is_empty());
        assert_eq!(event.len(), 2);
        assert_eq!(
            graph_body_bytes,
            graph.iter().map(row_body_bytes).sum::<usize>()
        );
        assert_eq!(
            event_body_bytes,
            event.iter().map(row_body_bytes).sum::<usize>()
        );
        assert!(graph.windows(2).all(|rows| rows[0].key() < rows[1].key()));
        assert!(event.windows(2).all(|rows| rows[0].key() < rows[1].key()));

        let claim = TickCommitClaimV1::compose(
            CampaignId::from_uuid(uuid::Uuid::nil()),
            1,
            TickContentHashV1::from_bytes([0x33; 32]),
        );
        CommittedTickEnvelopeV1::compose(
            claim,
            CommittedTickRowFamiliesV1 {
                graph,
                state: vec![],
                event,
                checkpoint: vec![],
                archive_dirty_receipt,
            },
        )
        .expect("existing envelope laws accept both ordered families");
    }

    fn row_body_bytes(row: &CommittedTickRowV1) -> usize {
        8 + row.key().len() + row.payload().len()
    }
}
