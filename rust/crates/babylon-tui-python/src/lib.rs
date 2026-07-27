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

impl Host for PyHost {
    fn lobby_catalog_json(&self) -> String {
        Python::attach(|py| {
            self.obj
                .call_method0(py, "lobby_catalog_json")
                .and_then(|v| v.extract::<String>(py))
                .unwrap_or_else(|_| "[]".into()) // honest absence: empty catalog
        })
    }
}

/// Run the client. Headless configs render one frame to a test backend and
/// return a JSON transcript `{"frames": [...], "host_calls": [...]}`; the
/// interactive path owns the terminal until `q`/`Esc`.
#[pyfunction]
fn run(py: Python<'_>, host: Py<PyAny>, config_json: &str) -> PyResult<String> {
    let cfg = AppConfig::from_json(config_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let py_host = PyHost { obj: host };
    let headless = cfg.headless;
    let app = App::new(cfg, py_host);
    py.detach(|| {
        if headless {
            let mut t = Terminal::new(TestBackend::new(80, 24))
                .map_err(|e| format!("test backend init: {e:?}"))?;
            app.render_frame(&mut t)
                .map_err(|e| format!("headless render: {e:?}"))?;
            let frame = format!("{:?}", t.backend().buffer());
            let calls = app.host_calls();
            Ok(serde_json::json!({"frames": [frame], "host_calls": calls}).to_string())
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
