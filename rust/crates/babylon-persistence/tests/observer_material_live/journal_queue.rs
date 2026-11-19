//! Bounded recovery, a live commit wakeup, and graceful shutdown on the actual worker binary.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::DurableMaterialRuntime;
use postgres::{Client, Config};
use serde_json::Value;
use std::io::Write as _;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

fn command(owner: &Config, observer: &Config) -> Command {
    let mut command = Command::new(env!("CARGO_BIN_EXE_babylon-economic-projections"));
    command
        .env_clear()
        .env(
            "BABYLON_RUNTIME_DSN",
            super::runtime_process::child_dsn(owner),
        )
        .env(
            "BABYLON_OBSERVER_DSN",
            super::runtime_process::child_dsn(observer),
        );
    command
}

struct Worker(Child);
impl Drop for Worker {
    fn drop(&mut self) {
        if !matches!(self.0.try_wait(), Ok(Some(_))) {
            let _ = self.0.kill();
            let _ = self.0.wait();
        }
    }
}
impl Worker {
    fn wait_for_period(&mut self, database: &mut Client, campaign: CampaignId, period: i64) {
        let start = Instant::now();
        loop {
            let present: bool = database.query_one("SELECT EXISTS (SELECT 1 FROM public.v_observer_money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=$2)", &[campaign.as_uuid(), &period]).expect("read published coverage").get(0);
            if present {
                return;
            }
            assert!(
                self.0.try_wait().expect("inspect worker").is_none(),
                "worker exited before publication"
            );
            assert!(
                start.elapsed() < Duration::from_secs(120),
                "period {period} not published"
            );
            thread::sleep(Duration::from_millis(100));
        }
    }

    fn finish(mut self) {
        self.0
            .stdin
            .take()
            .expect("lifetime pipe")
            .write_all(b"Q")
            .expect("request final sweep");
        let start = Instant::now();
        loop {
            if let Some(status) = self.0.try_wait().expect("inspect worker") {
                assert!(
                    status.success(),
                    "worker refused during final sweep: {status}"
                );
                return;
            }
            assert!(
                start.elapsed() < Duration::from_secs(30),
                "worker failed to drain"
            );
            thread::sleep(Duration::from_millis(100));
        }
    }
}

pub(super) fn recover_and_follow(
    runtime: &mut DurableMaterialRuntime,
    database: &mut Client,
    writer: &Config,
    observer: &Config,
    campaign: CampaignId,
) {
    let deleted = database.execute(
        "DELETE FROM babylon_state.money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick BETWEEN 2 AND 10",
        &[campaign.as_uuid()],
    ).expect("remove only derived test coverage");
    assert_eq!(
        deleted, 9,
        "latest period fourteen remains published above nine interior gaps"
    );
    let scoped = command(writer, observer)
        .args(["sweep", "--campaign", &campaign.as_uuid().to_string()])
        .output()
        .expect("run scoped worker batch");
    assert!(
        scoped.status.success(),
        "scoped projection worker failed: {}",
        String::from_utf8_lossy(&scoped.stderr)
    );
    let report: Value = serde_json::from_slice(&scoped.stdout).expect("scoped result");
    assert_eq!(
        report["covered"], 8,
        "bounded sweep leaves the final hole for restart"
    );
    assert_eq!(report["campaign"], campaign.as_uuid().to_string());
    let missing: bool = database.query_one("SELECT NOT EXISTS (SELECT 1 FROM public.v_observer_money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=10)", &[campaign.as_uuid()]).expect("inspect batch bound").get(0);
    assert!(missing);
    let mut worker = Worker(
        command(writer, observer)
            .args(["watch-database", "--session-stdin"])
            .stdin(Stdio::piped())
            .spawn()
            .expect("launch independent watcher"),
    );
    worker.wait_for_period(database, campaign, 10);
    check_publication_wakeup(&mut worker, database, runtime, observer, campaign);
    worker.finish();
    let total: i64 = database
        .query_one(
            "SELECT count(*) FROM public.v_observer_money_journal_period_v1 WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .expect("covered history")
        .get(0);
    assert_eq!(
        total, 15,
        "every committed period has identity-bound coverage"
    );
}

fn check_publication_wakeup(
    worker: &mut Worker,
    database: &mut Client,
    runtime: &mut DurableMaterialRuntime,
    config: &Config,
    campaign: CampaignId,
) {
    use babylon_persistence::money_journal::PeriodWindow;
    use babylon_persistence::observer_reader::{ObserverEconomyReader, ObserverVisibility};
    use postgres::fallible_iterator::FallibleIterator as _;

    let reader = ObserverEconomyReader::connect(config, ObserverVisibility::FullObserver)
        .expect("confined observer");
    let window = PeriodWindow {
        first: 14,
        last: 15,
    };
    let mut wait = reader
        .watch_journal_periods(campaign, window)
        .expect("subscribe");
    assert!(!wait.wait(Duration::ZERO).expect("period 15 is missing"));
    database
        .batch_execute("NOTIFY babylon_economic_publication_v1")
        .expect("send an untrusted empty hint");
    assert!(!wait
        .wait(Duration::from_secs(1))
        .expect("reconcile hinted coverage"));
    database
        .batch_execute("LISTEN babylon_economic_publication_v1")
        .expect("register for writer commit");
    super::advance_material_period(runtime);
    worker.wait_for_period(database, campaign, 15);
    let notification = database
        .notifications()
        .timeout_iter(Duration::from_secs(2))
        .next()
        .expect("read writer notification")
        .expect("changed journal emits a committed hint");
    assert_eq!(notification.channel(), "babylon_economic_publication_v1");
    assert_eq!(notification.payload(), "");
    assert!(wait
        .wait(Duration::from_secs(1))
        .expect("marker and both periods are covered"));
    let mut after = reader
        .watch_journal_periods(campaign, window)
        .expect("late subscriber");
    assert!(after
        .wait(Duration::ZERO)
        .expect("a preexisting marker is visible immediately"));
}
