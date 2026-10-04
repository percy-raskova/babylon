//! Canonical typed-row reader shared by retry reconciliation and restart.

mod source;

pub(crate) use source::{StoredTickReadSource, StoredTickRelation};

use std::collections::BTreeMap;

use babylon_bsl::identity_codec::StableBslValue;
use babylon_graph::stable_element::StableElementKey;
use babylon_graph::stable_state::{
    compose_stable_graph_state_from_rows, StableGraphState, StableGraphStateRowsInput,
};
use babylon_kernel::{content_digest::sha256_of, H3CellId};
use babylon_tick::h3_runtime::MichiganDynamicHexValueBits;
use babylon_tick::material_state::{
    DynamicHexStateRow, MaterialStateRows, MaterialStateRowsInput, OrganizationStateRow,
    TerritoryStateRow, WorldRegisterRow,
};
use postgres::{GenericClient, Row};

use crate::committed_tick_envelope::CommittedTickRow;
use crate::identity::CampaignId;
use crate::runtime::RustPersistenceRuntimeError;
use crate::semantic_codec;

#[derive(Debug, Clone, PartialEq)]
pub(crate) struct StoredEvent {
    pub(crate) emitting_rule: String,
    pub(crate) choice_receipt_ordinal: Option<u32>,
    pub(crate) event_type: String,
    pub(crate) fields: Vec<(String, StableBslValue)>,
}

pub(crate) struct StoredEventRows {
    pub(crate) encoded: Vec<CommittedTickRow>,
    pub(crate) decoded: Vec<StoredEvent>,
}

