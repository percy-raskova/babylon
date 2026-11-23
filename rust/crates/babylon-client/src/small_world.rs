//! The small world in the client: a period of the doubled world read as hours, goods and
//! payments, and the table that sums those readings.

pub mod controls;
pub mod frame;
pub mod inspect;
pub mod layout;
pub mod panel;
pub mod reading;
pub mod scene;
pub mod table;

pub use reading::{
    read_period, GoodsMove, Party, Payment, PaymentKind, PeriodReading, ReadingError, WorkFlow,
};
pub use scene::{
    install_scene, open_on_first_period, SceneCommand, SceneRunner, SceneStatus, SmallWorldPlugin,
};
pub use table::{table, Grouping, Table, TableRow, NOT_MEASURED};
