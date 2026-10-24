//! Dispatch the durable campaign observer and headless Archive commands.

use babylon_client::app;
use babylon_client::app::AppMode;
use babylon_client::cli::{self, CliRequest};
use bevy::app::AppExit;

fn main() {
    let request = cli::parse(std::env::args_os().skip(1)).unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(2);
    });
    let mode = match request {
        CliRequest::Help(topic) => {
            print!("{}", cli::render_help(topic));
            return;
        }
        CliRequest::Windowed {
            initial_target,
            qualification_control,
        } => AppMode::Windowed {
            initial_target,
            qualification_control,
        },
        CliRequest::Headless {
            command,
            campaign_id,
        } => AppMode::Headless {
            command,
            campaign_id,
        },
    };
    let exit = app::build_app(mode)
        .unwrap_or_else(|error| {
            eprintln!("babylon-client startup refused: {error}");
            std::process::exit(2);
        })
        .run();
    std::process::exit(match exit {
        AppExit::Success => 0,
        AppExit::Error(code) => i32::from(code.get()),
    });
}
