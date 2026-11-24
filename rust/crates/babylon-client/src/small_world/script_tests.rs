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

#[test]
fn the_script_names_the_six_rules() {
    for name in [
        "hiring_within_means",
        "seeking_in_place",
        "stop_without_pay",
        "resting_price",
        "owner_restart",
        "goods_step_down",
    ] {
        let line = format!("{{\"rule\":\"{name}\"}}");
        assert_eq!(
            script::parse_script(&line),
            Ok(vec![ScriptCommand::Rule(name.into())])
        );
    }
    assert!(matches!(
        script::parse_script("{\"step\":1}\n{\"rule\":\"everything\"}"),
        Err(ScriptError::Line { line: 2, .. })
    ));
}

/// The proof script of Task 2c, run by the lead on the display.
const PROOF_2C: &str = r#"{"step":2}
{"report":"before-rules"}
{"capture":"before-rules"}
{"rule":"stop_without_pay"}
"#;

#[test]
fn the_proof_script_of_task_2c_parses() {
    let commands = script::parse_script(PROOF_2C);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(2),
            ScriptCommand::Report("before-rules".into()),
            ScriptCommand::Capture("before-rules".into()),
            ScriptCommand::Rule("stop_without_pay".into()),
        ])
    );
}

/// The proof script of Task 3c, run by the lead on the display.
const PROOF_3C: &str = r#"{"step":20}
{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}
{"step":10}
{"rule":"seeking_in_place"}
{"step":20}
{"capture":"seekers-on"}
{"particles":"people"}
{"capture":"seekers-people"}
{"report":"seekers-on"}
"#;

#[test]
fn the_proof_script_of_task_3c_parses() {
    let commands = script::parse_script(PROOF_3C);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(20),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "a".into(),
                lasts: "until_lifted".into(),
            },
            ScriptCommand::Step(10),
            ScriptCommand::Rule("seeking_in_place".into()),
            ScriptCommand::Step(20),
            ScriptCommand::Capture("seekers-on".into()),
            ScriptCommand::Particles("people".into()),
            ScriptCommand::Capture("seekers-people".into()),
            ScriptCommand::Report("seekers-on".into()),
        ])
    );
}

#[test]
fn the_script_names_tabs_picks_and_beats() {
    assert_eq!(
        script::parse_script(
            "{\"lower\":\"rules\"}\n{\"pick\":\"household:15\"}\n{\"pick\":\"workplace:a:farm\"}\n{\"pick\":\"treasury\"}\n{\"pick\":\"none\"}\n{\"beat_millis\":60}"
        ),
        Ok(vec![
            ScriptCommand::Lower("rules".into()),
            ScriptCommand::Pick("household:15".into()),
            ScriptCommand::Pick("workplace:a:farm".into()),
            ScriptCommand::Pick("treasury".into()),
            ScriptCommand::Pick("none".into()),
            ScriptCommand::BeatMillis(60),
        ])
    );
    for (bad, word) in [
        (r#"{"lower":"table"}"#, "table"),
        (r#"{"pick":"household:19"}"#, "household:19"),
        (r#"{"pick":"workplace:c:farm"}"#, "workplace:c:farm"),
        (r#"{"beat_millis":5}"#, "not 5"),
        (r#"{"beat_millis":5000}"#, "not 5000"),
    ] {
        let refused = script::parse_script(&format!("{{\"step\":1}}\n{bad}"));
        assert!(
            matches!(&refused, Err(ScriptError::Line { line: 2, reason }) if reason.contains(word)),
            "{bad} must be refused at its line, in words that name {word}: {refused:?}"
        );
    }
}

/// The proof script of Task 3d, run by the lead on the display.
const PROOF_3D: &str = r#"{"beat_millis":60}
{"step":20}
{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}
{"step":10}
{"rule":"seeking_in_place"}
{"step":20}
{"wait_frames":30}
{"capture":"slump-groups"}
{"pick":"household:15"}
{"wait_frames":30}
{"capture":"slump-clinic-workers"}
{"pick":"workplace:a:farm"}
{"wait_frames":30}
{"capture":"slump-farm"}
{"particles":"people"}
{"wait_frames":60}
{"capture":"slump-people"}
{"report":"slump"}
"quit"
"#;

#[test]
fn the_proof_script_of_task_3d_parses() {
    let commands = script::parse_script(PROOF_3D);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::BeatMillis(60),
            ScriptCommand::Step(20),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "a".into(),
                lasts: "until_lifted".into(),
            },
            ScriptCommand::Step(10),
            ScriptCommand::Rule("seeking_in_place".into()),
            ScriptCommand::Step(20),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("slump-groups".into()),
            ScriptCommand::Pick("household:15".into()),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("slump-clinic-workers".into()),
            ScriptCommand::Pick("workplace:a:farm".into()),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("slump-farm".into()),
            ScriptCommand::Particles("people".into()),
            ScriptCommand::WaitFrames(60),
            ScriptCommand::Capture("slump-people".into()),
            ScriptCommand::Report("slump".into()),
            ScriptCommand::Quit,
        ])
    );
}

/// The proof script of Task 4c, run by the lead on the display.
const PROOF_4C: &str = r#"{"step":20}
{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}
{"step":10}
{"rule":"seeking_in_place"}
{"step":5}
{"rule":"hiring_within_means"}
{"step":20}
{"capture":"bound-on"}
{"particles":"people"}
{"capture":"bound-people"}
{"report":"bound-on"}
"#;

#[test]
fn the_proof_script_of_task_4c_parses() {
    let commands = script::parse_script(PROOF_4C);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(20),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "a".into(),
                lasts: "until_lifted".into(),
            },
            ScriptCommand::Step(10),
            ScriptCommand::Rule("seeking_in_place".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("hiring_within_means".into()),
            ScriptCommand::Step(20),
            ScriptCommand::Capture("bound-on".into()),
            ScriptCommand::Particles("people".into()),
            ScriptCommand::Capture("bound-people".into()),
            ScriptCommand::Report("bound-on".into()),
        ])
    );
}

