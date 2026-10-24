//! Confined read-only facts for the actual native game's committed boundaries.
//! This operator never creates a campaign, advances a tick or drives Archive.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::qualification_audit::policy::FrozenPolicy;
use babylon_persistence::qualification_audit::reader::{ReadSession, Request};
use babylon_persistence::qualification_audit::Scope;
use babylon_persistence::SemanticArchiveReader;

use babylon_persistence::qualification_audit::policy;
use babylon_persistence::qualification_audit::reader;
use babylon_persistence::qualification_audit::reader::Refusal;
use serde_json::json;
use std::collections::BTreeMap;
use std::fmt::Formatter;
use std::io;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use uuid::Uuid;

const REQUEST_BYTES: u64 = 4096;
const RESPONSE_BYTES: usize = 4_194_304;

struct Configuration {
    policy: FrozenPolicy,
    scope: Scope,
    view: View,
}
type Result<T> = std::result::Result<T, &'static str>;

#[derive(Debug, PartialEq, Eq)]
enum View {
    Material,
    Archive([u8; 32]),
}

enum Reader {
    Material(Box<ReadSession>),
    Archive {
        reader: Box<SemanticArchiveReader>,
        graph: [u8; 32],
    },
}

fn view(value: &str, graph: Option<&str>) -> Result<View> {
    match (value, graph) {
        ("material", None) => Ok(View::Material),
        ("material", Some(_)) => Err("arguments_refused"),
        ("archive", None) => Err("graph_foundation_absent"),
        ("archive", Some(graph)) => {
            let graph = digest(graph).map_err(|_| "graph_foundation_refused")?;
            if graph == [0; 32] {
                return Err("graph_foundation_refused");
            }
            Ok(View::Archive(graph))
        }
        _ => Err("view_refused"),
    }
}

enum OperatorRefusal {
    Operator(&'static str),
    Boundary(Refusal),
}
impl From<&'static str> for OperatorRefusal {
    fn from(code: &'static str) -> Self {
        Self::Operator(code)
    }
}
impl std::fmt::Display for OperatorRefusal {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Operator(code) => f.write_str(code),
            Self::Boundary(reason) => write!(f, "{reason}"),
        }
    }
}

fn digest(value: &str) -> Result<[u8; 32]> {
    policy::canonical_digest(value).map_err(|_| "digest_refused")
}

fn configuration(arguments: impl Iterator<Item = String>) -> Result<Configuration> {
    let mut arguments = arguments;
    let mut flags = BTreeMap::new();
    while let Some(flag) = arguments.next() {
        if ![
            "--campaign",
            "--foundation",
            "--policy",
            "--policy-sha256",
            "--periods",
            "--view",
            "--graph-foundation",
        ]
        .contains(&flag.as_str())
        {
            return Err("arguments_refused");
        }
        let value = arguments.next().ok_or("arguments_refused")?;
        if flags.insert(flag, value).is_some() {
            return Err("arguments_refused");
        }
    }
    let get = |key: &str| flags.get(key).ok_or("arguments_refused");
    let campaign = Uuid::parse_str(get("--campaign")?).map_err(|_| "campaign_refused")?;
    if campaign.is_nil() || campaign.to_string() != *get("--campaign")? {
        return Err("campaign_refused");
    }
    let foundation = digest(get("--foundation")?)?;
    let policy_sha256 = digest(get("--policy-sha256")?)?;
    let policy_path = PathBuf::from(get("--policy")?);
    let periods = get("--periods")?
        .parse::<u64>()
        .map_err(|_| "periods_refused")?;
    if periods == 0 || periods.to_string() != *get("--periods")? {
        return Err("periods_refused");
    }
    let policy =
        FrozenPolicy::open(&policy_path, policy_sha256, periods).map_err(|_| "policy_refused")?;
    Ok(Configuration {
        scope: policy.scope(CampaignId::from_uuid(campaign), foundation),
        policy,
        view: view(
            flags.get("--view").map_or("material", String::as_str),
            flags.get("--graph-foundation").map(String::as_str),
        )?,
    })
}

