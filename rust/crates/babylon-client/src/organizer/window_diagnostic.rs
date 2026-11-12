//! Bounded observations for one owned resize diagnostic; no window mutation.

use std::time::Instant;

use bevy::prelude::*;
use bevy::window::{MonitorSelection, WindowMode, WindowResized};
use bevy::winit::WINIT_WINDOWS;
use serde::Serialize;
use serde_json::{json, Value};

use super::Action;

/// Fixed boundaries only; a missing boundary remains absent rather than inferred.
#[derive(Default, Serialize)]
struct RetainedWindowContext {
    before_request: Option<Value>,
    after_request: Option<Value>,
    first_after_last: Option<Value>,
    terminal: Option<Value>,
}

#[derive(Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
pub(super) enum ResizeBranch {
    PrimaryUnavailable,
    VerifiedWindowedNoOp,
    ObservedFullscreenNoOp,
    ExtentUnobserved,
    ComponentRequest,
}

pub(super) enum DetailMode {
    Compact,
    Detailed,
}

pub(super) struct WindowDiagnostic {
    sequence: u64,
    action: Action,
    detailed: bool,
    branch: Option<ResizeBranch>,
    context: RetainedWindowContext,
    target: UVec2,
    mode: WindowMode,
    started: Instant,
    prior: Option<(Entity, UVec2)>,
    pub(super) events: u64,
    pub(super) accepted_events: u64,
    pub(super) checks: u64,
    pub(super) post_last: u64,
    pub(super) records: u64,
    last_event: Option<Value>,
}

impl WindowDiagnostic {
    pub(super) fn new(
        sequence: u64,
        action: Action,
        prior: Option<(Entity, UVec2)>,
        window: Option<(Entity, &Window)>,
        detail_mode: DetailMode,
    ) -> Self {
        let mut diagnostic = Self {
            sequence,
            action,
            detailed: matches!(detail_mode, DetailMode::Detailed),
            branch: None,
            context: RetainedWindowContext::default(),
            target: action.extent().expect("diagnostic only for resize"),
            mode: if action == Action::Resize1366x768 {
                WindowMode::Windowed
            } else {
                WindowMode::BorderlessFullscreen(MonitorSelection::Current)
            },
            started: Instant::now(),
            prior,
            events: 0,
            accepted_events: 0,
            checks: 0,
            post_last: 0,
            records: 0,
            last_event: None,
        };
        diagnostic.snapshot("request", window, prior, false, None);
        diagnostic
    }

    pub(super) fn detailed_enabled(&self) -> bool {
        self.detailed
    }

    pub(super) fn request_branch(&mut self, branch: ResizeBranch) {
        self.branch = Some(branch);
    }

    pub(super) fn event(
        &mut self,
        event: &WindowResized,
        current: Option<(Entity, &Window)>,
        accepted: bool,
    ) {
        self.events = self.events.saturating_add(1);
        self.accepted_events = self.accepted_events.saturating_add(u64::from(accepted));
        self.last_event = Some(json!({
            "entity": event.window.to_bits(), "logical": [event.width, event.height],
            "accepted": accepted,
            "component": component(current),
            "resulting_observation": if accepted { current.map(|(entity, window)| json!({
                "entity": entity.to_bits(), "physical": [window.physical_width(), window.physical_height()]
            })) } else { None },
        }));
        if self.events <= 16 {
            self.emit("event", json!({"event": self.last_event}));
        }
    }

