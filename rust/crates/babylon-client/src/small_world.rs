//! The small world in the client: a period of the doubled world read as hours, goods and
//! payments, and the table that sums those readings.

pub mod reading;
pub mod table;

pub use reading::{
    read_period, GoodsMove, Party, Payment, PaymentKind, PeriodReading, ReadingError, WorkFlow,
};
pub use table::{table, Grouping, Table, TableRow, NOT_MEASURED};
