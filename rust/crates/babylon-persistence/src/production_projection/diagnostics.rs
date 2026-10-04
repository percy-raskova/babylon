//! Opt-in refusal diagnostics. No retained state, authority or validation changes.
use super::ProductionProjectionError;
use crate::observer_reader::ObserverEconomyError;

#[derive(Clone, Copy, Debug)]
pub(crate) enum Stage {
    FoundationQuery,
    FoundationGraphAdmission,
    FoundationEconomicAdmission,
    FoundationLoad,
    FoundationComponentHash,
    FoundationRegisterDecode,
    FoundationGraphSession,
    FoundationAdmission,
    HistoryLoad,
    AuthenticatedEnvelope,
    EvidenceValidation,
    EvidenceCanonical,
    EvidenceHash,
    InitialHistory,
    ExtendHistory,
    MaterialRow,
    LookupDecode,
    StorageDecode,
    RegisterDecode,
    ReceiptIdentity,
    ReceiptBinding,
    ReceiptTick,
    PeriodLifecycle,
    OrderHistory,
    CurrentProjection,
    Staffing,
    Attribution,
    Metadata,
    Duration,
    Events,
    Maintenance,
    Labor,
    Households,
    HouseholdServices,
    Prices,
    MaterialBalance,
    FreightCapacity,
    Merchants,
    Sites,
    Routes,
    Freight,
    LifecycleOrders,
    LifecycleServices,
    LifecycleEquipment,
    LifecyclePrices,
    LifecycleHouseholds,
}

pub(crate) fn projection<T>(
    stage: Stage,
    tick: u64,
    result: Result<T, ProductionProjectionError>,
) -> Result<T, ProductionProjectionError> {
    result.inspect_err(|error| report(stage, tick, Some(*error)))
}

pub(crate) fn observer<T>(
    stage: Stage,
    tick: u64,
    result: Result<T, ObserverEconomyError>,
) -> Result<T, ObserverEconomyError> {
    result.inspect_err(|_| report(stage, tick, None))
}

fn report(stage: Stage, tick: u64, error: Option<ProductionProjectionError>) {
    if std::env::var("BABYLON_TIMINGS").as_deref() != Ok("1") {
        return;
    }
    if let Some(source) = error {
        eprintln!("observer_projection_refused tick={tick} stage={stage:?} source={source:?}");
    } else {
        eprintln!("observer_projection_refused tick={tick} stage={stage:?}");
    }
}

pub(crate) fn invalid(stage: Stage, tick: u64) -> ObserverEconomyError {
    report(stage, tick, None);
    ObserverEconomyError::InvalidProjection
}

/// Opt-in wall time for one real stage, including failures; no retained state.
pub(crate) struct Timing {
    started: Option<std::time::Instant>,
    stage: Stage,
    tick: u64,
}

impl Timing {
    pub(crate) fn start(stage: Stage, tick: u64) -> Self {
        Self {
            started: (std::env::var("BABYLON_TIMINGS").as_deref() == Ok("1"))
                .then(std::time::Instant::now),
            stage,
            tick,
        }
    }
}

impl Drop for Timing {
    fn drop(&mut self) {
        if let Some(started) = self.started {
            let elapsed_us = started.elapsed().as_micros();
            let memory = process_memory();
            eprintln!(
                "observer_projection_timing tick={} stage={:?} elapsed_us={elapsed_us} resident_kib={} high_water_kib={}",
                self.tick, self.stage, MemoryValue(memory.resident), MemoryValue(memory.high_water)
            );
        }
    }
}

#[derive(Default)]
struct ProcessMemory {
    resident: Option<u64>,
    high_water: Option<u64>,
}
struct MemoryValue(Option<u64>);
impl std::fmt::Display for MemoryValue {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.0 {
            Some(value) => write!(formatter, "{value}"),
            None => formatter.write_str("unavailable"),
        }
    }
}

#[cfg(target_os = "linux")]
fn process_memory() -> ProcessMemory {
    use std::io::Read as _;
    // Proc status is small; refuse truncation rather than interpret a partial sample.
    let mut bytes = [0_u8; 8192];
    let mut read = || -> std::io::Result<usize> {
        let mut file = std::fs::File::open("/proc/self/status")?;
        let mut count = 0;
        while count < bytes.len() {
            match file.read(&mut bytes[count..]) {
                Ok(0) => return Ok(count),
                Ok(length) => count += length,
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => {}
                Err(error) => return Err(error),
            }
        }
        // A complete sample exactly filling the buffer is still accepted.
        if file.read(&mut [0_u8; 1])? == 0 {
            Ok(count)
        } else {
            Err(std::io::ErrorKind::InvalidData.into())
        }
    };
    read()
        .ok()
        .and_then(|count| std::str::from_utf8(&bytes[..count]).ok())
        .and_then(parse_process_memory)
        .unwrap_or_default()
}

#[cfg(not(target_os = "linux"))]
fn process_memory() -> ProcessMemory {
    ProcessMemory::default()
}

#[cfg(any(target_os = "linux", test))]
fn parse_process_memory(status: &str) -> Option<ProcessMemory> {
    let mut memory = ProcessMemory::default();
    for line in status.lines() {
        let target = if line.starts_with("VmRSS:") {
            &mut memory.resident
        } else if line.starts_with("VmHWM:") {
            &mut memory.high_water
        } else {
            continue;
        };
        if target.is_some() {
            return None;
        }
        let mut fields = line.split_ascii_whitespace();
        fields.next()?;
        let amount = fields.next()?;
        if amount.is_empty()
            || !amount.bytes().all(|byte| byte.is_ascii_digit())
            || fields.next()? != "kB"
            || fields.next().is_some()
        {
            return None;
        }
        *target = Some(amount.parse().ok()?);
    }
    Some(memory)
}

#[cfg(test)]
mod memory_controls {
    use super::*;

    #[test]
    fn process_status_memory_is_exact_bounded_numeric_or_unavailable() {
        let memory =
            parse_process_memory("Name: hidden\nVmHWM: 8398300 kB\nVmRSS: 7293040 kB\n").unwrap();
        assert_eq!(memory.resident, Some(7_293_040));
        assert_eq!(memory.high_water, Some(8_398_300));
        assert_eq!(MemoryValue(None).to_string(), "unavailable");
        assert_eq!(MemoryValue(Some(0)).to_string(), "0");
        let absent = parse_process_memory("Name: hidden\n").unwrap();
        assert_eq!(absent.resident, None);
        assert_eq!(absent.high_water, None);
        for malformed in [
            "VmRSS: 3 MB",
            "VmRSS: -3 kB",
            "VmRSS: 3 kB extra",
            "VmRSS: 3 kB\nVmRSS: 4 kB",
            "VmHWM: 18446744073709551616 kB",
        ] {
            assert!(parse_process_memory(malformed).is_none());
        }
    }
}
