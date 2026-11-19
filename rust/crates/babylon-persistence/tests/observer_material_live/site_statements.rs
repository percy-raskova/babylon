//! Reuse the journal test's actual national campaign for authenticated site joins.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, CircuitAccounting, SiteId};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::DurableMaterialRuntime;
use babylon_persistence::observer_reader::{
    CommittedMaterialReceipts, ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
};
use babylon_persistence::qualification_audit::trade;
use babylon_persistence::site_financial_statements::{
    PlanningControl, SiteFinancialStatements, SiteStatementsError,
};
use postgres::Config;
use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;

pub(super) fn opening(
    observer: &ObserverEconomyReader,
    owner_config: &Config,
    campaign: CampaignId,
    runtime: &DurableMaterialRuntime,
) -> SiteFinancialStatements {
    let CircuitAccounting::Monetary(economy) = &runtime.session().material().state().accounting
    else {
        panic!("actual national monetary opening");
    };
    let selected = economy
        .financial
        .ownership
        .first()
        .expect("actual captured ownership claim")
        .issuer_site_id;
    let opening = observer
        .site_financial_statements(campaign, 0, selected)
        .expect("authenticated opening site books");
    assert!(opening.books.opening.is_none());
    assert!(opening.books.activity.is_none());
    assert!(opening.receipt_digest.is_none());
    assert!(opening.tick_content_hash.is_none());
    assert_ne!(opening.books.ownership_claims, []);
    assert_eq!(opening.books.planning_control, PlanningControl::NotCaptured);
    assert_eq!(
        opening.books.closing.cash,
        economy
            .book
            .cash(AccountId::Site(selected))
            .expect("selected account")
    );
    assert_eq!(
        ObserverEconomyReader::connect(owner_config, ObserverVisibility::KnownPreview)
            .expect("restricted mode")
            .site_financial_statements(campaign, 0, selected),
        Err(SiteStatementsError::Read(ObserverEconomyError::Authority)),
    );
    assert_eq!(
        ObserverEconomyReader::connect(owner_config, ObserverVisibility::FullObserver)
            .expect("loopback owner target")
            .site_financial_statements(campaign, 0, selected),
        Err(SiteStatementsError::Read(ObserverEconomyError::Authority)),
        "labeling owner credentials full observer does not confer the database capability",
    );
    assert_eq!(
        observer.site_financial_statements(campaign, 0, SiteId::from_bytes([0xff; 32])),
        Err(SiteStatementsError::SiteAbsent)
    );
    opening
}

pub(super) fn period_one(
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    runtime: &DurableMaterialRuntime,
    source: &CommittedMaterialReceipts,
    opening: &SiteFinancialStatements,
) {
    let statements = observer
        .site_financial_statements(campaign, 1, opening.site_id)
        .expect("authenticated period one site books");
    assert_eq!(
        statements.books.opening.as_ref(),
        Some(&opening.books.closing)
    );
    assert_eq!(
        statements.receipt_digest,
        Some(source.identity.receipt_digest())
    );
    assert_eq!(
        statements.tick_content_hash,
        Some(*source.identity.tick_content_hash().as_bytes())
    );
    assert_eq!(
        statements.nominal_world_hash,
        Some(source.identity.result_world_hash())
    );
    assert_eq!(statements.foundation_digest, opening.foundation_digest);
    let account = AccountId::Site(opening.site_id);
    let activity = statements.books.activity.as_ref().expect("period activity");
    assert_eq!(
        &activity.income,
        source
            .receipts
            .income
            .iter()
            .find(|row| row.account == account)
            .expect("complete authoritative income")
    );
    let CircuitAccounting::Monetary(close) = &runtime.session().material().state().accounting
    else {
        panic!("actual national monetary close");
    };
    let actual_cash = close.book.cash(account).expect("selected cash");
    assert_eq!(statements.books.closing.cash, actual_cash);
    assert_eq!(activity.cash_flow.closing_cash, actual_cash);
    assert_eq!(activity.cash_flow.opening_cash, opening.books.closing.cash);
    let expected_delta = actual_cash
        .checked_sub(opening.books.closing.cash)
        .expect("cash difference");
    assert_eq!(activity.cash_flow.net_change_in_cash, expected_delta);
    let parts = [
        activity.cash_flow.operating,
        activity.cash_flow.investing,
        activity.cash_flow.financing,
        activity.cash_flow.reserve_reclassification,
    ];
    assert_eq!(
        parts
            .into_iter()
            .try_fold(Currency::from_micro_units(0), Currency::checked_add)
            .expect("exact flow sum"),
        expected_delta
    );
    for transfer in &activity.cash_flow.transfers {
        assert_eq!(
            transfer.transfer,
            source.receipts.money_transfers[transfer.receipt_index]
        );
    }
    assert_eq!(
        statements
            .books
            .closing
            .total_assets
            .checked_sub(statements.books.closing.total_liabilities)
            .expect("net assets"),
        statements.books.closing.total_equity
    );
    let equity_delta = statements
        .books
        .closing
        .total_equity
        .checked_sub(opening.books.closing.total_equity)
        .expect("equity change");
    assert_eq!(activity.change_in_equity, equity_delta);
    assert_eq!(
        equity_delta,
        activity
            .income
            .net_income
            .checked_add(activity.income.contributions_received)
            .and_then(|value| value.checked_sub(activity.income.distributions_paid))
            .expect("income/capital bridge")
    );
}

