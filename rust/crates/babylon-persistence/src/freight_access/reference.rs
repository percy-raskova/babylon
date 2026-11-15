//! Admit the published, turn-aware county matrix against the statewide source manifest.
use super::{Access, AccessError};
use crate::michigan_material::{
    MichiganCountyTerminal, MichiganRoadSource, MichiganTerminalPolicy,
};
use crate::national_transport::{self, TransportNodeKind};
use babylon_kernel::content_digest;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use flate2::read::GzDecoder;
use serde::de::DeserializeOwned;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::fs::File;
use std::io::Read;
use std::path::Path;

const MATRIX_LIMIT: u64 = 512 * 1024 * 1024;
const MANIFEST: &[u8] =
    include_bytes!("../../../../../content/scenarios/michigan/statewide-sources.json");
const PHYSICAL: &[u8] =
    include_bytes!("../../../../../content/scenarios/michigan/statewide-physical.json.gz");
const QUALIFICATION: &[u8] =
    include_bytes!("../../../../../content/scenarios/michigan/statewide-qualification.json.gz");

#[derive(Deserialize)]
struct Manifest {
    schema: String,
    physical_network_sha256: String,
    qualification_sha256: String,
}
#[derive(Deserialize)]
struct Qualification {
    schema: String,
    qualified: bool,
    paths_sha256: String,
}
#[derive(Deserialize)]
struct Physical {
    source: MichiganRoadSource,
    terminal_source_pins: BTreeMap<String, String>,
    terminal_policy: MichiganTerminalPolicy,
    terminals: Vec<MichiganCountyTerminal>,
}
#[derive(Deserialize)]
struct Matrix {
    schema: String,
    source_pins: BTreeMap<String, String>,
    policy: MichiganTerminalPolicy,
    terminals: Vec<MichiganCountyTerminal>,
    paths: Vec<Pair>,
}
#[derive(Deserialize)]
struct Pair {
    source_county_geoid: String,
    destination_county_geoid: String,
    path: Option<PathDistance>,
}
#[derive(Deserialize)]
struct PathDistance {
    distance_mm: u64,
}

/// One static Great Lakes truck-network reference. Observed campaign corridors remain separate.
#[derive(Debug)]
pub struct Reference {
    pub graph_sha256: String,
    pub matrix_sha256: String,
    pub source_date: String,
    pub profile: String,
    pub supplement_error: Option<AccessError>,
    airports: BTreeMap<CountyGeoid, Vec<AirportPoint>>,
    pub(crate) terminals: BTreeMap<CountyGeoid, MichiganCountyTerminal>,
    pins: BTreeMap<String, String>,
    policy: MichiganTerminalPolicy,
    paths: Option<BTreeMap<(CountyGeoid, CountyGeoid), Option<u64>>>,
}

/// Selected FAA public/open point in the pinned national facility reference.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AirportPoint {
    pub id: String,
    pub name: String,
    pub latitude: String,
    pub longitude: String,
    pub effective_date: String,
}

fn airports() -> Result<BTreeMap<CountyGeoid, Vec<AirportPoint>>, AccessError> {
    let reference =
        national_transport::national_transport_reference().map_err(|_| AccessError::Source)?;
    let facilities: BTreeMap<_, _> = reference
        .facilities()
        .iter()
        .map(|f| ((f.source_id.as_str(), f.key.as_str()), f))
        .collect();
    let mut points = BTreeMap::<CountyGeoid, Vec<AirportPoint>>::new();
    for node in reference
        .nodes()
        .iter()
        .filter(|n| n.kind() == TransportNodeKind::Airport)
    {
        let EconomicLocation::County(county) = node.location() else {
            continue;
        };
        let (latitude, longitude) = node.point().ok_or(AccessError::Source)?;
        let facility = facilities.get(&node.source()).ok_or(AccessError::Source)?;
        let field = |name: &str| {
            facility
                .fields
                .get(name)
                .and_then(Option::as_ref)
                .cloned()
                .ok_or(AccessError::Source)
        };
        points
            .entry(county.geoid())
            .or_default()
            .push(AirportPoint {
                id: node.id().to_owned(),
                name: field("ARPT_NAME")?,
                effective_date: field("EFF_DATE")?,
                latitude: latitude.to_owned(),
                longitude: longitude.to_owned(),
            });
    }
    Ok(points)
}

fn digest(bytes: &[u8]) -> String {
    crate::michigan_economy::digest_hex(&content_digest::sha256_of(bytes))
}

fn decode<T: DeserializeOwned>(bytes: &[u8], expected: &str, limit: u64) -> Result<T, AccessError> {
    if digest(bytes) != expected {
        return Err(AccessError::Digest);
    }
    let mut input = GzDecoder::new(bytes).take(limit + 1);
    let document = serde_json::from_reader(&mut input).map_err(|_| AccessError::Document)?;
    if input.limit() == 0 {
        return Err(AccessError::Bound);
    }
    Ok(document)
}

fn roster(
    rows: Vec<MichiganCountyTerminal>,
) -> Result<BTreeMap<CountyGeoid, MichiganCountyTerminal>, AccessError> {
    let mut map = BTreeMap::new();
    for row in rows {
        let id =
            CountyGeoid::try_from(row.county_geoid.as_str()).map_err(|_| AccessError::Terminal)?;
        if !id.as_str().starts_with("26")
            || row.status != "attached"
            || map.insert(id, row).is_some()
        {
            return Err(AccessError::Terminal);
        }
    }
    Ok(map)
}

