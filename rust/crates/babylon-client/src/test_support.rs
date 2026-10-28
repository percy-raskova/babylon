//! Test-only helpers shared across the crate's unit tests.

use bevy::camera::visibility::InheritedVisibility;
use bevy::ecs::schedule::IntoScheduleConfigs as _;
use bevy::input_focus::InputFocusSystems;
use bevy::prelude::{App, Plugin, PreUpdate, Query};
use std::ffi::OsString;
use std::sync::PoisonError;
use std::sync::{Mutex, MutexGuard};

/// Serializes tests that mutate process-global environment state.
static ENV_LOCK: Mutex<()> = Mutex::new(());

/// Locks [`ENV_LOCK`] and restores the guarded variable's prior value on
/// drop. Rust test threads run in one process, so a test that sets or
/// removes a variable must both serialize against its peers and put the
/// ambient value back; otherwise a dev box with `BABYLON_CAMPAIGN_ID` or
/// `BABYLON_READER_DSN` exported changes what unrelated tests see.
pub(crate) struct EnvVarGuard {
    _lock: MutexGuard<'static, ()>,
    key: &'static str,
    prior: Option<OsString>,
}

impl EnvVarGuard {
    /// Locks the environment and remembers `key`'s prior value.
    pub(crate) fn lock(key: &'static str) -> Self {
        let lock = ENV_LOCK.lock().unwrap_or_else(PoisonError::into_inner);
        let prior = std::env::var_os(key);
        Self {
            _lock: lock,
            key,
            prior,
        }
    }

    /// Sets the guarded variable for the lifetime of this guard.
    pub(crate) fn set(&self, value: &str) {
        std::env::set_var(self.key, value);
    }

    /// Removes the guarded variable for the lifetime of this guard.
    pub(crate) fn remove(&self) {
        std::env::remove_var(self.key);
    }
}

impl Drop for EnvVarGuard {
    fn drop(&mut self) {
        match self.prior.take() {
            Some(value) => std::env::set_var(self.key, value),
            None => std::env::remove_var(self.key),
        }
    }
}

/// Marks every UI node visible, standing in for the render pipeline.
///
/// Bevy 0.20's tab navigation skips descendants whose `InheritedVisibility` is
/// false, and only the visibility plugin (installed by the render stack)
/// computes that component from the `Visibility` hierarchy. A headless fixture
/// runs no renderer and never spawns a camera, so every node would stay
/// invisible and no control could ever be tabbed to. The observer's own focus
/// tree still decides tabbability from `Display`, `Visibility`, and policy, so
/// modelling "rendered and visible" here preserves the fixture's intent.
pub(crate) struct HeadlessVisibilityPlugin;

impl Plugin for HeadlessVisibilityPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(
            PreUpdate,
            reveal_ui_nodes.before(InputFocusSystems::Dispatch),
        );
    }
}

fn reveal_ui_nodes(mut nodes: Query<&mut InheritedVisibility>) {
    for mut visibility in &mut nodes {
        if !visibility.get() {
            *visibility = InheritedVisibility::VISIBLE;
        }
    }
}
