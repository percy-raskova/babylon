//! The scene driven by a file: one command a line, pressed as a button is pressed, one at a
//! time and only while no beat is playing. Each command is answered by a line of
//! `replies.jsonl` in the script's folder. A picture and a report can be kept on the way.

use super::frame::ParticleMode;
use super::frame_time::{FrameTime, SceneFrameTimes};
use super::panel::{self, ShockNotice};
use super::scene::{SceneCommand, SceneRunner, SceneStatus};
use babylon_circuit_worlds::{Lasts, PeriodResult, Place, Places, Shock, Workplace};
use bevy::prelude::*;
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use hypergraph_rs_bevy::{BeatClock, FieldConfig, Phase};
use serde::{Deserialize, Serialize};
use std::fmt::{Display, Error as FormatError, Formatter};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

/// The file the replies are appended to, in the script's folder.
pub const REPLIES_FILE: &str = "replies.jsonl";
/// The report written when the engine refuses, in the script's folder.
pub const REFUSAL_FILE: &str = "refusal.json";

/// One line of a script. The names inside are `harvest_fails` or `power_cut`; `a`, `b` or
/// `both`; `ten_periods` or `until_lifted`; `groups` or `people`.
#[derive(Deserialize, Clone, Debug, PartialEq, Eq)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum ScriptCommand {
    Step(u32),
    Strike {
        shock: String,
        places: String,
        lasts: String,
    },
    Lift {
        shock: String,
        place: String,
    },
    Particles(String),
    Capture(String),
    Report(String),
    WaitFrames(u32),
    Quit,
}

/// Why a script was refused: the line, and the words.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScriptError {
    Line { line: usize, reason: String },
}

impl Display for ScriptError {
    fn fmt(&self, f: &mut Formatter<'_>) -> Result<(), FormatError> {
        match self {
            Self::Line { line, reason } => write!(f, "script line {line}: {reason}"),
        }
    }
}

impl std::error::Error for ScriptError {}

fn shock_named(name: &str) -> Option<Shock> {
    match name {
        "harvest_fails" => Some(Shock::HarvestFails),
        "power_cut" => Some(Shock::PowerCut),
        _ => None,
    }
}

fn places_named(name: &str) -> Option<Places> {
    match name {
        "a" => Some(Places::A),
        "b" => Some(Places::B),
        "both" => Some(Places::Both),
        _ => None,
    }
}

fn lasts_named(name: &str) -> Option<Lasts> {
    match name {
        "ten_periods" => Some(Lasts::TenPeriods),
        "until_lifted" => Some(Lasts::UntilLifted),
        _ => None,
    }
}

fn place_named(name: &str) -> Option<Place> {
    match name {
        "a" => Some(Place::A),
        "b" => Some(Place::B),
        _ => None,
    }
}

fn mode_named(name: &str) -> Option<ParticleMode> {
    match name {
        "groups" => Some(ParticleMode::Groups),
        "people" => Some(ParticleMode::People),
        _ => None,
    }
}

/// A file's stem is letters, digits, `-` and `_` and nothing else: no folder, no dot.
fn stem_is_plain(name: &str) -> bool {
    !name.is_empty()
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
}

fn known<T>(found: Option<T>, what: &str, name: &str) -> Result<T, String> {
    found.ok_or_else(|| format!("{what} {name:?} is not one the scene knows"))
}

/// Every name of a command is one the scene knows, so that a script fails before a window opens.
fn check_names(command: &ScriptCommand) -> Result<(), String> {
    match command {
        ScriptCommand::Strike {
            shock,
            places,
            lasts,
        } => {
            known(shock_named(shock), "shock", shock)?;
            known(places_named(places), "places", places)?;
            known(lasts_named(lasts), "lasts", lasts)?;
        }
        ScriptCommand::Lift { shock, place } => {
            known(shock_named(shock), "shock", shock)?;
            known(place_named(place), "place", place)?;
        }
        ScriptCommand::Particles(name) => {
            known(mode_named(name), "particles", name)?;
        }
        ScriptCommand::Capture(name) | ScriptCommand::Report(name) => {
            if !stem_is_plain(name) {
                return Err(format!("a file name is letters, digits, - and _: {name:?}"));
            }
        }
        ScriptCommand::Step(_) | ScriptCommand::WaitFrames(_) | ScriptCommand::Quit => {}
    }
    Ok(())
}

/// A script is one JSON value a line; a blank line is skipped. The first line that is not a
/// command the scene knows refuses the whole file.
///
/// # Errors
/// The line and the reason.
pub fn parse_script(text: &str) -> Result<Vec<ScriptCommand>, ScriptError> {
    let mut commands = Vec::new();
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let refuse = |reason: String| ScriptError::Line {
            line: index + 1,
            reason,
        };
        let command: ScriptCommand =
            serde_json::from_str(line).map_err(|error| refuse(error.to_string()))?;
        check_names(&command).map_err(refuse)?;
        commands.push(command);
    }
    Ok(commands)
}

