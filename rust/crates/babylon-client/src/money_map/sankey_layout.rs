//! Separate origin and destination columns allow a location on both sides of a transfer.
use super::state::{Connection, Direction};

const BAND_SPACE: f64 = 184.0;
const LABEL_SPACE: f64 = 40.0;

pub(super) struct Place {
    pub(super) key: Option<String>,
    pub(super) top: f64,
    pub(super) thickness: f64,
}

pub(super) struct Band {
    pub(super) row: usize,
    pub(super) payer: usize,
    pub(super) recipient: usize,
    pub(super) start: f64,
    pub(super) end: f64,
    pub(super) thickness: f64,
}
impl Band {
    pub(super) fn upper_at(&self, x: f64) -> f64 {
        let blend = x * x * (3.0 - 2.0 * x);
        self.start + (self.end - self.start) * blend
    }
}

#[derive(Default)]
pub(super) struct DiagramLayout {
    pub(super) payers: Vec<Place>,
    pub(super) recipients: Vec<Place>,
    pub(super) bands: Vec<Band>,
    pub(super) height: u32,
}

fn add(column: &mut Vec<Place>, key: Option<&str>, amount: f64) -> usize {
    if let Some(index) = column.iter().position(|node| node.key.as_deref() == key) {
        column[index].thickness += amount;
        index
    } else {
        column.push(Place {
            key: key.map(str::to_owned),
            top: 0.0,
            thickness: amount,
        });
        column.len() - 1
    }
}

fn place(column: &mut [Place], height: u32) {
    let extent = column
        .iter()
        .map(|n| n.thickness + LABEL_SPACE)
        .sum::<f64>();
    let mut top = (f64::from(height) - extent) * 0.5 + LABEL_SPACE * 0.5;
    for node in column {
        node.top = top;
        top += node.thickness + LABEL_SPACE;
    }
}

pub(super) fn layout(county: &str, rows: &[Connection]) -> DiagramLayout {
    let home = Some(format!("county:{county}"));
    let values: Vec<_> = rows
        .iter()
        .enumerate()
        .filter_map(|(i, row)| {
            let n = row.quantity.micros().parse::<f64>().ok()?;
            (n.is_finite() && n > 0.0).then_some((i, row, n))
        })
        .collect();
    let total = values.iter().map(|(_, _, n)| *n).sum::<f64>();
    let mut diagram = DiagramLayout::default();
    for (i, row, n) in values {
        let (from, to) = match row.key.direction {
            Direction::PaidTo => (&home, &row.key.peer),
            Direction::ReceivedFrom => (&row.key.peer, &home),
            Direction::Internal => (&home, &home),
        };
        let thickness = BAND_SPACE * (n / total);
        let payer = add(&mut diagram.payers, from.as_deref(), thickness);
        let recipient = add(&mut diagram.recipients, to.as_deref(), thickness);
        diagram.bands.push(Band {
            row: i,
            payer,
            recipient,
            start: 0.0,
            end: 0.0,
            thickness,
        });
    }
    // SQL returns at most twenty counterparties and at most one additional home node.
    let count = u32::try_from(diagram.payers.len().max(diagram.recipients.len()))
        .expect("bounded payment page");
    diagram.height = 184 + 40 * count;
    place(&mut diagram.payers, diagram.height);
    place(&mut diagram.recipients, diagram.height);
    let mut left: Vec<_> = diagram.payers.iter().map(|p| p.top).collect();
    let mut right: Vec<_> = diagram.recipients.iter().map(|p| p.top).collect();
    for band in &mut diagram.bands {
        band.start = left[band.payer];
        band.end = right[band.recipient];
        left[band.payer] += band.thickness;
        right[band.recipient] += band.thickness;
    }
    diagram
}
