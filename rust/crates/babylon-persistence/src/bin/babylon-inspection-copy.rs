//! Operator-only row transport from the exact pre-PER-293 schema to a fresh current destination.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::inspection_copy;
use postgres::Config;
use std::process::ExitCode;
use uuid::Uuid;

fn connection(name: &str) -> Result<Config, String> {
    std::env::var(name)
        .map_err(|_| format!("{name} is required"))?
        .parse()
        .map_err(|_| format!("{name} is invalid"))
}

fn run() -> Result<(), String> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let [flag, value] = args.as_slice() else {
        return Err("use --campaign <uuid>".into());
    };
    let id = Uuid::parse_str(value).map_err(|_| "invalid campaign")?;
    if flag != "--campaign" || id.is_nil() || id.to_string() != *value {
        return Err("use --campaign <canonical uuid>".into());
    }
    let report = inspection_copy::copy_campaign(
        &connection("BABYLON_PRE293_SOURCE_DSN")?,
        &connection("BABYLON_INSPECTION_TARGET_DSN")?,
        CampaignId::from_uuid(id),
    )
    .map_err(|e| e.to_string())?;
    let body = serde_json::to_string(&report).map_err(|_| "report serialization failed")?;
    println!("{body}");
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("{e}");
            ExitCode::FAILURE
        }
    }
}