/// The proof script of Task 5c, run by the lead on the display.
const PROOF_5C: &str = r#"{"step":20}
{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}
{"step":10}
{"rule":"seeking_in_place"}
{"step":5}
{"rule":"hiring_within_means"}
{"step":5}
{"rule":"stop_without_pay"}
{"step":20}
{"capture":"stop-on"}
{"particles":"people"}
{"capture":"stop-people"}
{"report":"stop-on"}
"#;

#[test]
fn the_proof_script_of_task_5c_parses() {
    let commands = script::parse_script(PROOF_5C);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(20),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "a".into(),
                lasts: "until_lifted".into(),
            },
            ScriptCommand::Step(10),
            ScriptCommand::Rule("seeking_in_place".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("hiring_within_means".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("stop_without_pay".into()),
            ScriptCommand::Step(20),
            ScriptCommand::Capture("stop-on".into()),
            ScriptCommand::Particles("people".into()),
            ScriptCommand::Capture("stop-people".into()),
            ScriptCommand::Report("stop-on".into()),
        ])
    );
}

/// The proof script of Task 6c, run by the lead on the display.
const PROOF_6C: &str = r#"{"step":20}
{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}
{"step":10}
{"rule":"seeking_in_place"}
{"step":5}
{"rule":"hiring_within_means"}
{"step":5}
{"rule":"stop_without_pay"}
{"step":5}
{"rule":"resting_price"}
{"step":20}
{"capture":"rest-on"}
{"particles":"people"}
{"capture":"rest-people"}
{"report":"rest-on"}
"#;

#[test]
fn the_proof_script_of_task_6c_parses() {
    let commands = script::parse_script(PROOF_6C);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(20),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "a".into(),
                lasts: "until_lifted".into(),
            },
            ScriptCommand::Step(10),
            ScriptCommand::Rule("seeking_in_place".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("hiring_within_means".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("stop_without_pay".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("resting_price".into()),
            ScriptCommand::Step(20),
            ScriptCommand::Capture("rest-on".into()),
            ScriptCommand::Particles("people".into()),
            ScriptCommand::Capture("rest-people".into()),
            ScriptCommand::Report("rest-on".into()),
        ])
    );
}

/// The proof script of Task 7c, run by the lead on the display.
const PROOF_7C: &str = r#"{"step":20}
{"strike":{"shock":"harvest_fails","places":"a","lasts":"until_lifted"}}
{"step":10}
{"rule":"seeking_in_place"}
{"step":5}
{"rule":"hiring_within_means"}
{"step":5}
{"rule":"stop_without_pay"}
{"step":5}
{"rule":"resting_price"}
{"step":5}
{"rule":"owner_restart"}
{"step":20}
{"capture":"restart-on"}
{"particles":"people"}
{"capture":"restart-people"}
{"report":"restart-on"}
"#;

#[test]
fn the_proof_script_of_task_7c_parses() {
    let commands = script::parse_script(PROOF_7C);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(20),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "a".into(),
                lasts: "until_lifted".into(),
            },
            ScriptCommand::Step(10),
            ScriptCommand::Rule("seeking_in_place".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("hiring_within_means".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("stop_without_pay".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("resting_price".into()),
            ScriptCommand::Step(5),
            ScriptCommand::Rule("owner_restart".into()),
            ScriptCommand::Step(20),
            ScriptCommand::Capture("restart-on".into()),
            ScriptCommand::Particles("people".into()),
            ScriptCommand::Capture("restart-people".into()),
            ScriptCommand::Report("restart-on".into()),
        ])
    );
}

/// The proof script of Task 5 of stored hours, run by the lead on the display.
const PROOF_SH5: &str = r#"{"step":1}
{"capture":"hours-1"}
{"step":1}
{"capture":"hours-2"}
{"step":2}
{"capture":"hours-4"}
{"step":8}
{"capture":"hours-12"}
"#;

