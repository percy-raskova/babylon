//! Exact generated identity representation; never generates economic outcomes.
use super::{admitted_count, Error as StorageError, OpeningRegister, MAX_LOOKUP_BYTES};
use crate::state_storage::{IdentityEntry, IdentityKind as K};
use babylon_kernel::content_digest::sha256_of;
use babylon_material_circuit::{
    equipment_purchase_order_id, recurring_household_order_id, recurring_procurement_order_id,
    recurring_service_order_id, AccountId, FinalDemandPrincipalId, GoodId, ProcessId, SiteId,
    UnitId,
};
use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Error {
    Recipe,
    Reference,
    Kind,
    Period,
    Row,
    Framing,
    Allocation,
}
type Result<T> = std::result::Result<T, StorageError>;
#[derive(Clone, Copy, Debug)]
enum Descriptor {
    Literal(IdentityEntry),
    Row { recipe: u8, row: u32, period: u64 },
    Freight { reference: u32, period: u64 },
}
const HOUSEHOLD: u8 = 128;
const PROCUREMENT: u8 = 129;
const SERVICE_SITE: u8 = 130;
const SERVICE_HOUSEHOLD: u8 = 131;
const EQUIPMENT: u8 = 132;
const SHIFT: u8 = 133;
const POOL: u8 = 134;
const FREIGHT: u8 = 135;
const RECIPES: [(u8, u16); 7] = [
    (HOUSEHOLD, 32),
    (PROCUREMENT, 35),
    (SERVICE_SITE, 38),
    (SERVICE_HOUSEHOLD, 33),
    (EQUIPMENT, 63),
    (SHIFT, 27),
    (POOL, 2),
];
fn failure(error: Error) -> StorageError {
    StorageError::Descriptor(error)
}
fn identity(
    opening: &OpeningRegister,
    section: u16,
    row: u32,
    field: usize,
    kind: K,
) -> Result<[u8; 32]> {
    opening
        .recipe_row_identity(section, row as usize, field, kind)
        .map_err(|_| failure(Error::Row))
}
fn row_value(
    opening: &OpeningRegister,
    recipe: u8,
    row: u32,
    period: u64,
) -> Result<IdentityEntry> {
    let section = RECIPES
        .iter()
        .find(|(tag, _)| *tag == recipe)
        .ok_or_else(|| failure(Error::Recipe))?
        .1;
    let field = |index, kind| identity(opening, section, row, index, kind);
    let order = match recipe {
        HOUSEHOLD => recurring_household_order_id(
            period,
            (
                FinalDemandPrincipalId::from_bytes(field(0, K::FinalDemandPrincipal)?),
                GoodId::from_bytes(field(1, K::Good)?),
                UnitId::from_bytes(field(2, K::Unit)?),
            ),
        ),
        PROCUREMENT => recurring_procurement_order_id(
            period,
            SiteId::from_bytes(field(0, K::Site)?),
            SiteId::from_bytes(field(1, K::Site)?),
            GoodId::from_bytes(field(2, K::Good)?),
            UnitId::from_bytes(field(3, K::Unit)?),
        ),
        SERVICE_SITE | SERVICE_HOUSEHOLD => {
            let buyer = if recipe == SERVICE_SITE {
                AccountId::Site(SiteId::from_bytes(field(0, K::Site)?))
            } else {
                AccountId::Household(FinalDemandPrincipalId::from_bytes(field(
                    0,
                    K::FinalDemandPrincipal,
                )?))
            };
            recurring_service_order_id(
                period,
                buyer,
                SiteId::from_bytes(field(1, K::Site)?),
                GoodId::from_bytes(field(2, K::Good)?),
                UnitId::from_bytes(field(3, K::Unit)?),
            )
        }
        EQUIPMENT => {
            equipment_purchase_order_id(period, ProcessId::from_bytes(field(0, K::Process)?))
        }
        SHIFT => {
            // The public member_shift_id constructor hashes only these four typed identities.
            let mut bytes = b"babylon.member-funded-attendance.v1\0".to_vec();
            bytes.extend_from_slice(&period.to_be_bytes());
            for (index, kind) in [K::StaffingMember, K::Site, K::Unit, K::FinalDemandPrincipal]
                .into_iter()
                .enumerate()
            {
                bytes.extend_from_slice(&field(index, kind)?);
            }
            return Ok(IdentityEntry {
                kind: K::Shift,
                bytes: sha256_of(&bytes),
            });
        }
        POOL => {
            // Only exact matches from the admitted national producer use this recipe.
            let mut bytes = b"NationalStaffingPoolV1\0".to_vec();
            bytes.extend_from_slice(&field(0, K::Site)?);
            return Ok(IdentityEntry {
                kind: K::StaffingPool,
                bytes: sha256_of(&bytes),
            });
        }
        _ => return Err(failure(Error::Recipe)),
    };
    Ok(IdentityEntry {
        kind: K::Order,
        bytes: order.as_bytes(),
    })
}
fn freight(order: [u8; 32], period: u64) -> IdentityEntry {
    let mut bytes = b"babylon.freight-lot.v2\0".to_vec();
    bytes.extend_from_slice(&order);
    bytes.extend_from_slice(&period.to_be_bytes());
    IdentityEntry {
        kind: K::FreightLot,
        bytes: sha256_of(&bytes),
    }
}
fn candidates(
    opening: &OpeningRegister,
    tick: u64,
    additions: &[IdentityEntry],
) -> Result<BTreeMap<IdentityEntry, Descriptor>> {
    let mut values = BTreeMap::new();
    for (recipe, section) in RECIPES {
        let output_kind = match recipe {
            SHIFT => K::Shift,
            POOL => K::StaffingPool,
            _ => K::Order,
        };
        if !additions.iter().any(|entry| entry.kind == output_kind) {
            continue;
        }
        let Some((_, Some(count))) = opening.section(section) else {
            continue;
        };
        for row in 0..count {
            let row = u32::try_from(row).map_err(|_| failure(Error::Row))?;
            let period = if recipe == POOL { 0 } else { tick };
            values
                .entry(row_value(opening, recipe, row, period)?)
                .or_insert(Descriptor::Row {
                    recipe,
                    row,
                    period,
                });
        }
    }
    if additions.iter().any(|entry| entry.kind == K::FreightLot) {
        for (index, entry) in opening
            .lookup()
            .entries()
            .iter()
            .chain(additions)
            .enumerate()
        {
            if entry.kind == K::Order {
                let reference = u32::try_from(index).map_err(|_| failure(Error::Reference))?;
                values
                    .entry(freight(entry.bytes, tick))
                    .or_insert(Descriptor::Freight {
                        reference,
                        period: tick,
                    });
            }
        }
    }
    Ok(values)
}
pub(super) fn encode(
    opening: &OpeningRegister,
    tick: u64,
    additions: &[IdentityEntry],
) -> Result<Vec<u8>> {
    admitted_count(opening.lookup().entries().len(), additions.len())?;
    if additions.is_empty() {
        return Ok(0_u32.to_be_bytes().to_vec());
    }
    let candidates = candidates(opening, tick, additions)?;
    let maximum = additions
        .len()
        .checked_mul(33)
        .and_then(|n| n.checked_add(4))
        .ok_or(StorageError::Bounds)?;
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(maximum)
        .map_err(|_| failure(Error::Allocation))?;
    bytes.extend_from_slice(
        &u32::try_from(additions.len())
            .map_err(|_| StorageError::Bounds)?
            .to_be_bytes(),
    );
    for entry in additions {
        match candidates
            .get(entry)
            .copied()
            .unwrap_or(Descriptor::Literal(*entry))
        {
            Descriptor::Literal(value) => {
                bytes.push(value.kind as u8);
                bytes.extend_from_slice(&value.bytes);
            }
            Descriptor::Row {
                recipe,
                row,
                period,
            } => {
                bytes.push(recipe);
                bytes.extend_from_slice(&row.to_be_bytes());
                if recipe != POOL {
                    bytes.extend_from_slice(&period.to_be_bytes());
                }
            }
            Descriptor::Freight { reference, period } => {
                bytes.push(FREIGHT);
                bytes.extend_from_slice(&reference.to_be_bytes());
                bytes.extend_from_slice(&period.to_be_bytes());
            }
        }
    }
    if bytes.len() > MAX_LOOKUP_BYTES {
        return Err(StorageError::Bounds);
    }
    Ok(bytes)
}
fn parse(bytes: &[u8], tick: u64, expected_count: usize) -> Result<Vec<Descriptor>> {
    let mut cursor = super::Cursor { bytes, position: 0 };
    let count =
        usize::try_from(u32::from_be_bytes(cursor.array()?)).map_err(|_| StorageError::Bounds)?;
    if count != expected_count {
        return Err(failure(Error::Framing));
    }
    admitted_count(0, count)?;
    // Every descriptor needs at least five bytes; refuse hostile count before allocation.
    if count > bytes.len().saturating_sub(4) / 5 {
        return Err(failure(Error::Framing));
    }
    let mut rows = Vec::new();
    rows.try_reserve_exact(count)
        .map_err(|_| failure(Error::Allocation))?;
    for _ in 0..count {
        let tag = cursor.array::<1>()?[0];
        let value = if tag < 128 {
            Descriptor::Literal(IdentityEntry {
                kind: K::from_tag(tag)?,
                bytes: cursor.array()?,
            })
        } else {
            let row = u32::from_be_bytes(cursor.array()?);
            if !(HOUSEHOLD..=FREIGHT).contains(&tag) {
                return Err(failure(Error::Recipe));
            }
            let period = if tag == POOL {
                0
            } else {
                u64::from_be_bytes(cursor.array()?)
            };
            if tag != POOL && (period == 0 || period > tick) {
                return Err(failure(Error::Period));
            }
            if tag == FREIGHT {
                Descriptor::Freight {
                    reference: row,
                    period,
                }
            } else {
                Descriptor::Row {
                    recipe: tag,
                    row,
                    period,
                }
            }
        };
        rows.push(value);
    }
    cursor.done()?;
    Ok(rows)
}
fn direct(opening: &OpeningRegister, value: Descriptor) -> Result<IdentityEntry> {
    match value {
        Descriptor::Literal(entry) => Ok(entry),
        Descriptor::Row {
            recipe,
            row,
            period,
        } => row_value(opening, recipe, row, period),
        Descriptor::Freight { .. } => Err(failure(Error::Kind)),
    }
}
pub(super) fn decode(
    opening: &OpeningRegister,
    tick: u64,
    bytes: &[u8],
    expected_count: usize,
) -> Result<Vec<IdentityEntry>> {
    if bytes.len() > MAX_LOOKUP_BYTES {
        return Err(StorageError::Bounds);
    }
    admitted_count(opening.lookup().entries().len(), expected_count)?;
    let rows = parse(bytes, tick, expected_count)?;
    let mut entries = Vec::new();
    entries
        .try_reserve_exact(rows.len())
        .map_err(|_| failure(Error::Allocation))?;
    for value in &rows {
        let entry = match *value {
            Descriptor::Freight { reference, period } => {
                let reference = reference as usize;
                let seed = opening.lookup().entries();
                let order = if reference < seed.len() {
                    seed[reference]
                } else {
                    // Only direct Order descriptors may be referenced: maximum depth one,
                    // forward references allowed, cycles and Freight→Freight forbidden by kind.
                    let target = *rows
                        .get(reference - seed.len())
                        .ok_or_else(|| failure(Error::Reference))?;
                    direct(opening, target)?
                };
                if order.kind != K::Order {
                    return Err(failure(Error::Kind));
                }
                freight(order.bytes, period)
            }
            other => direct(opening, other)?,
        };
        entries.push(entry);
    }
    Ok(entries)
}

