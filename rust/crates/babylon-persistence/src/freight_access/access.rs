//! Directed access and admitted period corridor projection. Distances exclude terminal attachment.
use super::Reference;
use crate::observer_reader::{ObserverEconomySnapshot, ObserverVisibility};
use crate::production_observation::{
    PhysicalRouteIndex, ProductionRouteTransport, ProductionSnapshot,
};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AccessError {
    Read,
    Digest,
    Document,
    Source,
    Bound,
    Terminal,
    Pair,
    Authority,
    Corridor,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Access {
    Reachable { distance_mm: u64 },
    NoPermittedPath,
    Unqualified,
    OutsideCoverage,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum AccessDirection {
    #[default]
    Outbound,
    Inbound,
}
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct Corridor {
    pub route_id: String,
    pub distance_mm: Option<u64>,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AccessRow {
    pub peer: EconomicLocation,
    pub access: Access,
    pub corridors: Vec<Corridor>,
}

/// Designed display bands use inclusive upper boundaries on exact road millimetres.
#[must_use]
pub fn distance_band(mm: u64) -> &'static str {
    match mm {
        0..=50_000_000 => "0–50 km",
        50_000_001..=150_000_000 => "over 50–150 km",
        150_000_001..=300_000_000 => "over 150–300 km",
        _ => "over 300 km",
    }
}

impl Reference {
    /// Whether this matrix and any campaign road capture identify the same physical graph.
    #[must_use]
    pub fn graph_matches(&self, snapshot: &ProductionSnapshot) -> bool {
        snapshot
            .road_source
            .as_ref()
            .is_none_or(|s| s.graph_sha256 == self.graph_sha256)
    }

    /// Join the selected observer frame's disclosed, directed corridors to the independent regional reference.
    ///
    /// # Errors
    /// Rejects restricted frames and inconsistent economic corridor references.
    pub fn connections(
        &self,
        frame: &ObserverEconomySnapshot,
        origin: CountyGeoid,
        direction: AccessDirection,
    ) -> Result<Vec<AccessRow>, AccessError> {
        if frame.visibility != ObserverVisibility::FullObserver {
            return Err(AccessError::Authority);
        }
        let snapshot = frame.production.as_ref().ok_or(AccessError::Authority)?;
        let same_graph = self.graph_matches(snapshot);
        let home = EconomicLocation::domestic_county(origin).map_err(|_| AccessError::Terminal)?;
        let sites: BTreeMap<_, _> = snapshot
            .sites
            .iter()
            .map(|s| (s.id.as_str(), s.location))
            .collect();
        if sites.len() != snapshot.sites.len() {
            return Err(AccessError::Corridor);
        }
        let routes = PhysicalRouteIndex::try_new(snapshot).map_err(|_| AccessError::Corridor)?;
        let mut peers = BTreeMap::<EconomicLocation, BTreeSet<Corridor>>::new();
        if self.terminals.contains_key(&origin) {
            for county in self.terminals.keys() {
                peers
                    .entry(
                        EconomicLocation::domestic_county(*county)
                            .map_err(|_| AccessError::Terminal)?,
                    )
                    .or_default();
            }
        }
        for route in &snapshot.routes {
            let physical = routes.get(route).ok_or(AccessError::Corridor)?;
            if physical.transport_kind == ProductionRouteTransport::Local {
                continue;
            }
            let from = *sites
                .get(route.supplier_site_id.as_str())
                .ok_or(AccessError::Corridor)?;
            let to = *sites
                .get(route.buyer_site_id.as_str())
                .ok_or(AccessError::Corridor)?;
            let (source, peer) = match direction {
                AccessDirection::Outbound => (from, to),
                AccessDirection::Inbound => (to, from),
            };
            if source == home {
                peers.entry(peer).or_default().insert(Corridor {
                    route_id: physical.id.clone(),
                    distance_mm: physical.distance_mm.filter(|_| {
                        snapshot.road_source.is_some() && !physical.physical_edge_ids.is_empty()
                    }),
                });
            }
        }
        let mut rows: Vec<_> = peers
            .into_iter()
            .map(|(peer, corridors)| {
                let access = match (peer, direction) {
                    (EconomicLocation::County(c), AccessDirection::Outbound) => {
                        self.access(origin, c.geoid())
                    }
                    (EconomicLocation::County(c), AccessDirection::Inbound) => {
                        self.access(c.geoid(), origin)
                    }
                    _ => Access::OutsideCoverage,
                };
                let access = if !same_graph && access != Access::OutsideCoverage {
                    Access::Unqualified
                } else {
                    access
                };
                AccessRow {
                    peer,
                    access,
                    corridors: corridors.into_iter().collect(),
                }
            })
            .collect();
        rows.sort_by_key(|row| row.corridors.is_empty());
        Ok(rows)
    }
}