fn run(
    configuration: &Configuration,
    input: impl Read,
    mut output: impl Write,
) -> std::result::Result<(), OperatorRefusal> {
    let archive = std::env::var("BABYLON_NATIONAL_STORAGE_READER_DSN")
        .map_err(|_| "archive_credential_absent")?;
    let mut reader = match configuration.view {
        View::Material => {
            let observer = std::env::var("BABYLON_NATIONAL_STORAGE_OBSERVER_DSN")
                .map_err(|_| "observer_credential_absent")?
                .parse()
                .map_err(|_| "observer_credential_refused")?;
            Reader::Material(Box::new(
                ReadSession::new(configuration.scope, &observer, &archive)
                    .map_err(|_| "reader_admission_refused")?,
            ))
        }
        View::Archive(graph) => Reader::Archive {
            reader: Box::new(
                SemanticArchiveReader::from_dsn(&archive)
                    .map_err(|_| "reader_admission_refused")?,
            ),
            graph,
        },
    };
    let mut input = BufReader::new(input);
    loop {
        let mut line = Vec::new();
        let count = Read::by_ref(&mut input)
            .take(REQUEST_BYTES + 1)
            .read_until(b'\n', &mut line)
            .map_err(|_| "request_read_failed")?;
        if count == 0 {
            return Ok(());
        }
        if u64::try_from(count).map_err(|_| "request_unbounded")? > REQUEST_BYTES
            || line.last() != Some(&b'\n')
        {
            return Err("request_unbounded".into());
        }
        let request: Request =
            serde_json::from_slice(&line).map_err(|_| "request_fields_refused")?;
        if request.tick > configuration.policy.periods() {
            return Err("requested_horizon_exceeded".into());
        }
        configuration
            .policy
            .verify()
            .map_err(|_| "policy_changed_or_unbounded")?;
        let bytes = match &mut reader {
            Reader::Material(session) => {
                let result = session.read(&request).map_err(OperatorRefusal::Boundary)?;
                serde_json::to_vec(&result)
            }
            Reader::Archive { reader, graph } => {
                let result =
                    reader::read_archive_boundary(configuration.scope, *graph, reader, &request)
                        .map_err(OperatorRefusal::Boundary)?;
                serde_json::to_vec(&result)
            }
        }
        .map_err(|_| "response_encode_failed")?;
        configuration
            .policy
            .verify()
            .map_err(|_| "policy_changed_or_unbounded")?;
        if bytes.len() > RESPONSE_BYTES {
            return Err("response_unbounded".into());
        }
        output
            .write_all(&bytes)
            .and_then(|()| output.write_all(b"\n"))
            .and_then(|()| output.flush())
            .map_err(|_| "response_write_failed")?;
    }
}

fn main() -> ExitCode {
    let result = configuration(std::env::args().skip(1))
        .map_err(OperatorRefusal::Operator)
        .and_then(|configuration| run(&configuration, io::stdin().lock(), io::stdout().lock()));
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(code) => {
            // Driver errors and credentials never enter stdout/stderr evidence.
            eprintln!(
                "{}",
                json!({"version":1,"status":"refused","code":code.to_string()})
            );
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::View;
    #[test]
    fn operator_has_no_command_port_or_implicit_campaign() {
        for arguments in [
            vec![],
            vec!["--advance", "1"],
            vec!["--campaign", "x", "--campaign", "y"],
        ] {
            assert!(super::configuration(arguments.into_iter().map(str::to_owned)).is_err());
        }
        assert_eq!(super::digest(&"A".repeat(64)), Err("digest_refused"));
        assert_eq!(super::digest(&"a".repeat(64)), Ok([0xaa; 32]));
        assert_eq!(super::view("material", None), Ok(View::Material));
        assert_eq!(
            super::view("archive", Some(&"a".repeat(64))),
            Ok(View::Archive([0xaa; 32]))
        );
        assert_eq!(
            super::view("material", Some(&"a".repeat(64))),
            Err("arguments_refused")
        );
        assert_eq!(super::view("archive", None), Err("graph_foundation_absent"));
        assert_eq!(
            super::view("archive", Some(&"0".repeat(64))),
            Err("graph_foundation_refused")
        );
        for forbidden in ["", "all", "advance", "new", "sql", "Archive"] {
            assert_eq!(super::view(forbidden, None), Err("view_refused"));
        }
    }
}
