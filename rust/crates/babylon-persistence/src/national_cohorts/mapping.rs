use super::NationalCohortReferenceError as Error;
use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};

use babylon_kernel::content_digest;
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};

pub(super) const DOCUMENT: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../contracts/national_qcew_function_mapping_v1.json"
));
pub(super) const MAPPING_SHA256: [u8; 32] = [
    113, 133, 208, 190, 219, 27, 244, 168, 48, 255, 81, 153, 212, 175, 159, 189, 83, 170, 136, 182,
    108, 164, 227, 76, 22, 116, 4, 66, 44, 34, 192, 125,
];

pub(super) const DOCUMENT_V2: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../contracts/national_qcew_function_mapping_v2.json"
));
pub(super) const MAPPING_V2_SHA256: [u8; 32] = [
    139, 95, 34, 217, 121, 184, 43, 15, 168, 8, 189, 21, 121, 254, 235, 120, 39, 151, 104, 238,
    217, 21, 171, 95, 137, 0, 165, 130, 13, 133, 28, 60,
];

/// What one trade set pins: its contract, its functions, its member codes (with 99) and its mapping digest.
struct MappingPins {
    contract: &'static str,
    functions: usize,
    codes: usize,
    sha256: [u8; 32],
}
const fn mapping_pins(set: TradeSet) -> MappingPins {
    match set {
        TradeSet::Ten => MappingPins {
            contract: "NationalQcewFunctionMappingV1",
            functions: 10,
            codes: 50,
            sha256: MAPPING_SHA256,
        },
        TradeSet::Twelve => MappingPins {
            contract: "NationalQcewFunctionMappingV2",
            functions: 12,
            codes: 64,
            sha256: MAPPING_V2_SHA256,
        },
    }
}

// The exact document digest also pins qualifications and evidence declarations.
// Only the membership fields needed for this capture are deserialized here.
#[derive(Deserialize)]
struct Document {
    contract: String,
    evidence_class: String,
    source_vintage: u16,
    functions: Vec<Function>,
    residual_naics_codes: Vec<String>,
}
#[derive(Deserialize)]
struct Function {
    id: String,
    naics_codes: Vec<String>,
}
pub(super) struct FunctionMapping(BTreeMap<String, Option<EconomicFunction>>);
impl FunctionMapping {
    #[cfg(test)]
    pub(super) fn load() -> Result<Self, Error> {
        Self::decode_pinned(DOCUMENT, TradeSet::Ten)
    }
    #[cfg(test)]
    pub(super) fn load_for(set: TradeSet) -> Result<Self, Error> {
        Self::decode_pinned(
            match set {
                TradeSet::Ten => DOCUMENT,
                TradeSet::Twelve => DOCUMENT_V2,
            },
            set,
        )
    }
    pub(super) fn decode_pinned(bytes: &[u8], set: TradeSet) -> Result<Self, Error> {
        let pins = mapping_pins(set);
        if bytes.len() > 16_384 || content_digest::sha256_of(bytes) != pins.sha256 {
            return Err(Error::FunctionMapping);
        }
        let doc: Document = serde_json::from_slice(bytes).map_err(|_| Error::FunctionMapping)?;
        if doc.contract != pins.contract
            || doc.evidence_class != "Designed"
            || doc.source_vintage != 2024
            || doc.functions.len() != pins.functions
            || doc.residual_naics_codes != ["99"]
        {
            return Err(Error::FunctionMapping);
        }
        let mut members = BTreeMap::new();
        let mut functions = BTreeSet::new();
        for group in doc.functions {
            let function = set
                .from_source_key(&group.id)
                .ok_or(Error::FunctionMapping)?;
            if !functions.insert(function) || group.naics_codes.is_empty() {
                return Err(Error::FunctionMapping);
            }
            for code in group.naics_codes {
                if members.insert(code, Some(function)).is_some() {
                    return Err(Error::FunctionMapping);
                }
            }
        }
        if members.insert("99".to_owned(), None).is_some() || members.len() != pins.codes {
            return Err(Error::FunctionMapping);
        }
        Ok(Self(members))
    }
    pub(super) fn admits(&self, code: &str, function: Option<EconomicFunction>) -> bool {
        self.0.get(code) == Some(&function)
    }
}