    pub(super) fn snapshot(
        &mut self,
        phase: &str,
        current: Option<(Entity, &Window)>,
        observed: Option<(Entity, UVec2)>,
        armed: bool,
        outcome: Option<&str>,
    ) {
        let predicates = current.map(|(entity, window)| json!({
            "mode_matches": window.mode == self.mode,
            "observed_target": observed == Some((entity, self.target)),
            "physical_target": UVec2::new(window.physical_width(), window.physical_height()) == self.target,
        }));
        let detail = json!({
            "target_physical": self.target.to_array(), "target_mode": format!("{:?}", self.mode),
            "prior_observed": extent(self.prior), "observed": extent(observed),
            "component": component(current),
            "backend": backend(current, self.target),
            "resize_armed": armed, "predicates": predicates,
            "outcome": outcome, "last_event": self.last_event,
            "events": self.events, "accepted_events": self.accepted_events,
            "rejected_events": self.events.saturating_sub(self.accepted_events),
            "elapsed_us": self.started.elapsed().as_micros(),
        });
        match phase {
            "request" => self.context.before_request = Some(detail.clone()),
            "requested" => self.context.after_request = Some(detail.clone()),
            "post_last" if self.context.first_after_last.is_none() => {
                self.context.first_after_last = Some(detail.clone());
            }
            "final" => self.context.terminal = Some(detail.clone()),
            _ => {}
        }
        // Keep the opted-in stream's private phase contract unchanged.
        if phase != "requested" {
            self.emit(phase, detail);
        }
        if phase == "final" {
            bevy::log::info!(target: "babylon_client::window_context", "window_context {}", json!({
                "version": 1, "sequence": self.sequence, "action": match self.action {
                    Action::Resize1366x768 => "resize1366x768",
                    Action::Resize1920x1080 => "resize1920x1080",
                    _ => unreachable!("diagnostic only for resize"),
                },
                "request_branch": self.branch, "snapshots": self.context,
            }));
        }
    }

    fn emit(&mut self, phase: &str, detail: Value) {
        if !self.detailed {
            return;
        }
        // Request + first completion + 16 events + 8 post-Last + guaranteed final = 27.
        self.records = self.records.saturating_add(1);
        bevy::log::info!(target: "babylon_window_diagnostic", "window_diagnostic {}", json!({
            "sequence": self.sequence, "phase": phase, "elapsed_us": self.started.elapsed().as_micros(),
            "records": self.records, "events": self.events, "accepted_events": self.accepted_events,
            "rejected_events": self.events.saturating_sub(self.accepted_events),
            "checks": self.checks, "post_last": self.post_last, "detail": detail,
        }));
    }
}

fn extent(observed: Option<(Entity, UVec2)>) -> Option<Value> {
    observed.map(
        |(entity, physical)| json!({"entity": entity.to_bits(), "physical": physical.to_array()}),
    )
}

fn component(current: Option<(Entity, &Window)>) -> Option<Value> {
    current.map(|(entity, window)| {
        let mut internal = window.internal;
        json!({
        "entity": entity.to_bits(), "physical": [window.physical_width(), window.physical_height()],
        "logical": [window.width(), window.height()], "scale": window.scale_factor(),
        "base_scale": window.resolution.base_scale_factor(),
        "scale_override": window.resolution.scale_factor_override(),
        "pending_maximize": internal.take_maximize_request(),
        "position": format!("{:?}", window.position),
        "mode": format!("{:?}", window.mode),
    })})
}

