use super::NationalCohortReferenceError as Error;
use babylon_kernel::{content_digest::sha256_of, economic_identity::EconomicFunction};
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
        Self::decode_pinned(DOCUMENT)
    }
    pub(super) fn decode_pinned(bytes: &[u8]) -> Result<Self, Error> {
        if bytes.len() > 16_384 || sha256_of(bytes) != MAPPING_SHA256 {
            return Err(Error::FunctionMapping);
        }
        let doc: Document = serde_json::from_slice(bytes).map_err(|_| Error::FunctionMapping)?;
        if doc.contract != "NationalQcewFunctionMappingV1"
            || doc.evidence_class != "Designed"
            || doc.source_vintage != 2024
            || doc.functions.len() != 10
            || doc.residual_naics_codes != ["99"]
        {
            return Err(Error::FunctionMapping);
        }
        let mut members = BTreeMap::new();
        let mut functions = BTreeSet::new();
        for group in doc.functions {
            let function =
                EconomicFunction::from_source_key(&group.id).ok_or(Error::FunctionMapping)?;
            if !functions.insert(function) || group.naics_codes.is_empty() {
                return Err(Error::FunctionMapping);
            }
            for code in group.naics_codes {
                if members.insert(code, Some(function)).is_some() {
                    return Err(Error::FunctionMapping);
                }
            }
        }
        if members.insert("99".to_owned(), None).is_some() || members.len() != 50 {
            return Err(Error::FunctionMapping);
        }
        Ok(Self(members))
    }
    pub(super) fn admits(&self, code: &str, function: Option<EconomicFunction>) -> bool {
        self.0.get(code) == Some(&function)
    }
}
