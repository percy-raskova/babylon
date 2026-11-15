//! Only predecessor-owned base rows cross the connection. All DDL and triggers are the target's.
use super::InspectionCopyError;
use crate::identity::CampaignId;
use postgres::{Error, Transaction};
use std::collections::BTreeMap;
use std::io;

const FOUNDATIONS: &[&str] = &[
    "babylon_state.campaign",
    "babylon_meta.campaign",
    "babylon_state.campaign_foundation",
    "babylon_state.material_campaign_foundation_v3",
    "babylon_meta.territory_county_map_v1",
    "babylon_meta.breadcrumb",
    "babylon_meta.jumplist",
    "babylon_meta.watchlist",
];
const LOOKUPS: &[&str] = &[
    "babylon_state.graph_string_lookup_v1",
    "babylon_state.graph_node_lookup_v1",
    "babylon_state.event_text_lookup_v1",
    "babylon_state.event_key_lookup_v1",
    "babylon_state.territory_definition_v1",
];
const VECTORS: &str = "babylon_state.graph_node_vector_v1";
const FIELDS: &str = "babylon_state.territory_definition_field_v1";
// Insert components in their original parent-before-child order. The marker is always last.
const PERIODS: &[&str] = &[
    "babylon_state.checkpoint_manifest",
    "babylon_state.checkpoint_section_v1",
    "babylon_state.graph_edge_v1",
    "babylon_state.graph_edge_f64_v1",
    "babylon_state.graph_hyperedge_v1",
    "babylon_state.graph_hyperedge_member_v1",
    "babylon_state.graph_hyperedge_f64_v1",
    "babylon_state.graph_node_manifest_v1",
    "babylon_state.graph_node_chunk_v1",
    "babylon_state.graph_node_f64_chunk_v1",
    "babylon_state.graph_node_currency_v1",
    "babylon_state.hex_state_delta_v1",
    "babylon_state.organization_state_v1",
    "babylon_state.organization_state_field_v1",
    "babylon_state.organization_territory_v1",
    "babylon_state.territory_tick_manifest_v1",
    "babylon_state.territory_tick_membership_v1",
    "babylon_state.tick_action_batch_v1",
    "babylon_state.tick_choice_receipt_v1",
    "babylon_state.tick_choice_receipt_branch_v1",
    "babylon_state.tick_choice_receipt_carrier_element_v1",
    "babylon_state.world_register_v1",
    "babylon_state.event_manifest_v1",
    "babylon_state.event_parent_chunk_v1",
    "babylon_state.event_field_chunk_v1",
    "babylon_state.material_tick_v3",
    "babylon_state.archive_dirty_receipt_v1",
    "babylon_state.tick_commit",
];
const HISTORY: &[&str] = &[
    "babylon_state.organizer_command_v1",
    "babylon_state.organizer_subject_v1",
    "babylon_state.organizer_observation_v1",
    "babylon_state.organizer_receipt_v1",
    "babylon_state.organizer_encounter_v1",
    "babylon_meta.archive_provenance_v1",
    "babylon_meta.archive_knowledge_grant_v1",
    "babylon_meta.archive_receipt_consumption_v1",
    "babylon_meta.archive_atom_v1",
    "babylon_meta.archive_tick_knowledge_v3",
    "babylon_meta.archive_knowledge_membership_v3",
    "babylon_meta.archive_page_revision_v2",
];

/// The canonical binary fields must agree across both independently attested PG17 catalogs.
#[derive(PartialEq, Eq)]
struct TableColumns {
    writable: String,
    signature: String,
}

fn columns(
    tx: &mut Transaction<'_>,
    tables: &[&str],
) -> Result<BTreeMap<String, TableColumns>, Error> {
    let sql="SELECT n.nspname||'.'||c.relname,
        string_agg(quote_ident(a.attname),',' ORDER BY a.attnum)
            FILTER (WHERE a.attgenerated='' AND a.attname<>'creation_xid'),
        jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attndims,
            a.attnotnull,a.attgenerated,a.attidentity,cn.nspname,col.collname,
            pg_get_expr(d.adbin,d.adrelid)) ORDER BY a.attnum)::text
        FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_catalog.pg_collation col ON col.oid=a.attcollation
        LEFT JOIN pg_catalog.pg_namespace cn ON cn.oid=col.collnamespace
        LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        WHERE (n.nspname||'.'||c.relname)=ANY($1::text[]) AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped
        GROUP BY n.nspname,c.relname";
    tx.query(sql, &[&tables])?
        .into_iter()
        .map(|r| {
            Ok((
                r.try_get(0)?,
                TableColumns {
                    writable: r.try_get(1)?,
                    signature: r.try_get(2)?,
                },
            ))
        })
        .collect()
}