#[expect(
    clippy::cast_possible_truncation,
    reason = "Bevy stores the Winit scale as f32"
)]
fn backend(current: Option<(Entity, &Window)>, target: UVec2) -> Value {
    let Some((entity, component)) = current else {
        return json!({"available": false, "reason": "no_primary_entity"});
    };
    WINIT_WINDOWS.with(|windows| {
        let Ok(windows) = windows.try_borrow() else {
            return json!({"available": false, "reason": "backend_borrowed"});
        };
        let Some(window) = windows.get_window(entity) else {
            return json!({"available": false, "reason": "entity_has_no_backend", "entity": entity.to_bits()});
        };
        let physical = window.inner_size();
        let scale = window.scale_factor();
        let mut internal = component.internal;
        let fullscreen = window.fullscreen();
        let maximized = window.is_maximized();
        let outer = window.outer_size();
        json!({
            "available": true, "entity": entity.to_bits(), "native_id": format!("{:?}", window.id()),
            "physical": [physical.width, physical.height], "scale": scale,
            "fullscreen": format!("{fullscreen:?}"), "maximized": maximized,
            "inner_position": window.inner_position().ok().map(|position| [position.x, position.y]),
            "outer_position": window.outer_position().ok().map(|position| [position.x, position.y]),
            "outer_physical": [outer.width, outer.height],
            "predicates": {
                "physical_target": ([physical.width, physical.height] == target.to_array()),
                "windowed": fullscreen.is_none(), "unmaximized": !maximized,
                "valid_scale": scale.is_finite() && scale > 0.0,
                "base_scale_matches": (scale as f32).to_bits() == component.resolution.base_scale_factor().to_bits(),
                "no_pending_maximize": internal.take_maximize_request().is_none(),
            },
        })
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::logging;
    use crate::logging::RotatingSink;
    use bevy::log::tracing_subscriber;
    use bevy::log::BoxedLayer;
    use std::fs;
    use tracing_subscriber::fmt::Layer;
    use tracing_subscriber::EnvFilter;

    #[test]
    fn ordinary_log_retains_fixed_context_for_success_and_refusal() {
        use tracing_subscriber::layer::SubscriberExt as _;
        let directory =
            std::env::temp_dir().join(format!("babylon-window-context-{}", std::process::id()));
        fs::create_dir(&directory).expect("fresh context log fixture");
        let sink = RotatingSink::open(&directory, 100_000, 1).expect("normal file sink");
        let file_layer: Option<BoxedLayer> = Some(Box::new(
            Layer::default().with_ansi(false).with_writer(sink),
        ));
        let subscriber = tracing_subscriber::registry()
            .with(file_layer)
            .with(EnvFilter::new("warn,session=debug,babylon_client=debug"));
        bevy::log::tracing::subscriber::with_default(subscriber, || {
            let entity = Entity::from_bits(1);
            let mut window = Window::default();
            window.resolution.set_scale_factor(2.0);
            window.resolution.set_scale_factor_override(Some(1.25));
            for outcome in [
                "applied",
                "primary_window_resize_timeout",
                "primary_window_unavailable",
            ] {
                window.set_maximized(true);
                let mut diagnostic = WindowDiagnostic::new(
                    121,
                    Action::Resize1366x768,
                    None,
                    Some((entity, &window)),
                    DetailMode::Compact,
                );
                diagnostic.request_branch(ResizeBranch::ComponentRequest);
                window.set_maximized(false);
                diagnostic.snapshot("requested", Some((entity, &window)), None, false, None);
                if outcome != "primary_window_unavailable" {
                    diagnostic.snapshot("post_last", Some((entity, &window)), None, true, None);
                    diagnostic.snapshot("post_last", None, None, true, None);
                }
                let event = WindowResized {
                    window: entity,
                    width: window.width(),
                    height: window.height(),
                };
                diagnostic.event(&event, Some((entity, &window)), false);
                diagnostic.event(&event, Some((entity, &window)), true);
                diagnostic.snapshot("final", Some((entity, &window)), None, true, Some(outcome));
            }
            assert_eq!(
                window.internal.take_maximize_request(),
                Some(false),
                "observation must not consume the native request"
            );
        });
        let contents =
            fs::read_to_string(directory.join("babylon-client.log")).expect("normal log bytes");
        let records: Vec<Value> = contents
            .lines()
            .filter_map(|line| line.split_once("window_context "))
            .map(|(_, json)| serde_json::from_str(json).expect("context JSON"))
            .collect();
        assert_eq!(
            records.len(),
            3,
            "ordinary success, timeout and immediate refusal retain context"
        );
        for (record, outcome) in records.iter().zip([
            "applied",
            "primary_window_resize_timeout",
            "primary_window_unavailable",
        ]) {
            assert_retained_context(record, outcome);
        }
        assert!(
            !contents.contains("window_diagnostic "),
            "detailed records remain opt-in"
        );
        fs::remove_file(directory.join("babylon-client.log")).expect("remove fixture log");
        fs::remove_dir(directory).expect("remove empty fixture directory");
    }

    fn assert_retained_context(record: &Value, outcome: &str) {
        assert_eq!(record["version"], 1, "explicit private compact format");
        assert_eq!(record["sequence"], 121, "exact request identity");
        assert_eq!(record["action"], "resize1366x768", "exact action");
        assert_eq!(
            record["snapshots"]["terminal"]["outcome"], outcome,
            "actual terminal result"
        );
        let before = &record["snapshots"]["before_request"]["component"];
        assert_eq!(before["base_scale"], 2.0, "native-derived component scale");
        assert_eq!(before["scale_override"], 1.25, "authored override");
        assert_eq!(before["pending_maximize"], true, "copied pending flag");
        assert_eq!(
            record["snapshots"]["after_request"]["component"]["pending_maximize"], false,
            "copied boundaries survive later mutations"
        );
        assert_eq!(
            record["snapshots"]["terminal"]["events"], 2,
            "bounded event total"
        );
        assert_eq!(
            record["snapshots"]["terminal"]["accepted_events"], 1,
            "accepted event count"
        );
        assert_eq!(
            record["snapshots"]["terminal"]["rejected_events"], 1,
            "rejected event count"
        );
        assert_eq!(
            record["snapshots"]["terminal"]["last_event"]["accepted"], true,
            "last actual event"
        );
        if outcome == "primary_window_unavailable" {
            assert!(
                record["snapshots"]["first_after_last"].is_null(),
                "unreached boundary stays absent"
            );
        } else {
            assert_eq!(
                record["snapshots"]["first_after_last"]["component"]["entity"], 1,
                "first boundary is retained once"
            );
        }
    }

    #[test]
    fn dedicated_target_reaches_file_and_stderr_with_client_logging_disabled() {
        use tracing_subscriber::layer::SubscriberExt as _;
        let directory =
            std::env::temp_dir().join(format!("babylon-window-diagnostic-{}", std::process::id()));
        fs::create_dir(&directory).expect("fresh task-owned log test directory");
        let sink = RotatingSink::open(&directory, 100_000, 1).expect("real rotating file sink");
        let file_layer: Option<BoxedLayer> = Some(Box::new(
            Layer::default().with_ansi(false).with_writer(sink),
        ));
        let subscriber = tracing_subscriber::registry()
            .with(file_layer)
            .with(EnvFilter::new(
                "off,babylon_client=off,babylon_window_diagnostic=info",
            ))
            .with(logging::stderr_fmt_layer(&mut App::new()));
        bevy::log::tracing::subscriber::with_default(subscriber, || {
            let mut diagnostic =
                WindowDiagnostic::new(7, Action::Resize1366x768, None, None, DetailMode::Detailed);
            diagnostic.snapshot(
                "final",
                None,
                None,
                false,
                Some("primary_window_unavailable"),
            );
        });
        let contents =
            fs::read_to_string(directory.join("babylon-client.log")).expect("actual sink bytes");
        let records: Vec<Value> = contents
            .lines()
            .map(|line| {
                let (_, encoded) = line
                    .split_once("window_diagnostic ")
                    .expect("dedicated INFO event");
                serde_json::from_str(encoded).expect("bounded JSON observation")
            })
            .collect();
        assert_eq!(
            records.len(),
            2,
            "request and guaranteed final both reach the sink"
        );
        assert_eq!(records[0]["phase"], "request", "first request observation");
        assert_eq!(records[1]["phase"], "final", "final outcome observation");
        assert_eq!(
            records[1]["detail"]["backend"]["available"], false,
            "missing backend stays explicit"
        );
        fs::remove_file(directory.join("babylon-client.log")).expect("remove exact log fixture");
        fs::remove_dir(directory).expect("remove empty task-owned fixture");
    }
}
