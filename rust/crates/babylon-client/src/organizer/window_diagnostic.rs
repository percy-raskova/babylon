//! Bounded observations for one owned resize diagnostic; no window mutation.

use std::time::Instant;

use bevy::prelude::*;
use bevy::window::{MonitorSelection, WindowMode, WindowResized};
use bevy::winit::WINIT_WINDOWS;
use serde_json::{json, Value};

use super::Action;

pub(super) struct WindowDiagnostic {
    sequence: u64,
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
    ) -> Self {
        let mut diagnostic = Self {
            sequence,
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
        self.emit(phase, json!({
            "target_physical": self.target.to_array(), "target_mode": format!("{:?}", self.mode),
            "prior_observed": extent(self.prior), "observed": extent(observed),
            "component": component(current),
            "backend": backend(current.map(|(entity, _)| entity)),
            "resize_armed": armed, "predicates": predicates,
            "outcome": outcome, "last_event": self.last_event,
        }));
    }

    fn emit(&mut self, phase: &str, detail: Value) {
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
    current.map(|(entity, window)| json!({
        "entity": entity.to_bits(), "physical": [window.physical_width(), window.physical_height()],
        "logical": [window.width(), window.height()], "scale": window.scale_factor(),
        "mode": format!("{:?}", window.mode),
    }))
}

fn backend(entity: Option<Entity>) -> Value {
    let Some(entity) = entity else {
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
        json!({
            "available": true, "entity": entity.to_bits(),
            "physical": [physical.width, physical.height], "scale": window.scale_factor(),
            "fullscreen": format!("{:?}", window.fullscreen()), "maximized": window.is_maximized(),
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
            let mut diagnostic = WindowDiagnostic::new(7, Action::Resize1366x768, None, None);
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