/// What `Report(name)` writes: per workplace, the hours given and the units made in every period
/// kept, in the order of the periods.
#[derive(Serialize, Clone, Debug, PartialEq)]
pub struct ScriptReport {
    pub period: u64,
    pub hours_given: Vec<(String, Vec<u64>)>,
    pub made: Vec<(String, Vec<u64>)>,
    pub shocks: Vec<String>,
    pub frame: Option<FrameTime>,
    pub refusal: Option<String>,
}

/// Where a script's run stands.
#[derive(Debug)]
enum State {
    /// Between commands: the next starts when no beat is playing.
    Idle,
    /// Steps still to press, each when no beat is playing.
    Stepping(u32),
    /// A command was pressed last frame: its effect is checked, then the command is answered.
    Checking(u32),
    /// Frames still to wait.
    Waiting(u32),
    /// A picture was asked of the window and is not yet saved.
    Capturing,
    /// The script is over.
    Over,
}

/// The script being run: its commands, its folder and where it stands.
#[derive(Resource)]
pub struct ScriptRun {
    folder: PathBuf,
    commands: Vec<ScriptCommand>,
    next: usize,
    state: State,
    captured: Option<Result<(), String>>,
}

impl ScriptRun {
    /// A run of `commands`, answering into `folder`.
    #[must_use]
    pub fn new(folder: PathBuf, commands: Vec<ScriptCommand>) -> Self {
        Self {
            folder,
            commands,
            next: 0,
            state: State::Idle,
            captured: None,
        }
    }

    /// The number of the command last started: the first is 1.
    fn line(&self) -> usize {
        self.next
    }
}

/// Reads and parses a script file.
///
/// # Errors
/// The file could not be read or a line was refused, in words.
pub fn load_script(path: &Path) -> Result<ScriptRun, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|error| format!("the script {} could not be read: {error}", path.display()))?;
    let commands = parse_script(&text).map_err(|error| error.to_string())?;
    let folder = path
        .parent()
        .map_or_else(|| PathBuf::from("."), Path::to_path_buf);
    Ok(ScriptRun::new(folder, commands))
}

fn append_reply(
    folder: &Path,
    line: usize,
    event: &str,
    reason: Option<&str>,
) -> Result<(), String> {
    let value = match reason {
        Some(reason) => serde_json::json!({"line": line, "event": event, "reason": reason}),
        None => serde_json::json!({"line": line, "event": event}),
    };
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(folder.join(REPLIES_FILE))
        .map_err(|error| error.to_string())?;
    writeln!(file, "{value}").map_err(|error| error.to_string())
}

/// The report of the run so far.
fn build_report(
    scene: &SceneRunner,
    times: &SceneFrameTimes,
    refusal: Option<String>,
) -> ScriptReport {
    let history = scene.runner.history();
    let by_workplace = |pick: fn(&PeriodResult, usize) -> u64| {
        Workplace::ALL
            .iter()
            .map(|workplace| {
                (
                    workplace.label(),
                    history
                        .iter()
                        .map(|result| pick(result, workplace.index()))
                        .collect(),
                )
            })
            .collect::<Vec<(String, Vec<u64>)>>()
    };
    ScriptReport {
        period: u64::try_from(history.len()).unwrap_or(u64::MAX),
        hours_given: by_workplace(|result, k| result.summary.hours_attended[k]),
        made: by_workplace(|result, k| result.summary.made[k]),
        shocks: panel::shock_rows(scene.runner.shocks(), scene.runner.next_period())
            .into_iter()
            .map(|row| row.text)
            .collect(),
        frame: times.last,
        refusal,
    }
}

fn write_json(path: &Path, report: &ScriptReport) -> Result<(), String> {
    let text = serde_json::to_string_pretty(report).map_err(|error| error.to_string())?;
    let mut file = File::create(path).map_err(|error| error.to_string())?;
    file.write_all(text.as_bytes())
        .map_err(|error| error.to_string())
}

/// Save a captured window as a PNG of three colour channels.
fn save_png(captured: &ScreenshotCaptured, path: &Path) -> Result<(), String> {
    captured
        .image
        .clone()
        .try_into_dynamic()
        .map_err(|error| format!("the picture could not be read: {error}"))
        .and_then(|image| {
            image
                .to_rgb8()
                .save(path)
                .map_err(|error| format!("the picture could not be written: {error}"))
        })
}

/// Ask the window for a picture; the file is made now and refuses a name that exists.
fn start_capture(run: &ScriptRun, name: &str, commands: &mut Commands) -> Result<(), String> {
    let path = run.folder.join(format!("{name}.png"));
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|error| format!("the picture {} could not be made: {error}", path.display()))?;
    commands.spawn(Screenshot::primary_window()).observe(
        move |captured: On<ScreenshotCaptured>, mut run: ResMut<ScriptRun>| {
            run.captured = Some(save_png(&captured, &path));
        },
    );
    Ok(())
}

