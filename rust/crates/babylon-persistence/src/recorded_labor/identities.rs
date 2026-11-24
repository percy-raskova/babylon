//! Resolve the opaque freight and equipment IDs present at either display-window boundary.
use super::{LaborId, LaborNode, RecordedLaborError, Result};
use babylon_material_circuit::{
    CircuitAccounting, MaterialCatalog, MaterialCircuitState, ProcessId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use serde::Serialize;
use std::collections::BTreeMap;

/// Units for freight come from its captured commodity. Equipment quantity counts remaining
/// service batches for installed cohorts and physical equipment units for pending installations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum RecordedAssetIdentity {
    CommercialFreight {
        source_site: LaborId,
        destination_site: LaborId,
        order: LaborId,
        route: LaborId,
        good: LaborId,
        unit: LaborId,
    },
    AidFreight {
        donor: LaborId,
        recipient: LaborId,
        commitment: LaborId,
        route: LaborId,
        good: LaborId,
        unit: LaborId,
    },
    ProductiveEquipment {
        site: LaborId,
        process: LaborId,
        definition: LaborId,
        good: LaborId,
        unit: LaborId,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct RecordedAsset {
    pub node: LaborNode,
    pub identity: RecordedAssetIdentity,
}

fn equipment(catalog: &MaterialCatalog, process: ProcessId) -> Result<RecordedAssetIdentity> {
    let err = RecordedLaborError::ReceiptMismatch("equipment definition");
    let content = catalog.equipment_content().ok_or(err)?;
    let binding = content
        .bindings
        .binary_search_by_key(&process, |r| r.process_id)
        .map(|i| &content.bindings[i])
        .map_err(|_| err)?;
    let kind = content
        .definitions
        .binary_search_by_key(&binding.definition_id, |r| r.id)
        .map(|i| &content.definitions[i])
        .map_err(|_| err)?;
    Ok(RecordedAssetIdentity::ProductiveEquipment {
        site: LaborId(binding.site_id.as_bytes()),
        process: LaborId(process.as_bytes()),
        definition: LaborId(kind.id.as_bytes()),
        good: LaborId(kind.equipment_good_id.as_bytes()),
        unit: LaborId(kind.equipment_unit_id.as_bytes()),
    })
}

pub(super) fn crossed(
    catalog: &MaterialCatalog,
    before: &MaterialCircuitState,
    after: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
) -> Result<Vec<RecordedAsset>> {
    let mut assets = BTreeMap::new();
    let mut record = |node, identity| {
        if assets
            .insert(node, identity)
            .is_some_and(|prior| prior != identity)
        {
            return Err(RecordedLaborError::ReceiptMismatch(
                "changed asset identity",
            ));
        }
        Ok(())
    };
    for state in [before, after] {
        for row in &state.freight {
            record(
                LaborNode::freight(row.lot_id),
                RecordedAssetIdentity::CommercialFreight {
                    source_site: LaborId(row.source_site_id.as_bytes()),
                    destination_site: LaborId(row.destination_site_id.as_bytes()),
                    order: LaborId(row.order_id.as_bytes()),
                    route: LaborId(row.route_id.as_bytes()),
                    good: LaborId(row.good_id.as_bytes()),
                    unit: LaborId(row.unit_id.as_bytes()),
                },
            )?;
        }
        if let CircuitAccounting::Monetary(book) = &state.accounting {
            for row in &book.aid.freight {
                record(
                    LaborNode::freight(row.lot_id),
                    RecordedAssetIdentity::AidFreight {
                        donor: LaborId(row.donor.as_bytes()),
                        recipient: LaborId(row.recipient.as_bytes()),
                        commitment: LaborId(row.commitment_id.as_bytes()),
                        route: LaborId(row.route_id.as_bytes()),
                        good: LaborId(row.good_id.as_bytes()),
                        unit: LaborId(row.unit_id.as_bytes()),
                    },
                )?;
            }
        }
        for row in &state.capacity_reservations.equipment.cohorts {
            record(
                LaborNode::equipment(row.id),
                equipment(catalog, row.process_id)?,
            )?;
        }
        for row in &state.capacity_reservations.equipment.pending {
            record(
                LaborNode::installation(row.id),
                equipment(catalog, row.process_id)?,
            )?;
        }
    }
    // Work may start and finish in one close, leaving no pending installation at either boundary.
    for row in &receipts.installation {
        record(
            LaborNode::installation(row.id),
            equipment(catalog, row.process_id)?,
        )?;
    }
    Ok(assets
        .into_iter()
        .map(|(node, identity)| RecordedAsset { node, identity })
        .collect())
}