/// Opt in with an already built client; PostgreSQL-only jobs need no Bevy build.
pub(super) fn native_cli(
    observer_config: &Config,
    campaign: CampaignId,
    opening: &SiteFinancialStatements,
) {
    let Some(executable) = std::env::var_os("BABYLON_SITE_STATEMENTS_CLIENT_EXE") else {
        eprintln!("native site CLI smoke not requested (BABYLON_SITE_STATEMENTS_CLIENT_EXE unset)");
        return;
    };
    let executable = PathBuf::from(executable);
    assert!(
        executable.is_absolute() && executable.is_file(),
        "native site CLI smoke requires an absolute prebuilt executable path"
    );
    let logs = std::env::temp_dir().join(format!("babylon-site-cli-{}", std::process::id()));
    std::fs::create_dir(&logs).expect("create task-owned native CLI log directory");
    let observer_dsn = super::runtime_process::child_dsn(observer_config);
    let campaign_id = campaign.as_uuid().to_string();
    let site_id = trade::hex(&opening.site_id.as_bytes());
    let run = |args: &[&str]| -> Value {
        let output = Command::new(&executable)
            .args(["--headless", "--campaign", &campaign_id])
            .args(args)
            .env_clear()
            .env("BABYLON_OBSERVER_DSN", &observer_dsn)
            .env("XDG_DATA_HOME", &logs)
            .output()
            .expect("start the requested native client executable");
        assert!(
            output.status.success(),
            "native site command failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        serde_json::from_slice(&output.stdout).expect("one complete native JSON record")
    };
    let directory = run(&["economy", "sites"]);
    assert_eq!(directory["record"], "economy-sites");
    assert_eq!(directory["campaign_id"], campaign_id);
    assert_eq!(
        directory["resolve_tick"], 0,
        "the site directory stays on its foundation after period one commits"
    );
    let selected = directory["sites"]
        .as_array()
        .expect("site directory rows")
        .iter()
        .find(|row| row["site_id"] == site_id)
        .expect("the actual owned site is discoverable");
    assert_ne!(selected["label"].as_str().expect("readable label"), "");
    let statements = run(&["economy", "site", &site_id, "1"]);
    assert_eq!(statements["record"], "site-financial-statements");
    assert_eq!(statements["campaign_id"], campaign_id);
    assert_eq!(statements["site_id"], site_id);
    assert_eq!(statements["resolve_tick"], 1);
    assert_eq!(statements["visibility"], "full_observer");
    assert_eq!(
        statements["opening"]["cash"],
        opening.books.closing.cash.micro_units().to_string(),
        "the native statement uses the actual authenticated opening cash"
    );
    assert_eq!(
        statements["activity"]["cash_flow"]["closing_cash"],
        statements["closing"]["cash"]
    );
    assert_eq!(
        statements["foundation_digest"],
        directory["foundation_digest"]
    );
    assert_eq!(statements["activity"]["income"]["period"], 1);
    assert_eq!(
        statements["planning_control"]["availability"],
        "not_captured"
    );
    std::fs::remove_dir_all(&logs).expect("remove the exact task-owned native CLI log directory");
}
