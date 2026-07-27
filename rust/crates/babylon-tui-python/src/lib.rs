//! PyO3 FFI shell: `babylon_tui._core.run(host, config_json) -> transcript JSON`.
//!
//! JSON strings only cross the seam; the single `host` handle is the one
//! Python object Rust ever holds, and every callback re-attaches to the
//! interpreter (`Python::attach`, pyo3 0.29's `with_gil`) on the event-loop
//! thread.

use babylon_tui::app::{run_interactive, App};
use babylon_tui::config::AppConfig;
use babylon_tui::host::Host;
use pyo3::prelude::*;
use ratatui::backend::TestBackend;
use ratatui::Terminal;

/// `Host` over the Python host object: each read is a GIL-held method call.
struct PyHost {
    obj: Py<PyAny>,
}

impl PyHost {
    /// Call a zero-arg host method returning a JSON string.
    ///
    /// A raising host PANICS (after printing the Python traceback): an
    /// error must never be indistinguishable from honest absence
    /// (Constitution III.11 — a dropped Postgres connection is not an
    /// empty world). The unwind crosses back through the FFI boundary as
    /// a Python `PanicException` — after `TerminalSession`'s Drop has
    /// restored the terminal — so the player sees the real failure.
    fn call0(&self, name: &str) -> String {
        Python::attach(|py| {
            match self
                .obj
                .call_method0(py, name)
                .and_then(|v| v.extract::<String>(py))
            {
                Ok(value) => value,
                Err(error) => {
                    error.print(py);
                    panic!("host method {name} raised — traceback above (III.11 loud failure)")
                }
            }
        })
    }

    /// Call a one-string-arg host method returning a JSON string; raises
    /// loudly exactly like [`Self::call0`].
    fn call1(&self, name: &str, arg: &str) -> String {
        Python::attach(|py| {
            match self
                .obj
                .call_method1(py, name, (arg,))
                .and_then(|v| v.extract::<String>(py))
            {
                Ok(value) => value,
                Err(error) => {
                    error.print(py);
                    panic!("host method {name} raised — traceback above (III.11 loud failure)")
                }
            }
        })
    }
}

impl Host for PyHost {
    fn lobby_catalog_json(&self) -> String {
        self.call0("lobby_catalog_json")
    }

    fn load_campaign(&self, campaign_id: &str) -> String {
        self.call1("load_campaign", campaign_id)
    }

    fn read_page_json(&self, subject: &str) -> String {
        self.call1("read_page_json", subject)
    }

    fn known_subjects_json(&self) -> String {
        self.call0("known_subjects_json")
    }

    fn backlinks_json(&self, subject: &str) -> String {
        self.call1("backlinks_json", subject)
    }

    fn subject_view_json(&self, subject: &str) -> String {
        self.call1("subject_view_json", subject)
    }

    fn watchlist_json(&self) -> String {
        self.call0("watchlist_json")
    }

    fn pacing_state_json(&self) -> String {
        self.call0("pacing_state_json")
    }

    fn advance_tick(&self) -> String {
        self.call0("advance_tick")
    }

    fn run_until_paused(&self) -> String {
        self.call0("run_until_paused")
    }

    fn acknowledge_pause(&self) -> String {
        self.call0("acknowledge_pause")
    }

    fn chronicle_rail_json(&self) -> String {
        self.call0("chronicle_rail_json")
    }

    fn verb_plate_view_json(&self) -> String {
        self.call0("verb_plate_view_json")
    }

    fn issue_verb(&self, args_json: &str) -> String {
        self.call1("issue_verb", args_json)
    }

    fn endgame_status_json(&self) -> String {
        self.call0("endgame_status_json")
    }

    fn pin_watchlist(&self, args_json: &str) -> String {
        self.call1("pin_watchlist", args_json)
    }

    fn nav_state_json(&self) -> String {
        self.call0("nav_state_json")
    }

    fn save_nav_state(&self, nav_json: &str) -> String {
        self.call1("save_nav_state", nav_json)
    }

    fn tutorial_state_json(&self, view_state_json: &str) -> String {
        self.call1("tutorial_state_json", view_state_json)
    }

    fn new_campaign(&self) -> String {
        self.call0("new_campaign")
    }
}

/// Run the client. Headless configs render the initial frame, replay the
/// config's script steps (each appending its frame), and return a JSON
/// transcript `{"frames": [...], "host_calls": [...]}`; the interactive
/// path owns the terminal until quit.
#[pyfunction]
fn run(py: Python<'_>, host: Py<PyAny>, config_json: &str) -> PyResult<String> {
    let cfg = AppConfig::from_json(config_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let py_host = PyHost { obj: host };
    let headless = cfg.headless;
    let headless_size = cfg.headless_size;
    let script = cfg.script.clone();
    let mut app = App::new(cfg, py_host);
    py.detach(|| {
        if headless {
            let (width, height) = headless_size;
            let mut t = Terminal::new(TestBackend::new(width, height))
                .map_err(|e| format!("test backend init: {e:?}"))?;
            let mut frames = Vec::new();
            app.render_frame(&mut t)
                .map_err(|e| format!("headless render: {e:?}"))?;
            frames.push(format!("{:?}", t.backend().buffer()));
            for step in &script {
                if app.apply_step(step) {
                    break; // quit — the last recorded frame stands
                }
                app.render_frame(&mut t)
                    .map_err(|e| format!("headless step render: {e:?}"))?;
                frames.push(format!("{:?}", t.backend().buffer()));
            }
            let calls = app.host_calls();
            Ok(serde_json::json!({"frames": frames, "host_calls": calls}).to_string())
        } else {
            run_interactive(app)
                .map(|calls| serde_json::json!({"frames": [], "host_calls": calls}).to_string())
                .map_err(|e| e.to_string())
        }
    })
    .map_err(pyo3::exceptions::PyRuntimeError::new_err)
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run, m)?)
}