pub(super) struct Transfer<'a, 's, 't> {
    from: &'a mut Transaction<'s>,
    to: &'a mut Transaction<'t>,
    campaign: CampaignId,
    columns: BTreeMap<String, String>,
}

impl<'a, 's, 't> Transfer<'a, 's, 't> {
    pub(super) fn new(
        from: &'a mut Transaction<'s>,
        to: &'a mut Transaction<'t>,
        campaign: CampaignId,
    ) -> Result<Self, InspectionCopyError> {
        let tables: Vec<&str> = FOUNDATIONS
            .iter()
            .chain(LOOKUPS)
            .chain([&VECTORS, &FIELDS])
            .chain(PERIODS)
            .chain(HISTORY)
            .copied()
            .collect();
        let mut input = columns(from, &tables).map_err(|_| InspectionCopyError::SourceSchema)?;
        let mut target =
            columns(to, &tables).map_err(|_| InspectionCopyError::DestinationSchema)?;
        let mut columns = BTreeMap::new();
        for table in tables {
            let expected = target
                .remove(table)
                .ok_or(InspectionCopyError::TableColumns(table))?;
            if input.remove(table).as_ref() != Some(&expected) {
                return Err(InspectionCopyError::TableColumns(table));
            }
            columns.insert(table.to_owned(), expected.writable);
        }
        Ok(Self {
            from,
            to,
            campaign,
            columns,
        })
    }

    fn rows(&mut self, table: &'static str, condition: &str) -> Result<(), InspectionCopyError> {
        let cols = self
            .columns
            .get(table)
            .ok_or(InspectionCopyError::DestinationSchema)?;
        // Relation names, column identifiers, and predicates come from the pinned operator and
        // the attested target catalog; the campaign and tick are parsed UUID and integer values.
        let from = format!("COPY (SELECT {cols} FROM {table} t WHERE t.campaign_id='{}'::uuid {condition}) TO STDOUT (FORMAT BINARY)",self.campaign.as_uuid());
        let to = format!("COPY {table}({cols}) FROM STDIN (FORMAT BINARY)");
        let error = |_| InspectionCopyError::Table(table);
        let mut source = self.from.copy_out(&from).map_err(error)?;
        let mut destination = self.to.copy_in(&to).map_err(error)?;
        io::copy(&mut source, &mut destination).map_err(|_| InspectionCopyError::Table(table))?;
        destination.finish().map_err(error)?;
        Ok(())
    }

    pub(super) fn foundation(&mut self) -> Result<(), InspectionCopyError> {
        for &table in FOUNDATIONS {
            self.rows(table, "")?;
        }
        self.lookups(0)
    }

    fn lookups(&mut self, tick: i64) -> Result<(), InspectionCopyError> {
        let at = format!("AND t.first_tick={tick}");
        for &table in LOOKUPS {
            self.rows(table, &at)?;
        }
        let fields=format!("AND EXISTS(SELECT 1 FROM babylon_state.territory_definition_v1 d WHERE d.campaign_id=t.campaign_id AND d.definition_id=t.definition_id AND d.first_tick={tick})");
        self.rows(FIELDS, &fields)?;
        if tick > 0 {
            self.rows(VECTORS, &at)?;
        }
        Ok(())
    }

    pub(super) fn period(&mut self, tick: i64) -> Result<(), InspectionCopyError> {
        self.lookups(tick)?;
        let at = format!("AND t.resolve_tick={tick}");
        for &table in PERIODS {
            self.rows(table, &at)?;
        }
        self.to
            .batch_execute("SET CONSTRAINTS ALL IMMEDIATE; SET CONSTRAINTS ALL DEFERRED")
            .map_err(|_| InspectionCopyError::Components(tick))?;
        Ok(())
    }
    pub(super) fn history(&mut self) -> Result<(), InspectionCopyError> {
        for &table in HISTORY {
            let order = match table {
                "babylon_meta.archive_provenance_v1" => "ORDER BY t.provenance_ref",
                "babylon_meta.archive_tick_knowledge_v3" => "ORDER BY t.resolve_tick",
                _ => "",
            };
            self.rows(table, order)?;
        }
        Ok(())
    }
}
