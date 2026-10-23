//! Leaf implementation for the parent module; public paths stay on the parent.

#[allow(unused_imports)]
use super::{Error, ExitCode};

#[allow(unused_imports)]
use super::{arguments, facts, report, run, witness};

pub(crate) type Result<T> = std::result::Result<T, Box<dyn Error>>;

pub(crate) fn refused(message: impl Into<String>) -> Box<dyn Error> {
    std::io::Error::other(message.into()).into()
}

pub(crate) fn checked_sum(mut values: impl Iterator<Item = u64>) -> Result<u64> {
    values.try_fold(0_u64, |sum, n| {
        sum.checked_add(n)
            .ok_or_else(|| refused("receipt sum overflow"))
    })
}

pub(crate) fn quantity(a: u64, b: u64) -> Result<u64> {
    a.checked_mul(b)
        .ok_or_else(|| refused("native quantity or mass overflow"))
}

pub(crate) fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut encoded = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(encoded, "{byte:02x}").expect("String write");
    }
    encoded
}

pub(crate) fn execute() -> Result<()> {
    let Some(args) = arguments::Arguments::parse(std::env::args().skip(1))? else {
        return Ok(());
    };
    let inputs = arguments::read_inputs(&args)?;
    let report = run::experiment(&inputs, &args.candidate)?;
    arguments::write_report(&args.output, &report)?;
    if !report.qualified {
        return Err(refused(format!(
            "candidate lacks required causal witnesses; complete report: {}",
            args.output.display()
        )));
    }
    println!(
        "Four candidates / 64 committed periods qualified: {}",
        args.output.display()
    );
    Ok(())
}