/// What the script system reads of the world.
#[derive(bevy::ecs::system::SystemParam)]
pub struct ScriptWorld<'w> {
    time: Res<'w, Time>,
    clock: Res<'w, BeatClock>,
    config: Res<'w, FieldConfig>,
    scene: Res<'w, SceneRunner>,
    status: Res<'w, SceneStatus>,
    notice: ResMut<'w, ShockNotice>,
    times: Res<'w, SceneFrameTimes>,
    presses: MessageWriter<'w, SceneCommand>,
    exit: MessageWriter<'w, AppExit>,
}

impl ScriptWorld<'_> {
    fn resting(&self) -> bool {
        matches!(
            self.clock.phase(self.time.elapsed(), &self.config.beats),
            Phase::Resting
        )
    }

    /// The words of a refusal that came of the last press, if one did.
    fn refusal(&self) -> Option<String> {
        self.status
            .refusal
            .clone()
            .or_else(|| self.notice.text.clone())
    }
}

/// End the script on a refusal: say so in the replies, keep the report and leave the app.
fn refuse(run: &mut ScriptRun, world: &mut ScriptWorld, reason: &str) {
    if let Err(error) = append_reply(&run.folder, run.line(), "refused", Some(reason)) {
        log::error!("small world script: the reply could not be written: {error}");
    }
    let report = build_report(&world.scene, &world.times, Some(reason.to_owned()));
    if let Err(error) = write_json(&run.folder.join(REFUSAL_FILE), &report) {
        log::error!("small world script: the refusal could not be kept: {error}");
    }
    log::error!(
        "small world script refused at command {}: {reason}",
        run.line()
    );
    run.state = State::Over;
    world.exit.write(AppExit::from_code(2));
}

/// Answer the command as done and take the script on to the next.
fn done(run: &mut ScriptRun, world: &mut ScriptWorld) {
    match append_reply(&run.folder, run.line(), "done", None) {
        Ok(()) => run.state = State::Idle,
        Err(error) => refuse(run, world, &error),
    }
}

/// Press the next command, or finish a command that needs no press.
fn begin(run: &mut ScriptRun, world: &mut ScriptWorld, commands: &mut Commands) {
    let Some(command) = run.commands.get(run.next).cloned() else {
        run.state = State::Over;
        return;
    };
    run.next += 1;
    world.notice.text = None;
    match command {
        ScriptCommand::Step(0) | ScriptCommand::WaitFrames(0) => done(run, world),
        ScriptCommand::Step(n) => run.state = State::Stepping(n),
        ScriptCommand::WaitFrames(n) => run.state = State::Waiting(n),
        ScriptCommand::Strike {
            shock,
            places,
            lasts,
        } => {
            if let (Some(shock), Some(places), Some(lasts)) = (
                shock_named(&shock),
                places_named(&places),
                lasts_named(&lasts),
            ) {
                world
                    .presses
                    .write(SceneCommand::Strike(shock, places, lasts));
            }
            run.state = State::Checking(0);
        }
        ScriptCommand::Lift { shock, place } => {
            if let (Some(shock), Some(place)) = (shock_named(&shock), place_named(&place)) {
                world.presses.write(SceneCommand::Lift(shock, place));
            }
            run.state = State::Checking(0);
        }
        ScriptCommand::Particles(name) => {
            if let Some(mode) = mode_named(&name) {
                world.presses.write(SceneCommand::Particles(mode));
            }
            run.state = State::Checking(0);
        }
        ScriptCommand::Capture(name) => match start_capture(run, &name, commands) {
            Ok(()) => run.state = State::Capturing,
            Err(reason) => refuse(run, world, &reason),
        },
        ScriptCommand::Report(name) => {
            let report = build_report(&world.scene, &world.times, None);
            match write_json(&run.folder.join(format!("{name}.json")), &report) {
                Ok(()) => done(run, world),
                Err(reason) => refuse(run, world, &reason),
            }
        }
        ScriptCommand::Quit => {
            done(run, world);
            world.exit.write(AppExit::Success);
            run.state = State::Over;
        }
    }
}

/// Press one command at a time, each only while no beat is playing and nothing is pending.
pub fn run_script(mut run: ResMut<ScriptRun>, mut world: ScriptWorld, mut commands: Commands) {
    let run = &mut *run;
    match run.state {
        State::Over => {}
        State::Idle => {
            if world.resting() {
                begin(run, &mut world, &mut commands);
            }
        }
        State::Stepping(left) => {
            if world.resting() {
                world.presses.write(SceneCommand::Step);
                run.state = State::Checking(left.saturating_sub(1));
            }
        }
        State::Checking(left) => {
            if let Some(reason) = world.refusal() {
                refuse(run, &mut world, &reason);
            } else if left > 0 {
                run.state = State::Stepping(left);
            } else {
                done(run, &mut world);
            }
        }
        State::Waiting(left) => {
            if left <= 1 {
                done(run, &mut world);
            } else {
                run.state = State::Waiting(left - 1);
            }
        }
        State::Capturing => match run.captured.take() {
            Some(Ok(())) => done(run, &mut world),
            Some(Err(reason)) => refuse(run, &mut world, &reason),
            None => {}
        },
    }
}

#[cfg(test)]
#[path = "script_tests.rs"]
mod tests;