#[test]
fn the_proof_script_of_stored_hours_task_5_parses() {
    let commands = script::parse_script(PROOF_SH5);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(1),
            ScriptCommand::Capture("hours-1".into()),
            ScriptCommand::Step(1),
            ScriptCommand::Capture("hours-2".into()),
            ScriptCommand::Step(2),
            ScriptCommand::Capture("hours-4".into()),
            ScriptCommand::Step(8),
            ScriptCommand::Capture("hours-12".into()),
        ])
    );
}

#[test]
fn the_script_names_columns() {
    assert_eq!(
        script::parse_script("{\"columns\":\"money\"}\n{\"columns\":\"hours\"}"),
        Ok(vec![
            ScriptCommand::Columns("money".into()),
            ScriptCommand::Columns("hours".into()),
        ])
    );
    assert!(matches!(
        script::parse_script("{\"step\":1}\n{\"columns\":\"table\"}"),
        Err(ScriptError::Line { line: 2, .. })
    ));
}

/// The proof script of Task 6 of stored hours, run by the lead on the display.
const PROOF_SH6: &str = r#"{"step":2}
{"columns":"hours"}
{"wait_frames":30}
{"capture":"table-hours"}
{"pick":"household:22"}
{"wait_frames":30}
{"capture":"panel-supported"}
{"pick":"workplace:a:shop"}
{"wait_frames":30}
{"capture":"panel-shop"}
"quit"
"#;

#[test]
fn the_proof_script_of_stored_hours_task_6_parses() {
    let commands = script::parse_script(PROOF_SH6);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(2),
            ScriptCommand::Columns("hours".into()),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("table-hours".into()),
            ScriptCommand::Pick("household:22".into()),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("panel-supported".into()),
            ScriptCommand::Pick("workplace:a:shop".into()),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("panel-shop".into()),
            ScriptCommand::Quit,
        ])
    );
}

/// The proof script of this plan's Task 7 (decision 2); the lead runs it.
const PROOF_SH7: &str = r#"{"step":1}
{"capture":"stored-1"}
{"report":"stored-1"}
{"step":1}
{"report":"stored-2"}
{"step":10}
{"columns":"hours"}
{"wait_frames":30}
{"capture":"stored-12-table"}
{"pick":"household:22"}
{"wait_frames":30}
{"capture":"stored-12-panel"}
{"report":"stored-12"}
"quit"
"#;

#[test]
fn the_proof_script_of_stored_hours_task_7_parses() {
    let commands = script::parse_script(PROOF_SH7);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(1),
            ScriptCommand::Capture("stored-1".into()),
            ScriptCommand::Report("stored-1".into()),
            ScriptCommand::Step(1),
            ScriptCommand::Report("stored-2".into()),
            ScriptCommand::Step(10),
            ScriptCommand::Columns("hours".into()),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("stored-12-table".into()),
            ScriptCommand::Pick("household:22".into()),
            ScriptCommand::WaitFrames(30),
            ScriptCommand::Capture("stored-12-panel".into()),
            ScriptCommand::Report("stored-12".into()),
            ScriptCommand::Quit,
        ])
    );
}

/// The proof script of Task 8c, run by the lead on the display.
const PROOF_8C: &str = r#"{"step":1}
{"strike":{"shock":"harvest_fails","places":"both","lasts":"until_lifted"}}
{"step":20}
{"rule":"seeking_in_place"}
{"rule":"hiring_within_means"}
{"rule":"stop_without_pay"}
{"rule":"resting_price"}
{"rule":"owner_restart"}
{"rule":"goods_step_down"}
{"step":40}
{"capture":"all-six"}
{"report":"all-six"}
"#;

#[test]
fn the_proof_script_of_task_8c_parses() {
    let commands = script::parse_script(PROOF_8C);
    assert_eq!(
        commands,
        Ok(vec![
            ScriptCommand::Step(1),
            ScriptCommand::Strike {
                shock: "harvest_fails".into(),
                places: "both".into(),
                lasts: "until_lifted".into(),
            },
            ScriptCommand::Step(20),
            ScriptCommand::Rule("seeking_in_place".into()),
            ScriptCommand::Rule("hiring_within_means".into()),
            ScriptCommand::Rule("stop_without_pay".into()),
            ScriptCommand::Rule("resting_price".into()),
            ScriptCommand::Rule("owner_restart".into()),
            ScriptCommand::Rule("goods_step_down".into()),
            ScriptCommand::Step(40),
            ScriptCommand::Capture("all-six".into()),
            ScriptCommand::Report("all-six".into()),
        ])
    );
}

#[test]
fn the_script_names_a_file_of_receipts() {
    assert_eq!(
        script::parse_script(r#"{"receipts":"kept"}"#),
        Ok(vec![ScriptCommand::Receipts("kept".into())])
    );
    let refused = script::parse_script("{\"step\":1}\n{\"receipts\":\"a/b\"}");
    assert!(
        matches!(&refused, Err(ScriptError::Line { line: 2, reason }) if reason.contains("a/b")),
        "a file name with a path in it must be refused at its line: {refused:?}"
    );
}