#[cfg(test)]
fn monetary_fixture() -> crate::organizer_aid_fixture::Session {
    crate::organizer_aid_fixture::authored_session(
        crate::michigan_dynamic_hex_foundation().unwrap(),
        crate::organizer_aid_fixture::config(),
        false,
        false,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::state_storage::StorageError as StateError;
    fn opening() -> OpeningRegister {
        let session = monetary_fixture();
        OpeningRegister::from_opening(session.material()).unwrap()
    }
    #[test]
    fn opening_row_accessor_refuses_variable_sections_wrong_kinds_and_bounds() {
        let opening = opening();
        assert_eq!(
            opening.recipe_row_identity(6, 0, 0, K::Good),
            Err(StateError::Layout)
        );
        assert_eq!(
            opening.recipe_row_identity(2, 0, 0, K::Unit),
            Err(StateError::IdentityKind)
        );
        let count = opening.section(2).unwrap().1.unwrap();
        assert_eq!(
            opening.recipe_row_identity(2, count, 0, K::Site),
            Err(StateError::LookupIndex)
        );
        assert_eq!(
            opening.recipe_row_identity(2, 0, 99, K::Site),
            Err(StateError::Layout)
        );
    }
    #[test]
    fn shift_tuple_matches_the_current_engine_constructor_without_recomputing_pay() {
        let session = monetary_fixture();
        let opening = OpeningRegister::from_opening(session.material()).unwrap();
        let babylon_material_circuit::CircuitAccounting::Monetary(economy) =
            &session.material().state().accounting
        else {
            panic!("monetary fixture");
        };
        let expected = babylon_material_circuit::member_shift_id(7, &economy.employment[0]);
        assert_eq!(
            row_value(&opening, SHIFT, 0, 7).unwrap(),
            IdentityEntry {
                kind: K::Shift,
                bytes: expected.as_bytes()
            }
        );
    }
    fn body(tag: u8, argument: u32, period: u64) -> Vec<u8> {
        let mut bytes = 1u32.to_be_bytes().to_vec();
        bytes.push(tag);
        bytes.extend_from_slice(&argument.to_be_bytes());
        if tag != POOL {
            bytes.extend_from_slice(&period.to_be_bytes());
        }
        bytes
    }
    #[test]
    fn closed_dependencies_refuse_cycles_wrong_kind_rows_periods_and_trailing_bytes() {
        let opening = opening();
        let seed_count = u32::try_from(opening.lookup().entries().len()).unwrap();
        assert_eq!(
            decode(&opening, 2, &body(FREIGHT, seed_count, 2), 1),
            Err(failure(Error::Kind))
        );
        assert_eq!(
            decode(&opening, 2, &body(FREIGHT, u32::MAX, 2), 1),
            Err(failure(Error::Reference))
        );
        assert_eq!(
            decode(&opening, 2, &body(HOUSEHOLD, u32::MAX, 2), 1),
            Err(failure(Error::Row))
        );
        assert_eq!(
            decode(&opening, 2, &body(HOUSEHOLD, 0, 3), 1),
            Err(failure(Error::Period))
        );
        assert_eq!(
            decode(&opening, 2, &body(255, 0, 2), 1),
            Err(failure(Error::Recipe))
        );
        assert_eq!(
            decode(&opening, 2, &body(127, 0, 2), 1),
            Err(StorageError::State(StateError::IdentityKind))
        );
        let wrong = opening
            .lookup()
            .entries()
            .iter()
            .position(|e| e.kind != K::Order)
            .unwrap();
        assert_eq!(
            decode(
                &opening,
                2,
                &body(FREIGHT, u32::try_from(wrong).unwrap(), 2),
                1,
            ),
            Err(failure(Error::Kind))
        );
        let mut trailing = body(HOUSEHOLD, 0, 2);
        trailing.push(0);
        assert_eq!(
            decode(&opening, 2, &trailing, 1),
            Err(StorageError::Trailing)
        );
        let mut truncated = body(HOUSEHOLD, 0, 2);
        truncated.pop();
        assert_eq!(
            decode(&opening, 2, &truncated, 1),
            Err(StorageError::Truncated)
        );
    }
}

#[cfg(test)]
mod freight_controls {
    use super::*;
    #[test]
    fn ordinary_freight_can_reference_forward_order_without_a_previous_table() {
        let session = monetary_fixture();
        let opening = OpeningRegister::from_opening(session.material()).unwrap();
        let order = IdentityEntry {
            kind: K::Order,
            bytes: [249; 32],
        };
        let lot = freight(order.bytes, 3);
        let table = [lot, order];
        let bytes = encode(&opening, 3, &table).unwrap();
        assert_eq!(bytes.len(), 4 + 13 + 33);
        assert_eq!(bytes[4], FREIGHT);
        assert_eq!(
            u32::from_be_bytes(bytes[5..9].try_into().unwrap()) as usize,
            opening.lookup().entries().len() + 1
        );
        assert_eq!(decode(&opening, 3, &bytes, 2).unwrap(), table);
    }
}