/// Owned SQL rows; admission performs the original checks without a connection.
pub(crate) struct CapturedGraphState {
    nodes: Vec<Row>,
    node_f64: Vec<Row>,
    edges: Vec<Row>,
    hyperedges: Vec<Row>,
    edge_f64: Vec<Row>,
    node_currency: Vec<Row>,
    hyperedge_f64: Vec<Row>,
}
impl CapturedGraphState {
    pub(crate) fn capture(
        client: &mut impl GenericClient,
        source: StoredTickReadSource,
        campaign_id: CampaignId,
        resolve_tick: i64,
    ) -> Result<Self, RustPersistenceRuntimeError> {
        Ok(Self {
            nodes: client
                .query(
                    &format!(
                        "SELECT local_name, node_type FROM {graph_node} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY local_name",
                        graph_node = source.relation(StoredTickRelation::GraphNode)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored graph nodes", &error))?,
            node_f64: client
                .query(
                    &format!(
                        "SELECT local_name, qname, value_bits FROM {graph_node_f64} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY local_name, qname",
                        graph_node_f64 = source.relation(StoredTickRelation::GraphNodeF64)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored graph node f64", &error))?,
            edges: client
                .query(
                    &format!(
                        "SELECT edge_type, source_local_name, target_local_name, strength_bits \
             FROM {graph_edge} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY edge_type, source_local_name, target_local_name",
                        graph_edge = source.relation(StoredTickRelation::GraphEdge)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored graph edges", &error))?,
            hyperedges: client
                .query(
                    &format!(
                        "SELECT edge.local_name, edge.hyperedge_type, \
                    ARRAY(SELECT member.position FROM {graph_hyperedge_member} AS member \
                          WHERE member.campaign_id = edge.campaign_id \
                            AND member.resolve_tick = edge.resolve_tick \
                            AND member.local_name = edge.local_name ORDER BY member.position), \
                    ARRAY(SELECT member.member FROM {graph_hyperedge_member} AS member \
                          WHERE member.campaign_id = edge.campaign_id \
                            AND member.resolve_tick = edge.resolve_tick \
                            AND member.local_name = edge.local_name ORDER BY member.position) \
             FROM {graph_hyperedge} AS edge \
             WHERE edge.campaign_id = $1::uuid AND edge.resolve_tick = $2 ORDER BY edge.local_name",
                        graph_hyperedge_member =
                            source.relation(StoredTickRelation::GraphHyperedgeMember),
                        graph_hyperedge = source.relation(StoredTickRelation::GraphHyperedge)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored graph hyperedges", &error))?,
            edge_f64: client
                .query(
                    &format!(
                "SELECT edge_type, source_local_name, target_local_name, qname, value_bits \
             FROM {graph_edge_f64} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY edge_type, source_local_name, target_local_name, qname",
                graph_edge_f64 = source.relation(StoredTickRelation::GraphEdgeF64)
            ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored graph edge f64", &error))?,
            node_currency: client
                .query(
                    &format!(
                        "SELECT local_name, qname, micro_units::text \
             FROM {graph_node_currency} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY local_name, qname",
                        graph_node_currency =
                            source.relation(StoredTickRelation::GraphNodeCurrency)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored graph Currency", &error))?,
            hyperedge_f64: client
                .query(
                    &format!(
                        "SELECT local_name, qname, value_bits \
             FROM {graph_hyperedge_f64} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY local_name, qname",
                        graph_hyperedge_f64 =
                            source.relation(StoredTickRelation::GraphHyperedgeF64)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored graph hyperedge f64", &error))?,
        })
    }
    pub(crate) fn admit(
        self,
        scenario_scope: &str,
    ) -> Result<StableGraphState, RustPersistenceRuntimeError> {
        compose_stable_graph_state_from_rows(
            scenario_scope,
            StableGraphStateRowsInput {
                nodes: decode_graph_nodes(self.nodes)?,
                node_f64: decode_graph_node_f64(self.node_f64)?,
                edges: decode_graph_edges(self.edges)?,
                hyperedges: decode_graph_hyperedges(self.hyperedges)?,
                edge_f64: decode_graph_edge_f64(self.edge_f64)?,
                node_currency: decode_graph_node_currency(self.node_currency)?,
                hyperedge_f64: decode_graph_hyperedge_f64(self.hyperedge_f64)?,
            },
        )
        .map_err(|_| RustPersistenceRuntimeError::ReplaySource)
    }
}

/// Owned SQL rows; admission performs the original checks without a connection.
pub(crate) struct CapturedMaterialRows {
    world_registers: Vec<Row>,
    territory_fields: Vec<Row>,
    territories: Vec<Row>,
    dynamic_hexes: Vec<Row>,
    organization_territories: Vec<Row>,
    organization_fields: Vec<Row>,
    organizations: Vec<Row>,
}
impl CapturedMaterialRows {
    pub(crate) fn capture(
        client: &mut impl GenericClient,
        source: StoredTickReadSource,
        campaign_id: CampaignId,
        resolve_tick: i64,
    ) -> Result<Self, RustPersistenceRuntimeError> {
        Ok(Self {
            world_registers: client
        .query(
            &format!("SELECT register_name, value_tag, int_value, currency_value::text, real_bits, \
                    ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, enum_type, enum_member, stable_key \
             FROM {world_register} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY register_name", world_register = source.relation(StoredTickRelation::WorldRegister)),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored world registers", &error))?,
            territory_fields: client
        .query(
            &format!("SELECT territory_id, position, field_name, value_tag, int_value, currency_value::text, \
                    real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, enum_type, \
                    enum_member, stable_key \
             FROM {territory_state_field} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY territory_id, position", territory_state_field = source.relation(StoredTickRelation::TerritoryStateField)),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored territory fields", &error))?,
            territories: client
        .query(
            &format!(
                "SELECT territory_id, field_count, canonical_sha256 FROM {territory_state} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY territory_id",
                territory_state = source.relation(StoredTickRelation::TerritoryState)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored territory state", &error))?,
            dynamic_hexes: client
        .query(
            &format!(
                "SELECT cell_id, c_bits, v_bits, s_bits, k_bits, biocapacity_stock_bits, \
                    energy_stock_bits, raw_material_stock_bits, internet_access_pct_bits, \
                    surveillance_coupling_bits \
             FROM {hex_state_delta} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY cell_id",
                hex_state_delta = source.relation(StoredTickRelation::HexStateDelta)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored dynamic hex state", &error))?,
            organization_territories: client
        .query(
            &format!(
                "SELECT organization_id, position, territory_id \
             FROM {organization_territory} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY organization_id, position",
                organization_territory = source.relation(StoredTickRelation::OrganizationTerritory)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored organization territories", &error))?,
            organization_fields: client
        .query(
            &format!(
                "SELECT organization_id, position, field_name, value_tag, int_value, \
                    currency_value::text, real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, \
                    bool_value, enum_type, enum_member, stable_key \
             FROM {organization_state_field} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY organization_id, position",
                organization_state_field =
                    source.relation(StoredTickRelation::OrganizationStateField)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored organization fields", &error))?,
            organizations: client
        .query(
            &format!(
                "SELECT organization_id, organization_kind_tag, organization_kind_int, \
                    organization_kind_currency::text, organization_kind_real_bits, \
                    organization_kind_ratio_bits, organization_kind_ratio_min_bits, \
                    organization_kind_ratio_max_bits, organization_kind_bool, \
                    organization_kind_enum_type, organization_kind_enum_member, \
                    organization_kind_stable_key \
             FROM {organization_state} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY organization_id",
                organization_state = source.relation(StoredTickRelation::OrganizationState)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored organization state", &error))?,
        })
    }
    pub(crate) fn admit(self) -> Result<MaterialStateRows, RustPersistenceRuntimeError> {
        let world_registers = self
            .world_registers
            .iter()
            .map(|row| {
                WorldRegisterRow::try_new(decode_column(row, 0)?, decode_bsl_value(row, 1)?)
                    .map_err(|_| RustPersistenceRuntimeError::ReplaySource)
            })
            .collect::<Result<Vec<_>, RustPersistenceRuntimeError>>()?;
        let territories = decode_territories(self.territory_fields, self.territories)?;
        let dynamic_hexes = self
            .dynamic_hexes
            .iter()
            .map(|row| {
                let cell: i64 = decode_column(row, 0)?;
                let cell = H3CellId::try_from(cell)
                    .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?;
                let bits = MichiganDynamicHexValueBits {
                    c: unsigned_bits(decode_column(row, 1)?),
                    v: unsigned_bits(decode_column(row, 2)?),
                    s: unsigned_bits(decode_column(row, 3)?),
                    k: unsigned_bits(decode_column(row, 4)?),
                    biocapacity_stock: unsigned_bits(decode_column(row, 5)?),
                    energy_stock: unsigned_bits(decode_column(row, 6)?),
                    raw_material_stock: unsigned_bits(decode_column(row, 7)?),
                    internet_access_pct: unsigned_bits(decode_column(row, 8)?),
                    surveillance_coupling: unsigned_bits(decode_column(row, 9)?),
                };
                DynamicHexStateRow::try_new(cell, bits)
                    .map_err(|_| RustPersistenceRuntimeError::ReplaySource)
            })
            .collect::<Result<Vec<_>, RustPersistenceRuntimeError>>()?;
        let organizations = decode_organizations(
            self.organization_territories,
            self.organization_fields,
            self.organizations,
        )?;
        MaterialStateRows::try_from_rows(MaterialStateRowsInput {
            world_registers,
            territories,
            dynamic_hexes,
            organizations,
        })
        .map_err(|_| RustPersistenceRuntimeError::ReplaySource)
    }
}

/// Owned SQL rows; admission performs the original checks without a connection.
pub(crate) struct CapturedEventRows {
    fields: Vec<Row>,
    events: Vec<Row>,
}
impl CapturedEventRows {
    pub(crate) fn capture(
        client: &mut impl GenericClient,
        source: StoredTickReadSource,
        campaign_id: CampaignId,
        resolve_tick: i64,
    ) -> Result<Self, RustPersistenceRuntimeError> {
        Ok(Self {
            fields: client
        .query(
            &format!("SELECT ordinal, position, field_name, value_tag, int_value, currency_value::text, \
                    real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, enum_type, \
                    enum_member, stable_key \
             FROM {tick_event_field} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY ordinal, position", tick_event_field = source.relation(StoredTickRelation::TickEventField)),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored event fields", &error))?,
            events: client
        .query(
            &format!(
                "SELECT ordinal, event_type, emitting_rule, choice_receipt_ordinal \
             FROM {tick_event} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY ordinal",
                tick_event = source.relation(StoredTickRelation::TickEvent)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored events", &error))?,
        })
    }
    pub(crate) fn admit(self) -> Result<StoredEventRows, RustPersistenceRuntimeError> {
        let mut fields: BTreeMap<i64, Vec<(String, StableBslValue)>> = BTreeMap::new();
        for row in self.fields {
            let ordinal: i64 = decode_column(&row, 0)?;
            let position: i64 = decode_column(&row, 1)?;
            let target = fields.entry(ordinal).or_default();
            require_i64_position(position, target.len())?;
            target.push((decode_column(&row, 2)?, decode_bsl_value(&row, 3)?));
        }
        let mut output = Vec::new();
        let mut decoded = Vec::new();
        for row in self.events {
            let ordinal: i64 = decode_column(&row, 0)?;
            let ordinal_u32 = u32::try_from(ordinal)
                .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?;
            if usize::try_from(ordinal).ok() != Some(output.len()) {
                return Err(RustPersistenceRuntimeError::CampaignConflict);
            }
            let owned = fields.remove(&ordinal).unwrap_or_default();
            let event = StoredEvent {
                emitting_rule: decode_column(&row, 2)?,
                choice_receipt_ordinal: decode_column::<Option<i64>>(&row, 3)?
                    .map(|value| {
                        u32::try_from(value)
                            .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)
                    })
                    .transpose()?,
                event_type: decode_column(&row, 1)?,
                fields: owned,
            };
            output.push(encode_stored_event(ordinal_u32, &event)?);
            decoded.push(event);
        }
        if !fields.is_empty() {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        Ok(StoredEventRows {
            encoded: output,
            decoded,
        })
    }
}

/// Owned SQL rows; admission performs the original checks without a connection.
pub(crate) struct CapturedChoiceReceiptRows {
    branches: Vec<Row>,
    carriers: Vec<Row>,
    receipts: Vec<Row>,
}
impl CapturedChoiceReceiptRows {
    pub(crate) fn capture(
        client: &mut impl GenericClient,
        source: StoredTickReadSource,
        campaign_id: CampaignId,
        resolve_tick: i64,
    ) -> Result<Self, RustPersistenceRuntimeError> {
        Ok(Self {
            branches: client
                .query(
                    &format!(
                "SELECT encounter_ordinal, position, outcome_member, mass_nanounits::text, \
                    ticket_start::text, ticket_end_exclusive::text, ticket_count::text \
             FROM {tick_choice_receipt_branch} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY encounter_ordinal, position",
                tick_choice_receipt_branch =
                    source.relation(StoredTickRelation::TickChoiceReceiptBranch)
            ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored choice receipt branches", &error))?,
            carriers: client
                .query(
                    &format!(
                        "SELECT encounter_ordinal, position, stable_element \
             FROM {tick_choice_receipt_carrier_element} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY encounter_ordinal, position",
                        tick_choice_receipt_carrier_element =
                            source.relation(StoredTickRelation::TickChoiceReceiptCarrierElement)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored choice receipt carriers", &error))?,
            receipts: client
                .query(
                    &format!(
                "SELECT encounter_ordinal, rule_id, sample, slot, outcome_enum, stable_carrier, \
                    draw_ticket::text, selected_outcome, allocation_digest, instance_digest \
             FROM {tick_choice_receipt} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 \
             ORDER BY encounter_ordinal",
                tick_choice_receipt = source.relation(StoredTickRelation::TickChoiceReceipt)
            ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored choice receipts", &error))?,
        })
    }
    pub(crate) fn admit(self) -> Result<Vec<CommittedTickRow>, RustPersistenceRuntimeError> {
        let mut branches: BTreeMap<i64, Vec<semantic_codec::ChoiceReceiptSemanticBranch>> =
            BTreeMap::new();
        for row in self.branches {
            let ordinal: i64 = decode_column(&row, 0)?;
            let position: i64 = decode_column(&row, 1)?;
            let target = branches.entry(ordinal).or_default();
            require_i64_position(position, target.len())?;
            target.push(semantic_codec::ChoiceReceiptSemanticBranch {
                outcome_member: decode_column(&row, 2)?,
                mass_nanounits: decode_decimal(&row, 3)?,
                ticket_start: decode_decimal(&row, 4)?,
                ticket_end_exclusive: decode_decimal(&row, 5)?,
                ticket_count: decode_decimal(&row, 6)?,
            });
        }

        let mut carriers: BTreeMap<i64, Vec<StableElementKey>> = BTreeMap::new();
        for row in self.carriers {
            let ordinal: i64 = decode_column(&row, 0)?;
            let position: i64 = decode_column(&row, 1)?;
            let target = carriers.entry(ordinal).or_default();
            require_i64_position(position, target.len())?;
            let bytes: Vec<u8> = decode_column(&row, 2)?;
            target.push(decode_stable_key(&bytes)?);
        }

        let mut output = Vec::new();
        for row in self.receipts {
            let ordinal: i64 = decode_column(&row, 0)?;
            require_i64_position(ordinal, output.len())?;
            let stable_carrier: Vec<u8> = decode_column(&row, 5)?;
            let receipt = semantic_codec::ChoiceReceiptSemanticRow {
                encounter_ordinal: u32::try_from(ordinal)
                    .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?,
                rule_id: decode_column(&row, 1)?,
                sample: decode_column(&row, 2)?,
                slot: u32::try_from(decode_column::<i64>(&row, 3)?)
                    .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?,
                outcome_enum: decode_column(&row, 4)?,
                stable_carrier: decode_stable_key(&stable_carrier)?,
                active_elements: carriers.remove(&ordinal).unwrap_or_default(),
                branches: branches
                    .remove(&ordinal)
                    .ok_or(RustPersistenceRuntimeError::CampaignConflict)?,
                draw_ticket: decode_decimal(&row, 6)?,
                selected_outcome: decode_column(&row, 7)?,
                allocation_digest: decode_digest(&row, 8)?,
                instance_digest: decode_digest(&row, 9)?,
            };
            output.push(semantic_codec::encode_choice_receipt(&receipt)?);
        }
        if !branches.is_empty() || !carriers.is_empty() {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        Ok(output)
    }
}

/// Owned SQL rows; admission performs the original checks without a connection.
pub(crate) struct CapturedArchiveReceiptRows {
    receipt: Option<Row>,
}
impl CapturedArchiveReceiptRows {
    pub(crate) fn capture(
        client: &mut impl GenericClient,
        source: StoredTickReadSource,
        campaign_id: CampaignId,
        resolve_tick: i64,
    ) -> Result<Self, RustPersistenceRuntimeError> {
        Ok(Self {
            receipt: client
                .query_opt(
                    &format!(
                        "SELECT tick_content_hash FROM {archive_dirty_receipt} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2",
                        archive_dirty_receipt =
                            source.relation(StoredTickRelation::ArchiveDirtyReceipt)
                    ),
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|error| database("read stored archive receipt", &error))?,
        })
    }
    pub(crate) fn admit(self) -> Result<CommittedTickRow, RustPersistenceRuntimeError> {
        let row = self
            .receipt
            .ok_or(RustPersistenceRuntimeError::CampaignConflict)?;
        semantic_codec::encode_archive_dirty_receipt(&decode_digest(&row, 0)?).map_err(Into::into)
    }
}

/// Owned SQL rows; admission performs the original checks without a connection.
pub(crate) struct CapturedCheckpointRows {
    manifest: Option<Row>,
    sections: Vec<Row>,
    campaign_id: CampaignId,
}
impl CapturedCheckpointRows {
    pub(crate) fn capture(
        client: &mut impl GenericClient,
        source: StoredTickReadSource,
        campaign_id: CampaignId,
        resolve_tick: i64,
    ) -> Result<Self, RustPersistenceRuntimeError> {
        Ok(Self {
            manifest: client
        .query_opt(
            &format!(
                "SELECT completeness_tag, manifest_bytes, manifest_sha256 \
             FROM {checkpoint_manifest} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2",
                checkpoint_manifest = source.relation(StoredTickRelation::CheckpointManifest)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored checkpoint manifest", &error))?,
            sections: client
        .query(
            &format!(
                "SELECT section_tag, ordinal, source_tag, decoded_length, decoded_sha256, inline_section_bytes \
             FROM {checkpoint_section} \
             WHERE campaign_id = $1::uuid AND resolve_tick = $2 ORDER BY section_tag, ordinal",
                checkpoint_section = source.relation(StoredTickRelation::CheckpointSection)
            ),
            &[campaign_id.as_uuid(), &resolve_tick],
        )
        .map_err(|error| database("read stored checkpoint sections", &error))?,
            campaign_id,
        })
    }
    pub(crate) fn admit(
        self,
        resolve_tick: u64,
        sources: CheckpointSectionSources<'_>,
    ) -> Result<(Vec<CommittedTickRow>, Vec<Vec<u8>>), RustPersistenceRuntimeError> {
        let campaign_id = self.campaign_id;
        let CheckpointSectionSources {
            graph,
            material,
            foundation_sections,
        } = sources;
        let manifest = self
            .manifest
            .ok_or(RustPersistenceRuntimeError::CampaignConflict)?;
        let completeness: i16 = decode_column(&manifest, 0)?;
        let manifest_bytes: Vec<u8> = decode_column(&manifest, 1)?;
        let manifest_digest = decode_digest(&manifest, 2)?;
        if completeness != 1 || sha256_of(&manifest_bytes) != manifest_digest {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        let stored = self.sections;
        if stored.len() != 9 {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        let mut rows = Vec::new();
        let mut sections = Vec::new();
        let graph_count = graph_row_count(graph)?;
        let material_count = u32::try_from(material.source_count())
            .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?;
        let mut summaries = Vec::new();
        for (index, row) in stored.iter().enumerate() {
            let tag: i16 = decode_column(row, 0)?;
            let ordinal: i64 = decode_column(row, 1)?;
            let expected_tag = i16::try_from(index + 1)
                .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?;
            if tag != expected_tag || ordinal != 0 {
                return Err(RustPersistenceRuntimeError::CampaignConflict);
            }
            let tag_u8 =
                u8::try_from(tag).map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?;
            let reference = crate::checkpoint_reference::Reference::from_storage(
                tag_u8,
                u8::try_from(decode_column::<i16>(row, 2)?)
                    .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?,
                usize::try_from(decode_column::<i64>(row, 3)?)
                    .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?,
                decode_digest(row, 4)?,
                decode_column(row, 5)?,
            )
            .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?;
            let bytes = reference
                .resolve(
                    graph.canonical_bytes(),
                    foundation_sections,
                    material.canonical_bytes(),
                )
                .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?
                .to_vec();
            let row_count = match tag_u8 {
                1 => graph_count,
                9 => material_count,
                _ => 1,
            };
            summaries.push((tag_u8, row_count, sha256_of(&bytes)));
            rows.push(semantic_codec::encode_checkpoint_row(tag_u8, 0, 1, &bytes)?);
            sections.push(bytes);
        }
        if sections.first().map(Vec::as_slice) != Some(graph.canonical_bytes())
            || sections.get(8).map(Vec::as_slice) != Some(material.canonical_bytes())
            || semantic_codec::encode_full_checkpoint(campaign_id, resolve_tick, &summaries)?
                != manifest_bytes
        {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        Ok((rows, sections))
    }
}

type GraphNodeRows = Vec<(String, String)>;
type GraphNodeF64Rows = Vec<(String, String, u64)>;
type GraphEdgeRows = Vec<(String, String, String, u64)>;
type GraphHyperedgeRows = Vec<(String, String, Vec<String>)>;
type GraphEdgeF64Rows = Vec<(String, String, String, String, u64)>;
type GraphNodeCurrencyRows = Vec<(String, String, i128)>;
type GraphHyperedgeF64Rows = Vec<(String, String, u64)>;

fn decode_graph_nodes(rows: Vec<Row>) -> Result<GraphNodeRows, RustPersistenceRuntimeError> {
    rows.into_iter()
        .map(|row| Ok((decode_column(&row, 0)?, decode_column(&row, 1)?)))
        .collect()
}

fn decode_graph_node_f64(rows: Vec<Row>) -> Result<GraphNodeF64Rows, RustPersistenceRuntimeError> {
    rows.into_iter()
        .map(|row| {
            let bits: i64 = decode_column(&row, 2)?;
            Ok((
                decode_column(&row, 0)?,
                decode_column(&row, 1)?,
                unsigned_bits(bits),
            ))
        })
        .collect()
}

fn decode_graph_edges(rows: Vec<Row>) -> Result<GraphEdgeRows, RustPersistenceRuntimeError> {
    rows.into_iter()
        .map(|row| {
            let bits: i64 = decode_column(&row, 3)?;
            Ok((
                decode_column(&row, 0)?,
                decode_column(&row, 1)?,
                decode_column(&row, 2)?,
                unsigned_bits(bits),
            ))
        })
        .collect()
}

fn decode_graph_hyperedges(
    rows: Vec<Row>,
) -> Result<GraphHyperedgeRows, RustPersistenceRuntimeError> {
    rows.into_iter()
        .map(|row| {
            let positions: Vec<i32> = decode_column(&row, 2)?;
            let members: Vec<String> = decode_column(&row, 3)?;
            if positions.len() != members.len()
                || positions
                    .iter()
                    .enumerate()
                    .any(|(expected, actual)| usize::try_from(*actual).ok() != Some(expected))
            {
                return Err(RustPersistenceRuntimeError::CampaignConflict);
            }
            Ok((decode_column(&row, 0)?, decode_column(&row, 1)?, members))
        })
        .collect()
}

fn decode_graph_edge_f64(rows: Vec<Row>) -> Result<GraphEdgeF64Rows, RustPersistenceRuntimeError> {
    rows.into_iter()
        .map(|row| {
            let bits: i64 = decode_column(&row, 4)?;
            Ok((
                decode_column(&row, 0)?,
                decode_column(&row, 1)?,
                decode_column(&row, 2)?,
                decode_column(&row, 3)?,
                unsigned_bits(bits),
            ))
        })
        .collect()
}

fn decode_graph_node_currency(
    rows: Vec<Row>,
) -> Result<GraphNodeCurrencyRows, RustPersistenceRuntimeError> {
    rows.into_iter()
        .map(|row| {
            let value: String = decode_column(&row, 2)?;
            Ok((
                decode_column(&row, 0)?,
                decode_column(&row, 1)?,
                value
                    .parse::<i128>()
                    .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?,
            ))
        })
        .collect()
}

fn decode_graph_hyperedge_f64(
    rows: Vec<Row>,
) -> Result<GraphHyperedgeF64Rows, RustPersistenceRuntimeError> {
    rows.into_iter()
        .map(|row| {
            let bits: i64 = decode_column(&row, 2)?;
            Ok((
                decode_column(&row, 0)?,
                decode_column(&row, 1)?,
                unsigned_bits(bits),
            ))
        })
        .collect()
}

type NamedStableValues = BTreeMap<Vec<u8>, Vec<(String, StableBslValue)>>;

fn decode_territories(
    field_rows: Vec<Row>,
    state_rows: Vec<Row>,
) -> Result<Vec<TerritoryStateRow>, RustPersistenceRuntimeError> {
    let mut fields: NamedStableValues = BTreeMap::new();
    for row in field_rows {
        let key: Vec<u8> = decode_column(&row, 0)?;
        let position: i32 = decode_column(&row, 1)?;
        let target = fields.entry(key).or_default();
        require_position(position, target.len())?;
        target.push((decode_column(&row, 2)?, decode_bsl_value(&row, 3)?));
    }
    let mut output = Vec::new();
    for row in state_rows {
        let bytes: Vec<u8> = decode_column(&row, 0)?;
        let key = decode_stable_key(&bytes)?;
        let territory = TerritoryStateRow::try_new(key, fields.remove(&bytes).unwrap_or_default())
            .map_err(|_| RustPersistenceRuntimeError::ReplaySource)?;
        let field_count: i32 = decode_column(&row, 1)?;
        let digest: Vec<u8> = decode_column(&row, 2)?;
        if usize::try_from(field_count).ok() != Some(territory.ordered_fields().len())
            || digest.as_slice() != sha256_of(territory.canonical_bytes())
        {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        output.push(territory);
    }
    if !fields.is_empty() {
        return Err(RustPersistenceRuntimeError::CampaignConflict);
    }
    Ok(output)
}

type StableKeyLists = BTreeMap<Vec<u8>, Vec<StableElementKey>>;

fn decode_organizations(
    territory_rows: Vec<Row>,
    field_rows: Vec<Row>,
    state_rows: Vec<Row>,
) -> Result<Vec<OrganizationStateRow>, RustPersistenceRuntimeError> {
    let mut territories: StableKeyLists = BTreeMap::new();
    for row in territory_rows {
        let owner: Vec<u8> = decode_column(&row, 0)?;
        let position: i32 = decode_column(&row, 1)?;
        let target = territories.entry(owner).or_default();
        require_position(position, target.len())?;
        let key: Vec<u8> = decode_column(&row, 2)?;
        target.push(decode_stable_key(&key)?);
    }
    let mut fields: NamedStableValues = BTreeMap::new();
    for row in field_rows {
        let owner: Vec<u8> = decode_column(&row, 0)?;
        let position: i32 = decode_column(&row, 1)?;
        let target = fields.entry(owner).or_default();
        require_position(position, target.len())?;
        target.push((decode_column(&row, 2)?, decode_bsl_value(&row, 3)?));
    }
    let mut output = Vec::new();
    for row in state_rows {
        let bytes: Vec<u8> = decode_column(&row, 0)?;
        output.push(
            OrganizationStateRow::try_new(
                decode_stable_key(&bytes)?,
                decode_bsl_value(&row, 1)?,
                territories.remove(&bytes).unwrap_or_default(),
                fields.remove(&bytes).unwrap_or_default(),
            )
            .map_err(|_| RustPersistenceRuntimeError::ReplaySource)?,
        );
    }
    if !territories.is_empty() || !fields.is_empty() {
        return Err(RustPersistenceRuntimeError::CampaignConflict);
    }
    Ok(output)
}

fn encode_stored_event(
    ordinal: u32,
    event: &StoredEvent,
) -> Result<CommittedTickRow, RustPersistenceRuntimeError> {
    let borrowed = event
        .fields
        .iter()
        .map(|(name, value)| (name.as_str(), value))
        .collect::<Vec<_>>();
    semantic_codec::encode_successful_event(
        ordinal,
        &event.emitting_rule,
        event.choice_receipt_ordinal,
        &event.event_type,
        &borrowed,
    )
    .map_err(Into::into)
}

#[derive(Clone, Copy)]
pub(crate) struct CheckpointSectionSources<'a> {
    pub graph: &'a StableGraphState,
    pub material: &'a MaterialStateRows,
    pub foundation_sections: &'a [Vec<u8>; 6],
}

pub(crate) fn decode_bsl_value(
    row: &Row,
    start: usize,
) -> Result<StableBslValue, RustPersistenceRuntimeError> {
    let tag: i16 = decode_column(row, start)?;
    let int_value: Option<i64> = decode_column(row, start + 1)?;
    let currency_value: Option<String> = decode_column(row, start + 2)?;
    let real_bits: Option<i64> = decode_column(row, start + 3)?;
    let ratio_bits: Option<i64> = decode_column(row, start + 4)?;
    let ratio_min_bits: Option<i64> = decode_column(row, start + 5)?;
    let ratio_max_bits: Option<i64> = decode_column(row, start + 6)?;
    let bool_value: Option<bool> = decode_column(row, start + 7)?;
    let enum_type: Option<String> = decode_column(row, start + 8)?;
    let enum_member: Option<String> = decode_column(row, start + 9)?;
    let stable_key: Option<Vec<u8>> = decode_column(row, start + 10)?;
    match tag {
        1 => int_value
            .map(StableBslValue::Int)
            .ok_or(RustPersistenceRuntimeError::CampaignConflict),
        2 => currency_value
            .ok_or(RustPersistenceRuntimeError::CampaignConflict)?
            .parse::<i128>()
            .map(StableBslValue::CurrencyMicroUnits)
            .map_err(|_| RustPersistenceRuntimeError::CampaignConflict),
        3 => real_bits
            .map(|value| StableBslValue::RealBits(unsigned_bits(value)))
            .ok_or(RustPersistenceRuntimeError::CampaignConflict),
        4 => ratio_bits
            .map(|value| StableBslValue::RatioBits {
                value: unsigned_bits(value),
                floor: ratio_min_bits.map(unsigned_bits),
                cap: ratio_max_bits.map(unsigned_bits),
            })
            .ok_or(RustPersistenceRuntimeError::CampaignConflict),
        5 => bool_value
            .map(StableBslValue::Bool)
            .ok_or(RustPersistenceRuntimeError::CampaignConflict),
        6 => Ok(StableBslValue::Enum {
            enum_type: enum_type.ok_or(RustPersistenceRuntimeError::CampaignConflict)?,
            member: enum_member.ok_or(RustPersistenceRuntimeError::CampaignConflict)?,
        }),
        7 => Ok(StableBslValue::Node(decode_stable_key(
            &stable_key.ok_or(RustPersistenceRuntimeError::CampaignConflict)?,
        )?)),
        8 => Ok(StableBslValue::Hyperedge(decode_stable_key(
            &stable_key.ok_or(RustPersistenceRuntimeError::CampaignConflict)?,
        )?)),
        9 => Ok(StableBslValue::Edge(decode_stable_key(
            &stable_key.ok_or(RustPersistenceRuntimeError::CampaignConflict)?,
        )?)),
        _ => Err(RustPersistenceRuntimeError::CampaignConflict),
    }
}

pub(crate) fn decode_stable_key(
    bytes: &[u8],
) -> Result<StableElementKey, RustPersistenceRuntimeError> {
    StableElementKey::from_canonical_bytes(bytes)
        .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)
}

fn graph_row_count(graph: &StableGraphState) -> Result<u32, RustPersistenceRuntimeError> {
    let rows = graph.rows();
    let count = [
        rows.nodes().len(),
        rows.node_f64().len(),
        rows.edges().len(),
        rows.hyperedges().len(),
        rows.edge_f64().len(),
        rows.node_currency().len(),
        rows.hyperedge_f64().len(),
    ]
    .into_iter()
    .try_fold(0_usize, usize::checked_add)
    .ok_or(RustPersistenceRuntimeError::CampaignConflict)?;
    u32::try_from(count).map_err(|_| RustPersistenceRuntimeError::CampaignConflict)
}

fn require_position(actual: i32, expected: usize) -> Result<(), RustPersistenceRuntimeError> {
    if usize::try_from(actual).ok() == Some(expected) {
        Ok(())
    } else {
        Err(RustPersistenceRuntimeError::CampaignConflict)
    }
}

fn require_i64_position(actual: i64, expected: usize) -> Result<(), RustPersistenceRuntimeError> {
    if usize::try_from(actual).ok() == Some(expected) {
        Ok(())
    } else {
        Err(RustPersistenceRuntimeError::CampaignConflict)
    }
}

fn decode_decimal<T>(row: &Row, index: usize) -> Result<T, RustPersistenceRuntimeError>
where
    T: std::str::FromStr,
{
    decode_column::<String>(row, index)?
        .parse()
        .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)
}

fn unsigned_bits(value: i64) -> u64 {
    u64::from_be_bytes(value.to_be_bytes())
}

fn decode_column<T: postgres::types::FromSqlOwned>(
    row: &Row,
    index: usize,
) -> Result<T, RustPersistenceRuntimeError> {
    row.try_get(index)
        .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)
}

fn decode_digest(row: &Row, index: usize) -> Result<[u8; 32], RustPersistenceRuntimeError> {
    let bytes: Vec<u8> = decode_column(row, index)?;
    bytes
        .try_into()
        .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)
}

fn database(operation: &'static str, error: &postgres::Error) -> RustPersistenceRuntimeError {
    RustPersistenceRuntimeError::postgres(operation, error)
}
