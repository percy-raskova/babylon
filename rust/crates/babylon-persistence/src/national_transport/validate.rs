use super::{
    model::{
        AllocationDirection, AllocationMode, CargoClass, CountyAllocationFactor,
        CountyTransportAccess, TransportFlows, TransportLink, TransportMode, TransportNode,
        TransportNodeKind, TransportPool, TransportService, UnavailableBulkAccess,
    },
    raw, NationalTransportError as Error,
};
use babylon_kernel::{
    economic_location::{EconomicLocation, ForeignCounterpart, UsDependency},
    geography::{CountyGeoid, NationalCountyRoster},
};
use std::collections::{BTreeMap, BTreeSet, VecDeque};

fn county(raw: &str, roster: &NationalCountyRoster) -> Result<CountyGeoid, Error> {
    let id = CountyGeoid::try_from(raw).map_err(|_| Error::County)?;
    if !roster.contains(id) {
        return Err(Error::County);
    }
    Ok(id)
}
fn location(raw: &str, roster: &NationalCountyRoster) -> Result<EconomicLocation, Error> {
    let (kind, key) = raw.split_once(':').ok_or(Error::Location)?;
    match kind {
        "county" => {
            EconomicLocation::domestic_county(county(key, roster)?).map_err(|_| Error::Location)
        }
        "foreign" => ForeignCounterpart::from_key(key)
            .map(EconomicLocation::Foreign)
            .ok_or(Error::Location),
        "dependency" => UsDependency::from_m49(key)
            .map(EconomicLocation::Dependency)
            .ok_or(Error::Location),
        _ => Err(Error::Location),
    }
}
fn point(latitude: Option<&str>, longitude: Option<&str>) -> Result<(), Error> {
    match (latitude, longitude) {
        (None, None) => Ok(()),
        (Some(lat), Some(lon)) => {
            let lat: f64 = lat.parse().map_err(|_| Error::Location)?;
            let lon: f64 = lon.parse().map_err(|_| Error::Location)?;
            if lat.is_finite() && lon.is_finite() && lat.abs() <= 90.0 && lon.abs() <= 180.0 {
                Ok(())
            } else {
                Err(Error::Location)
            }
        }
        _ => Err(Error::Location),
    }
}
pub(super) fn nodes(
    rows: Vec<raw::Node>,
    roster: &NationalCountyRoster,
) -> Result<Vec<TransportNode>, Error> {
    let mut output = Vec::with_capacity(rows.len());
    for row in rows {
        if row.id.is_empty()
            || row.id.len() > 128
            || !row.id.is_ascii()
            || output
                .last()
                .is_some_and(|previous: &TransportNode| previous.id >= row.id)
        {
            return Err(Error::Node);
        }
        point(row.latitude.as_deref(), row.longitude.as_deref())?;
        let place = location(&row.location, roster)?;
        let valid_actor = match row.kind {
            TransportNodeKind::County => matches!(place, EconomicLocation::County(_)),
            TransportNodeKind::Foreign => matches!(place, EconomicLocation::Foreign(_)),
            TransportNodeKind::Dependency => matches!(place, EconomicLocation::Dependency(_)),
            _ => true,
        };
        if !valid_actor
            || (matches!(
                row.kind,
                TransportNodeKind::County
                    | TransportNodeKind::Foreign
                    | TransportNodeKind::Dependency
            ) && row.id != row.location)
        {
            return Err(Error::Location);
        }
        output.push(TransportNode {
            id: row.id,
            kind: row.kind,
            location: place,
            latitude: row.latitude,
            longitude: row.longitude,
            source_id: row.source_id,
            source_key: row.source_key,
        });
    }
    let counties = output
        .iter()
        .filter(|n| n.kind == TransportNodeKind::County)
        .count();
    let foreign = output
        .iter()
        .filter(|n| n.kind == TransportNodeKind::Foreign)
        .count();
    let dependencies = output
        .iter()
        .filter(|n| n.kind == TransportNodeKind::Dependency)
        .count();
    if counties != 3144 || foreign != 12 || dependencies != 6 {
        return Err(Error::Coverage);
    }
    Ok(output)
}
pub(super) fn links(
    rows: &[TransportLink],
    nodes: &[TransportNode],
    pools: &[TransportPool],
    services: &BTreeMap<String, TransportService>,
) -> Result<(), Error> {
    let node_ids: BTreeMap<&str, &TransportNode> =
        nodes.iter().map(|n| (n.id.as_str(), n)).collect();
    let pool_ids: BTreeSet<&str> = pools.iter().map(|n| n.id.as_str()).collect();
    if pool_ids.len() != pools.len()
        || pools.iter().any(|p| p.capacity_grams == 0)
        || !pools.windows(2).all(|pair| pair[0].id < pair[1].id)
    {
        return Err(Error::Pool);
    }
    if !rows.windows(2).all(|pair| pair[0].id < pair[1].id) {
        return Err(Error::Link);
    }
    for row in rows {
        let profile = services.get(&row.profile).ok_or(Error::Profile)?;
        if profile.mode != row.mode
            || profile.travel_periods == 0
            || profile.capacity_grams == 0
            || profile.cost_micros_per_tonne == 0
            || i64::try_from(profile.cost_micros_per_tonne).is_err()
            || profile.loss_ppm > 1_000_000
        {
            return Err(Error::Profile);
        }
        if row.cargo.is_empty()
            || !row.cargo.windows(2).all(|pair| pair[0] < pair[1])
            || (row.mode == TransportMode::Air && row.cargo != [CargoClass::General])
            || (row.mode == TransportMode::Pipeline && row.cargo != [CargoClass::CrudeOil])
        {
            return Err(Error::ModeCargo);
        }
        if !node_ids.contains_key(row.from.as_str())
            || !node_ids.contains_key(row.to.as_str())
            || row.from == row.to
        {
            return Err(Error::Endpoint);
        }
        truck_access(row, node_ids[row.from.as_str()], node_ids[row.to.as_str()])?;
        if row.pools.is_empty()
            || !row.pools.windows(2).all(|pair| pair[0] < pair[1])
            || row.pools.iter().any(|id| !pool_ids.contains(id.as_str()))
        {
            return Err(Error::Pool);
        }
    }
    Ok(())
}
fn island_county(county: CountyGeoid) -> bool {
    matches!(county.state_fips(), [b'0', b'2'] | [b'1', b'5'])
        || ["25007", "25019", "53055"].contains(&county.as_str())
}
fn truck_access(
    link: &TransportLink,
    from: &TransportNode,
    to: &TransportNode,
) -> Result<(), Error> {
    if link.mode != TransportMode::Truck || from.location == to.location {
        return Ok(());
    }
    let (EconomicLocation::County(a), EconomicLocation::County(b)) = (from.location, to.location)
    else {
        return Ok(());
    };
    if (island_county(a.geoid()) || island_county(b.geoid()))
        && !matches!(
            (a.geoid().as_str(), b.geoid().as_str()),
            ("02063", "02090") | ("02090", "02063")
        )
    {
        return Err(Error::Access);
    }
    Ok(())
}
pub(super) fn access(
    rows: Vec<raw::CountyAccess>,
    nodes: &[TransportNode],
    roster: &NationalCountyRoster,
) -> Result<Vec<CountyTransportAccess>, Error> {
    let ids: BTreeSet<&str> = nodes.iter().map(|n| n.id.as_str()).collect();
    let mut result = Vec::with_capacity(rows.len());
    for row in rows {
        let county = county(&row.county, roster)?;
        if row.zone.len() != 3
            || !row.zone.bytes().all(|b| b.is_ascii_digit())
            || row
                .airport
                .as_ref()
                .is_some_and(|id| !ids.contains(format!("airport:{id}").as_str()))
            || result
                .last()
                .is_some_and(|r: &CountyTransportAccess| r.county >= county)
        {
            return Err(Error::Access);
        }
        let island = island_county(county);
        if island != row.airport.is_some() {
            return Err(Error::Access);
        }
        result.push(CountyTransportAccess {
            county,
            zone: row.zone,
            airport: row.airport,
        });
    }
    if result.len() != 3144 {
        return Err(Error::Coverage);
    }
    Ok(result)
}
pub(super) fn decimal(raw: &str) -> Result<(), Error> {
    if raw.is_empty() || raw.len() > 96 {
        return Err(Error::Decimal);
    }
    let parts: Vec<_> = raw.split(['e', 'E']).collect();
    if parts.len() > 2 {
        return Err(Error::Decimal);
    }
    if parts.len() == 2 {
        let exponent: i16 = parts[1].parse().map_err(|_| Error::Decimal)?;
        if !(-60..=60).contains(&exponent) {
            return Err(Error::Decimal);
        }
    }
    let mantissa = parts[0];
    if mantissa.is_empty()
        || mantissa.starts_with('.')
        || mantissa.ends_with('.')
        || mantissa.bytes().filter(|b| *b == b'.').count() > 1
        || !mantissa.bytes().all(|b| b.is_ascii_digit() || b == b'.')
    {
        return Err(Error::Decimal);
    }
    Ok(())
}
pub(super) fn flows(value: &TransportFlows, access: &[CountyTransportAccess]) -> Result<(), Error> {
    let zones: BTreeSet<&str> = access.iter().map(|row| row.zone.as_str()).collect();
    let mut total = 0_usize;
    for (rows, width) in raw::flow_collections(value) {
        total = total.checked_add(rows.len()).ok_or(Error::Bound)?;
        if !rows.windows(2).all(|pair| pair[0].key < pair[1].key) {
            return Err(Error::Flow);
        }
        for row in rows {
            if row.key.len() != width || row.rows == 0 {
                return Err(Error::Flow);
            }
            flow_key(&row.key, &zones)?;
            for cell in &row.values {
                decimal(&cell.known_sum)?;
                if cell.published > row.rows
                    || (cell.published == 0
                        && cell.known_sum.split(['e', 'E']).next().is_none_or(|part| {
                            !part.bytes().all(|byte| byte == b'0' || byte == b'.')
                        }))
                {
                    return Err(Error::Flow);
                }
            }
        }
    }
    if total > 40_000 || value.source_rows == 0 {
        return Err(Error::Bound);
    }
    let count = |rows: &[super::model::FlowEvidence]| {
        rows.iter().try_fold(0_u64, |sum, row| {
            sum.checked_add(row.rows).ok_or(Error::Flow)
        })
    };
    let domestic = value
        .controls
        .iter()
        .filter(|row| row.key[0] == "1")
        .try_fold(0_u64, |sum, row| {
            sum.checked_add(row.rows).ok_or(Error::Flow)
        })?;
    if count(&value.controls)? != value.source_rows
        || count(&value.foreign)? != value.source_rows.checked_sub(domestic).ok_or(Error::Flow)?
        || count(&value.domestic)? > domestic
        || value.domestic_aggregate_rows
            < u64::try_from(value.domestic.len()).map_err(|_| Error::Bound)?
    {
        return Err(Error::Flow);
    }
    Ok(())
}
fn flow_key(key: &[String], zones: &BTreeSet<&str>) -> Result<(), Error> {
    let mode = |value: &str| value.len() == 1 && (b'1'..=b'8').contains(&value.as_bytes()[0]);
    let valid = match key {
        [a, b, m, _] => zones.contains(a.as_str()) && zones.contains(b.as_str()) && mode(m),
        [trade, foreign, external, domestic, _] => {
            ["2", "3"].contains(&trade.as_str())
                && ["801", "802", "803", "804", "805", "806", "807", "808"]
                    .contains(&foreign.as_str())
                && mode(external)
                && mode(domestic)
        }
        [trade, m, _] => ["1", "2", "3"].contains(&trade.as_str()) && mode(m),
        _ => false,
    };
    if !valid
        || !key.last().is_some_and(|group| {
            ["sctg0109", "sctg1014", "sctg1519", "sctg2033", "sctg3499"].contains(&group.as_str())
        })
    {
        return Err(Error::Flow);
    }
    Ok(())
}
pub(super) fn factors(
    rows: &[[String; 7]],
    access: &[CountyTransportAccess],
    roster: &NationalCountyRoster,
) -> Result<Vec<CountyAllocationFactor>, Error> {
    if rows.len() > 100_000 || !rows.windows(2).all(|pair| pair[0][..5] < pair[1][..5]) {
        return Err(Error::Factor);
    }
    let map: BTreeMap<_, _> = access
        .iter()
        .map(|r| (r.county.as_str(), r.zone.as_str()))
        .collect();
    let zones: BTreeSet<&str> = map.values().copied().collect();
    let mut truck = BTreeSet::new();
    let mut result = Vec::with_capacity(rows.len());
    for row in rows {
        if !["truck", "rail", "water", "pipeline"].contains(&row[0].as_str())
            || !["origin", "destination"].contains(&row[1].as_str())
            || !["sctg0109", "sctg1014", "sctg1519", "sctg2033", "sctg3499"]
                .contains(&row[4].as_str())
            || !map.contains_key(row[2].as_str())
            || !zones.contains(row[3].as_str())
            || (row[0] == "truck" && map.get(row[2].as_str()).copied() != Some(row[3].as_str()))
        {
            return Err(Error::Factor);
        }
        decimal(&row[5])?;
        if row[6] != "1" && row[6] != "2" {
            return Err(Error::Factor);
        }
        if row[0] == "truck" {
            truck.insert((&row[1], &row[2], &row[4]));
        }
        result.push(CountyAllocationFactor {
            mode: match row[0].as_str() {
                "truck" => AllocationMode::Truck,
                "rail" => AllocationMode::Rail,
                "water" => AllocationMode::Water,
                "pipeline" => AllocationMode::Pipeline,
                _ => return Err(Error::Factor),
            },
            direction: if row[1] == "origin" {
                AllocationDirection::Origin
            } else {
                AllocationDirection::Destination
            },
            county: county(&row[2], roster)?,
            zone: row[3].clone(),
            commodity_group: row[4].clone(),
            decimal_factor: row[5].clone(),
            source_rows: row[6].parse().map_err(|_| Error::Factor)?,
        });
    }
    if truck.len() != 31_440 {
        return Err(Error::Factor);
    }
    Ok(result)
}
fn adjacency(
    nodes: &[TransportNode],
    links: &[TransportLink],
    cargo: CargoClass,
    reverse: bool,
) -> Vec<Vec<usize>> {
    let indices: BTreeMap<_, _> = nodes
        .iter()
        .enumerate()
        .map(|(i, n)| (n.id.as_str(), i))
        .collect();
    let mut edges = vec![Vec::new(); nodes.len()];
    for link in links.iter().filter(|l| l.cargo.contains(&cargo)) {
        let (a, b) = if reverse {
            (&link.to, &link.from)
        } else {
            (&link.from, &link.to)
        };
        edges[indices[a.as_str()]].push(indices[b.as_str()]);
    }
    edges
}
fn distances(edges: &[Vec<usize>], origin: usize) -> Vec<usize> {
    let mut lengths = vec![usize::MAX; edges.len()];
    let mut queue = VecDeque::from([origin]);
    lengths[origin] = 0;
    while let Some(node) = queue.pop_front() {
        for &next in &edges[node] {
            if lengths[next] == usize::MAX {
                lengths[next] = lengths[node] + 1;
                queue.push_back(next);
            }
        }
    }
    lengths
}
pub(super) fn audit(
    value: &raw::Audit,
    nodes: &[TransportNode],
    links: &[TransportLink],
    access: &[CountyTransportAccess],
) -> Result<Vec<UnavailableBulkAccess>, Error> {
    let targets: Vec<_> = nodes
        .iter()
        .enumerate()
        .filter(|(_, node)| {
            matches!(
                node.kind,
                TransportNodeKind::County
                    | TransportNodeKind::Foreign
                    | TransportNodeKind::Dependency
            )
        })
        .map(|(i, _)| i)
        .collect();
    let edges = adjacency(nodes, links, CargoClass::General, false);
    let mut maximum = 0;
    for &origin in &targets {
        let paths = distances(&edges, origin);
        for &target in &targets {
            maximum = maximum.max(paths[target]);
        }
    }
    if maximum > babylon_material_circuit::MAX_ROUTE_STAGES_PER_ROUTE {
        return Err(Error::Reachability);
    }
    if maximum != value.general_diameter || targets.len() != value.general_targets {
        return Err(Error::Audit);
    }
    let control = nodes
        .binary_search_by(|n| n.id.as_str().cmp("county:17031"))
        .map_err(|_| Error::Audit)?;
    let mut result = Vec::new();
    for cargo in [
        CargoClass::DryBulk,
        CargoClass::CrudeOil,
        CargoClass::RefinedLiquid,
    ] {
        let receive = distances(&adjacency(nodes, links, cargo, false), control);
        let supply = distances(&adjacency(nodes, links, cargo, true), control);
        for row in access {
            let id = format!("county:{}", row.county);
            let index = nodes
                .binary_search_by(|n| n.id.as_str().cmp(&id))
                .map_err(|_| Error::Audit)?;
            let can_receive = receive[index] != usize::MAX;
            let can_supply = supply[index] != usize::MAX;
            if !can_receive || !can_supply {
                result.push(UnavailableBulkAccess {
                    county: row.county,
                    cargo,
                    can_receive,
                    can_supply,
                });
            }
        }
    }
    if result.len() != value.unavailable_bulk_counties.len() {
        return Err(Error::Audit);
    }
    for (actual, expected) in result.iter().zip(&value.unavailable_bulk_counties) {
        if actual.county.as_str() != expected.county
            || actual.cargo != expected.cargo
            || actual.can_receive != expected.can_receive
            || actual.can_supply != expected.can_supply
        {
            return Err(Error::Audit);
        }
    }
    Ok(result)
}