impl Reference {
    /// Read the bundled reference capture and optionally the exact compressed path product.
    ///
    /// # Errors
    /// Refuses an invalid bundled reference. A rejected supplemental matrix is retained
    /// as a diagnostic beside the authenticated source and its terminal coverage.
    pub fn load(path: Option<&Path>) -> Result<Self, AccessError> {
        let manifest: Manifest =
            serde_json::from_slice(MANIFEST).map_err(|_| AccessError::Document)?;
        let physical: Physical = decode(PHYSICAL, &manifest.physical_network_sha256, MATRIX_LIMIT)?;
        let qualification: Qualification =
            decode(QUALIFICATION, &manifest.qualification_sha256, MATRIX_LIMIT)?;
        if manifest.schema != "MichiganStatewideSourcesV1"
            || qualification.schema != "MichiganCommodityCircuitV1"
            || !qualification.qualified
            || physical.terminal_source_pins.get("graph_sha256")
                != Some(&physical.source.graph_sha256)
        {
            return Err(AccessError::Source);
        }
        let mut reference = Self {
            graph_sha256: physical.source.graph_sha256,
            matrix_sha256: qualification.paths_sha256,
            source_date: physical.source.replication_timestamp,
            profile: physical.source.routing_profile_version,
            supplement_error: None,
            airports: airports()?,
            terminals: roster(physical.terminals)?,
            pins: physical.terminal_source_pins,
            policy: physical.terminal_policy,
            paths: None,
        };
        if reference.terminals.len() != 83 {
            return Err(AccessError::Terminal);
        }
        reference.supplement_error = path.and_then(|p| reference.admit_file(p).err());
        Ok(reference)
    }
    fn admit_file(&mut self, path: &Path) -> Result<(), AccessError> {
        let mut bytes = Vec::new();
        File::open(path)
            .map_err(|_| AccessError::Read)?
            .take(MATRIX_LIMIT + 1)
            .read_to_end(&mut bytes)
            .map_err(|_| AccessError::Read)?;
        if bytes.len() as u64 > MATRIX_LIMIT {
            return Err(AccessError::Bound);
        }
        self.admit(&bytes)
    }

    /// Source points selected in the national facility reference. The list does not cover every airport.
    #[must_use]
    pub fn airport_points(&self, county: CountyGeoid) -> &[AirportPoint] {
        self.airports
            .get(&county)
            .map(Vec::as_slice)
            .unwrap_or_default()
    }

    pub(super) fn admit(&mut self, bytes: &[u8]) -> Result<(), AccessError> {
        let matrix: Matrix = decode(bytes, &self.matrix_sha256, MATRIX_LIMIT)?;
        if matrix.schema != "MichiganCountyPathMatrixV1"
            || matrix.source_pins != self.pins
            || matrix.policy != self.policy
            || roster(matrix.terminals)? != self.terminals
        {
            return Err(AccessError::Source);
        }
        let mut paths = BTreeMap::new();
        for row in matrix.paths {
            let from = CountyGeoid::try_from(row.source_county_geoid.as_str())
                .map_err(|_| AccessError::Terminal)?;
            let to = CountyGeoid::try_from(row.destination_county_geoid.as_str())
                .map_err(|_| AccessError::Terminal)?;
            if !self.terminals.contains_key(&from)
                || !self.terminals.contains_key(&to)
                || paths
                    .insert((from, to), row.path.map(|p| p.distance_mm))
                    .is_some()
            {
                return Err(AccessError::Pair);
            }
        }
        if paths.len() != self.terminals.len() * self.terminals.len()
            || self
                .terminals
                .keys()
                .any(|&t| paths.get(&(t, t)) != Some(&Some(0)))
        {
            return Err(AccessError::Pair);
        }
        self.paths = Some(paths);
        Ok(())
    }

    #[must_use]
    pub fn access(&self, from: CountyGeoid, to: CountyGeoid) -> Access {
        if !self.terminals.contains_key(&from) || !self.terminals.contains_key(&to) {
            return Access::OutsideCoverage;
        }
        match self.paths.as_ref().and_then(|p| p.get(&(from, to))) {
            Some(Some(distance_mm)) => Access::Reachable {
                distance_mm: *distance_mm,
            },
            Some(None) => Access::NoPermittedPath,
            None => Access::Unqualified,
        }
    }

    #[must_use]
    pub fn qualified(&self) -> bool {
        self.paths.is_some()
    }

    #[cfg(test)]
    pub(super) fn fixture(text: &str, bytes: &[u8]) -> Self {
        let matrix: Matrix = serde_json::from_str(text).expect("router fixture");
        Self {
            graph_sha256: matrix.source_pins["graph_sha256"].clone(),
            matrix_sha256: digest(bytes),
            source_date: String::new(),
            profile: String::new(),
            supplement_error: None,
            airports: BTreeMap::new(),
            terminals: roster(matrix.terminals).expect("fixture terminals"),
            pins: matrix.source_pins,
            policy: matrix.policy,
            paths: None,
        }
    }
}
