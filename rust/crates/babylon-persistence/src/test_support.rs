//! Explicit shipped-content fixture for native unit tests only.
use crate::michigan_material::MichiganMaterialCatalog;
use babylon_tick::material_world::MaterialTickReceipts;

pub(crate) fn catalog() -> MichiganMaterialCatalog {
    MichiganMaterialCatalog::from_defines_toml(
        &include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/michigan/defines.toml"
        ))
        .replace(
            "DURATION = { kind = \"continuous\" }",
            "DURATION = { kind = \"finite\", final_period = 16 }",
        ),
    )
    .expect("shipped numeric material fixture")
}

/// Local names of the two counties the membership fixture's hyperedge joins.
pub(crate) const MEMBERSHIP_COUNTIES: [&str; 2] = ["county-26163", "county-26125"];
/// Qualified name of the membership field the fixture declares.
pub(crate) const MEMBERSHIP_QNAME: &str = "economic-sector/weight";

/// The shipped catalog with one membership field and one hyperedge whose two
/// members carry values (7 and -3), authored as a replacement graph
/// declarations artifact: the way content reaches a campaign, nothing else.
pub(crate) fn catalog_with_membership_values() -> MichiganMaterialCatalog {
    use crate::economic_catalog::SourceArtifactKind;
    let mut catalog = catalog();
    let shipped = catalog
        .captured_sources()
        .iter()
        .find(|source| source.kind() == SourceArtifactKind::GraphDeclarations)
        .map(|source| String::from_utf8(source.bytes().to_vec()))
        .expect("the shipped catalog captures its graph declarations")
        .expect("the shipped declarations are text");
    let authored = format!(
        "{shipped}\n  (deffield {MEMBERSHIP_QNAME} int extensive :member NodeType/TERRITORY)\n  \
         (hyperedge membership-proof HyperedgeType/ECONOMIC_SECTOR (members\n    \
         (member NodeType/TERRITORY {a} ({MEMBERSHIP_QNAME} 7))\n    \
         (member NodeType/TERRITORY {b} ({MEMBERSHIP_QNAME} -3))))\n",
        a = MEMBERSHIP_COUNTIES[0],
        b = MEMBERSHIP_COUNTIES[1],
    );
    catalog.replace_source(SourceArtifactKind::GraphDeclarations, authored.into_bytes());
    catalog
}

pub(crate) fn material_receipts(period: u64) -> MaterialTickReceipts {
    MaterialTickReceipts {
        agency_paid: vec![],
        household_time: vec![],
        household_lifecycle: vec![],
        resident_workforce_attrition: vec![],
        aid: vec![],
        collections: vec![],
        installation: vec![],
        installation_decisions: vec![],
        equipment_wear: vec![],
        investment: vec![],
        staffing_members: vec![],
        member_labor_use: vec![],
        public_budgets: vec![],
        taxes: vec![],
        distributions: vec![],
        company_basis: vec![],
        company_distributions: vec![],
        contributions: vec![],
        service_performance: vec![],
        household_services: vec![],
        service_markets: vec![],
        service_outputs: vec![],
        income: vec![],
        resolve_tick: period,
        household_demand: vec![],
        household_consumption: vec![],
        procurement: vec![],
        production_plans: vec![],
        prices: vec![],
        money_transfers: vec![],
        wage_accruals: vec![],
        labor_use: vec![],
        production: vec![],
        dispatches: vec![],
        losses: vec![],
        arrivals: vec![],
        deliveries: vec![],
        realizations: vec![],
        handling: vec![],
        local_fulfillments: vec![],
        local_transfers: vec![],
        maintenance: None,
    }
}

/// A disposable database for the live event continuity tests.
///
/// These tests run destructive `COPY` controls and raw inserts, so the fixture
/// refuses to exist outside the runner's disposable PostgreSQL: it checks the
/// runner's acknowledgement, its canary on the server, and its loopback `test`
/// role, then clones the runner's validated template under a name that starts
/// with `per337_event_continuity_`. The clone is dropped with the fixture.
#[cfg(test)]
pub(crate) struct EventContinuityDatabase {
    name: String,
    admin: postgres::Config,
    config: postgres::Config,
}

#[cfg(test)]
impl EventContinuityDatabase {
    const NAME_PREFIX: &'static str = "per337_event_continuity_";

    pub(crate) fn create(label: &str) -> Self {
        use postgres::{Config, NoTls};
        use std::str::FromStr;

        assert!(!label.is_empty() && label.bytes().all(|byte| byte.is_ascii_lowercase()));
        assert_eq!(
            std::env::var("BABYLON_POSTGRES_DISPOSABLE_ACK").as_deref(),
            Ok("I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES")
        );
        let canary = std::env::var("BABYLON_POSTGRES_DISPOSABLE_CANARY")
            .expect("runner supplies the disposable canary");
        assert_eq!(canary.len(), 32);
        let dsn =
            std::env::var("BABYLON_POSTGRES_TEST_DSN").expect("runner supplies the disposable DSN");
        let mut admin = Config::from_str(&dsn).expect("runner DSN parses");
        crate::postgres_catalog::validate_connection_target(&admin).expect("loopback target");
        assert_eq!(admin.get_user(), Some("test"));
        assert_eq!(admin.get_dbname(), Some("postgres"));
        let mut admin_client = admin.connect(NoTls).expect("canary connection");
        let actual: Option<String> = admin_client
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.disposable_runtime', true)",
                &[],
            )
            .expect("canary query")
            .try_get(0)
            .expect("canary decode");
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        let template = std::env::var("BABYLON_RUNTIME_TEMPLATE_DB")
            .expect("runner supplies the validated Rust-active template database");
        assert!(template.starts_with("per281_runtime_template_"));
        assert!(template
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_'));
        let name = format!("{}{label}_{}", Self::NAME_PREFIX, std::process::id());
        assert!(name.starts_with(Self::NAME_PREFIX));
        admin_client
            .batch_execute(&format!(
                "CREATE DATABASE \"{name}\" OWNER test TEMPLATE \"{template}\""
            ))
            .expect("event continuity clone creation");
        admin.dbname("postgres");
        let mut config = admin.clone();
        config.dbname(&name);
        let database = Self {
            name,
            admin,
            config,
        };
        crate::preflight_current_schema(&database.config)
            .expect("event continuity clone has the exact current catalog and role grants");
        database
    }

    pub(crate) fn config(&self) -> &postgres::Config {
        &self.config
    }
}

#[cfg(test)]
impl Drop for EventContinuityDatabase {
    fn drop(&mut self) {
        use postgres::NoTls;

        if !self.name.starts_with(Self::NAME_PREFIX) {
            return;
        }
        let sql = format!("DROP DATABASE IF EXISTS \"{}\" WITH (FORCE)", self.name);
        let dropped = self
            .admin
            .connect(NoTls)
            .and_then(|mut client| client.batch_execute(&sql));
        if let Err(error) = dropped {
            assert!(
                std::thread::panicking(),
                "event continuity database cleanup failed: {error}"
            );
        }
    }
}
