use super::{ScriptCommand, ScriptError};
use crate::small_world::frame_time;
use crate::small_world::frame_time::{FrameTime, SAMPLE_WINDOW, SETTLE};
use crate::small_world::script;
use hypergraph_rs_bevy::FrameWindows;
use std::time::Duration;

/// The proof script of Task 9, as it is run on the display.
const PROOF: &str = r#"{"step":1}
{"strike":{"shock":"harvest_fails","places":"a","lasts":"ten_periods"}}
{"step":10}
{"capture":"after-ten"}
{"report":"after-ten"}
{"wait_frames":600}
{"report":"frame-time"}
"quit"
"#;

#[test]
fn the_script_reads_one_command_a_line() {
    let commands = script::parse_script(PROOF);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(1),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "a".into(),
                lasts: "ten_periods".into(),
            },
            ScriptCommand::Step(10),
            ScriptCommand::Capture("after-ten".into()),
            ScriptCommand::Report("after-ten".into()),
            ScriptCommand::WaitFrames(600),
            ScriptCommand::Report("frame-time".into()),
            ScriptCommand::Quit,
        ])
    );
}

#[test]
fn an_unknown_command_refuses_the_whole_script() {
    let text = "{\"step\":1}\n{\"step\":2}\n{\"jump\":1}\n{\"step\":3}\n";
    assert!(matches!(
        script::parse_script(text),
        Err(ScriptError::Line { line: 3, .. })
    ));
    for bad in [
        r#"{"strike":{"shock":"flood","places":"a","lasts":"until_lifted"}}"#,
        r#"{"lift":{"shock":"harvest_fails","place":"both"}}"#,
        r#"{"particles":"crowd"}"#,
        r#"{"capture":"../escape"}"#,
        r#"{"report":""}"#,
    ] {
        assert!(
            matches!(
                script::parse_script(bad),
                Err(ScriptError::Line { line: 1, .. })
            ),
            "{bad} must be refused"
        );
    }
}

#[test]
fn the_scene_times_its_frames_as_the_client_does() {
    let mut windows = FrameWindows::new(SAMPLE_WINDOW, SETTLE);
    let tick = Duration::from_millis(10);
    let mut settled = Duration::ZERO;
    while settled < SETTLE {
        assert_eq!(windows.push(tick), None);
        settled += tick;
    }
    let mut stats = None;
    for _ in 0..SAMPLE_WINDOW {
        stats = windows.push(tick);
    }
    let figures = frame_time::frame_time(&stats.expect("a full window"));
    assert_eq!(figures.window, 300);
    assert!((figures.median_ms - 10.0).abs() < 1e-9);
    assert!((figures.p95_ms - 10.0).abs() < 1e-9);
    assert_eq!(
        figures,
        FrameTime {
            median_ms: figures.median_ms,
            p95_ms: figures.p95_ms,
            window: 300
        }
    );
}
