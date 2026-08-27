//! Governed replay-identity discriminants and scalar codecs.

use std::collections::TryReserveError;

use babylon_graph::stable_element::{
    StableElementKeyV1, StableElementResolverV1, StableIdentityError,
};

use crate::causal_contract::{
    canonical_event_type, EffectSignature, EvidenceClass, RuleRole, ShapeVerb,
};
use crate::evaluator::Value;
use crate::types::{BslType, EnumRegistry, EnumTypeId, FieldKind};
use crate::vocabulary::EnumKind;

/// Maximum bytes one BSL-owned identity section may contain.
pub const MAX_IDENTITY_SECTION_BYTES_V1: usize = 67_108_864;
/// Maximum exact UTF-8 bytes in one governance string without a narrower grammar.
pub const MAX_GOVERNANCE_UTF8_BYTES_V1: usize = 4_194_304;
/// Maximum bytes in one intrinsic identity shared by fuel and replay identity.
pub(crate) const MAX_INTRINSIC_IDENTITY_BYTES_V1: usize = 96;

/// One grammar violation in the shared intrinsic identity validator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum IntrinsicIdentityViolation {
    Empty,
    TooLong { actual: usize },
    NonAscii { index: usize },
    Delimiter { index: usize },
}

/// Validate the one canonical intrinsic identity grammar.
pub(crate) fn validate_intrinsic_identity(value: &str) -> Result<(), IntrinsicIdentityViolation> {
    if value.is_empty() {
        return Err(IntrinsicIdentityViolation::Empty);
    }
    if value.len() > MAX_INTRINSIC_IDENTITY_BYTES_V1 {
        return Err(IntrinsicIdentityViolation::TooLong {
            actual: value.len(),
        });
    }
    for (index, byte) in value
        .bytes()
        .enumerate()
        .take(MAX_INTRINSIC_IDENTITY_BYTES_V1)
    {
        if !byte.is_ascii() {
            return Err(IntrinsicIdentityViolation::NonAscii { index });
        }
        if matches!(byte, b'|' | b'\n' | b'\r') {
            return Err(IntrinsicIdentityViolation::Delimiter { index });
        }
    }
    Ok(())
}

/// A governed BSL identity-codec refusal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IdentityCodecError {
    /// A graph reference did not resolve through the sealed stable resolver.
    StableIdentity(StableIdentityError),
    /// A binary64 value was NaN or infinite.
    NonFiniteValue,
    /// A constant used a runtime enum or graph-reference form.
    InvalidConstantKind,
    /// An option byte was neither absent nor present.
    InvalidOptionByte {
        /// Invalid byte.
        value: u8,
    },
    /// An enum id did not belong to the supplied registry.
    UnknownEnumType {
        /// Foreign or missing enum id.
        id: EnumTypeId,
    },
    /// A governed string failed its grammar or length limit.
    InvalidString {
        /// Semantic field name.
        field: &'static str,
        /// Offending byte position or received length boundary.
        index: usize,
    },
    /// A governed section exceeded its row ceiling.
    RowLimit {
        /// Section name.
        section: &'static str,
        /// Received rows.
        actual: usize,
        /// Governed maximum.
        maximum: usize,
    },
    /// Aggregate rows exceeded their governed ceiling.
    AggregateRowLimit {
        /// Received aggregate rows.
        actual: usize,
        /// Governed maximum.
        maximum: usize,
    },
    /// Checked size arithmetic overflowed.
    CapacityOverflow {
        /// Object being sized.
        field: &'static str,
    },
    /// A checked integer conversion failed.
    IntegerConversion {
        /// Converted field.
        field: &'static str,
        /// Unrepresentable value.
        value: usize,
    },
    /// A governed byte ceiling was exceeded.
    ByteLimit {
        /// Encoded object name.
        field: &'static str,
        /// Received byte count.
        actual: usize,
        /// Governed maximum.
        maximum: usize,
    },
    /// A bounded allocation failed.
    Allocation {
        /// Allocated object name.
        field: &'static str,
        /// Requested capacity.
        requested: usize,
    },
    /// A fired count could not fit the governed u64 lane.
    FiredCountOverflow {
        /// Unrepresentable fired count.
        value: usize,
    },
}

impl From<StableIdentityError> for IdentityCodecError {
    fn from(value: StableIdentityError) -> Self {
        Self::StableIdentity(value)
    }
}

/// A bounded, allocation-aware identity byte writer.
pub(crate) struct IdentityWriter {
    field: &'static str,
    bytes: Vec<u8>,
}

impl IdentityWriter {
    pub(crate) const fn new(field: &'static str) -> Self {
        Self {
            field,
            bytes: Vec::new(),
        }
    }

    pub(crate) fn push(&mut self, value: u8) -> Result<(), IdentityCodecError> {
        self.extend(&[value])
    }

    pub(crate) fn extend(&mut self, value: &[u8]) -> Result<(), IdentityCodecError> {
        let requested = checked_add(self.field, self.bytes.len(), value.len())?;
        if requested > MAX_IDENTITY_SECTION_BYTES_V1 {
            return Err(IdentityCodecError::ByteLimit {
                field: self.field,
                actual: requested,
                maximum: MAX_IDENTITY_SECTION_BYTES_V1,
            });
        }
        self.bytes
            .try_reserve_exact(value.len())
            .map_err(|_: TryReserveError| IdentityCodecError::Allocation {
                field: self.field,
                requested,
            })?;
        self.bytes.extend_from_slice(value);
        Ok(())
    }

    pub(crate) fn str32(
        &mut self,
        field: &'static str,
        value: &str,
    ) -> Result<(), IdentityCodecError> {
        self.extend(&checked_u32(field, value.len())?.to_be_bytes())?;
        self.extend(value.as_bytes())
    }

    pub(crate) fn finish(self) -> Vec<u8> {
        self.bytes
    }
}

/// Encode one exact `ValueV1` into `output`.
///
/// # Errors
/// Returns a semantic, stable-reference, numeric, arithmetic, byte-limit,
/// conversion, or allocation error without modifying `output`.
pub fn encode_value_v1(
    value: &Value,
    resolver: &StableElementResolverV1,
    output: &mut Vec<u8>,
) -> Result<(), IdentityCodecError> {
    let mut writer = IdentityWriter::new("ValueV1");
    encode_value(value, resolver, &mut writer)?;
    append_checked(output, "ValueV1 output", &writer.finish())
}

fn encode_value(
    value: &Value,
    resolver: &StableElementResolverV1,
    output: &mut IdentityWriter,
) -> Result<(), IdentityCodecError> {
    match value {
        Value::Int(value) => encode_int(*value, output),
        Value::Currency(value) => encode_currency(value.micro_units(), output),
        Value::Real(value) => encode_real(*value, output),
        Value::Ratio { value, floor, cap } => {
            output.push(0x04)?;
            output.extend(&canonical_f64_bits(value.get())?.to_be_bytes())?;
            encode_ratio_option(*floor, output)?;
            encode_ratio_option(*cap, output)
        }
        Value::Bool(value) => {
            output.push(0x05)?;
            output.push(u8::from(*value))
        }
        Value::Enum { enum_type, member } => {
            validate_enum_type("ValueV1 enum type", enum_type)?;
            validate_enum_member("ValueV1 enum member", member)?;
            output.push(0x06)?;
            output.str32("ValueV1 enum type", enum_type)?;
            output.str32("ValueV1 enum member", member)
        }
        Value::NodeRef(node) => {
            let key = resolver.node_key(*node)?;
            append_stable_key(0x07, key, output)
        }
        Value::HyperedgeRef(hyperedge) => {
            let key = resolver.hyperedge_key(*hyperedge)?;
            append_stable_key(0x08, key, output)
        }
        Value::EdgeRef(edge) => {
            let key = resolver.edge_key(&edge.edge_type, edge.source, edge.target)?;
            append_stable_key(0x09, &key, output)
        }
    }
}

fn encode_int(value: i64, output: &mut IdentityWriter) -> Result<(), IdentityCodecError> {
    output.push(0x01)?;
    output.extend(&value.to_be_bytes())
}

fn encode_currency(value: i128, output: &mut IdentityWriter) -> Result<(), IdentityCodecError> {
    output.push(0x02)?;
    output.extend(&value.to_be_bytes())
}

fn encode_real(value: f64, output: &mut IdentityWriter) -> Result<(), IdentityCodecError> {
    output.push(0x03)?;
    output.extend(&canonical_f64_bits(value)?.to_be_bytes())
}

fn encode_ratio_option(
    value: Option<babylon_kernel::Ratio>,
    output: &mut IdentityWriter,
) -> Result<(), IdentityCodecError> {
    match value {
        None => output.push(0),
        Some(value) => {
            output.push(1)?;
            output.extend(&canonical_f64_bits(value.get())?.to_be_bytes())
        }
    }
}

fn append_stable_key(
    tag: u8,
    key: &StableElementKeyV1,
    output: &mut IdentityWriter,
) -> Result<(), IdentityCodecError> {
    output.push(tag)?;
    output.extend(&key.canonical_bytes()?)
}

/// Encode one constant, restricted to the five live scalar forms.
///
/// # Errors
/// Returns [`IdentityCodecError::InvalidConstantKind`] for enum or graph
/// references, or the applicable scalar codec failure.
pub fn encode_const_value_v1(
    value: &Value,
    output: &mut Vec<u8>,
) -> Result<(), IdentityCodecError> {
    let mut writer = IdentityWriter::new("ConstValueV1");
    match value {
        Value::Int(value) => encode_int(*value, &mut writer)?,
        Value::Currency(value) => encode_currency(value.micro_units(), &mut writer)?,
        Value::Real(value) => encode_real(*value, &mut writer)?,
        Value::Ratio { value, floor, cap } => {
            writer.push(0x04)?;
            writer.extend(&canonical_f64_bits(value.get())?.to_be_bytes())?;
            encode_ratio_option(*floor, &mut writer)?;
            encode_ratio_option(*cap, &mut writer)?;
        }
        Value::Bool(value) => {
            writer.push(0x05)?;
            writer.push(u8::from(*value))?;
        }
        Value::Enum { .. } | Value::NodeRef(_) | Value::HyperedgeRef(_) | Value::EdgeRef(_) => {
            return Err(IdentityCodecError::InvalidConstantKind)
        }
    }
    append_checked(output, "ConstValueV1 output", &writer.finish())
}

/// Encode one governed `BslTypeV1`.
///
/// # Errors
/// Returns an unknown-enum, semantic-string, conversion, byte, or allocation error.
pub fn encode_bsl_type_v1(
    value: &BslType,
    enums: &EnumRegistry,
    output: &mut Vec<u8>,
) -> Result<(), IdentityCodecError> {
    let mut writer = IdentityWriter::new("BslTypeV1");
    match value {
        BslType::Probability => writer.push(0x01)?,
        BslType::Intensity => writer.push(0x02)?,
        BslType::Coefficient => writer.push(0x03)?,
        BslType::Currency => writer.push(0x04)?,
        BslType::Real => writer.push(0x05)?,
        BslType::Int => writer.push(0x06)?,
        BslType::Bool => writer.push(0x07)?,
        BslType::Enum(id) => {
            let declaration = enums
                .declaration(*id)
                .ok_or(IdentityCodecError::UnknownEnumType { id: *id })?;
            validate_enum_type("BslTypeV1 enum type", &declaration.name)?;
            writer.push(0x08)?;
            writer.str32("BslTypeV1 enum type", &declaration.name)?;
        }
        BslType::NodeSet(member) => {
            validate_enum_member("BslTypeV1 NodeType member", member)?;
            writer.push(0x09)?;
            writer.str32("BslTypeV1 NodeType member", member)?;
        }
        BslType::EdgeSet(member) => {
            validate_enum_member("BslTypeV1 EdgeType member", member)?;
            writer.push(0x0a)?;
            writer.str32("BslTypeV1 EdgeType member", member)?;
        }
    }
    append_checked(output, "BslTypeV1 output", &writer.finish())
}

/// Return the governed `FieldKindV1` tag.
#[must_use]
pub const fn encode_field_kind_v1(value: FieldKind) -> u8 {
    match value {
        FieldKind::Intensive => 0x01,
        FieldKind::Extensive => 0x02,
        FieldKind::NotApplicable => 0x03,
    }
}

/// Return the governed `RuleRoleV1` tag.
#[must_use]
pub const fn encode_rule_role_v1(value: RuleRole) -> u8 {
    match value {
        RuleRole::Mechanic => 0x01,
        RuleRole::Recognizer => 0x02,
        RuleRole::ExternalEvent => 0x03,
        RuleRole::Intent => 0x04,
    }
}

/// Return the governed `EvidenceClassV1` tag.
#[must_use]
pub const fn encode_evidence_class_v1(value: EvidenceClass) -> u8 {
    match value {
        EvidenceClass::Observed => 0x01,
        EvidenceClass::Derived => 0x02,
        EvidenceClass::Calibrated => 0x03,
        EvidenceClass::Designed => 0x04,
    }
}

/// Return the governed `ShapeVerbV1` tag.
#[must_use]
pub const fn encode_shape_verb_v1(value: ShapeVerb) -> u8 {
    match value {
        ShapeVerb::AddNode => 0x01,
        ShapeVerb::RemoveNode => 0x02,
        ShapeVerb::AddEdge => 0x03,
        ShapeVerb::RemoveEdge => 0x04,
        ShapeVerb::AddHyperedge => 0x05,
        ShapeVerb::RemoveHyperedge => 0x06,
    }
}

/// Return the governed `EnumKindV1` tag.
#[must_use]
pub const fn encode_enum_kind_v1(value: EnumKind) -> u8 {
    match value {
        EnumKind::NodeType => 0x01,
        EnumKind::EdgeType => 0x02,
        EnumKind::HyperedgeType => 0x03,
        EnumKind::EventType => 0x04,
    }
}

/// Encode one governed `EffectSignatureV1`.
///
/// # Errors
/// Returns a semantic-string, conversion, byte, or allocation error.
pub fn encode_effect_signature_v1(
    value: &EffectSignature,
    output: &mut Vec<u8>,
) -> Result<(), IdentityCodecError> {
    let mut writer = IdentityWriter::new("EffectSignatureV1");
    match value {
        EffectSignature::NodeField(qname) => encode_effect_field(0x01, qname, &mut writer)?,
        EffectSignature::EdgeField(qname) => encode_effect_field(0x02, qname, &mut writer)?,
        EffectSignature::HyperedgeField(qname) => encode_effect_field(0x03, qname, &mut writer)?,
        EffectSignature::Event(event) => {
            let canonical = canonical_event_name_v1(event)?;
            writer.push(0x04)?;
            writer.str32("effect event", &canonical)?;
        }
        EffectSignature::Shape(verb) => {
            writer.push(0x05)?;
            writer.push(encode_shape_verb_v1(*verb))?;
        }
    }
    append_checked(output, "EffectSignatureV1 output", &writer.finish())
}

fn encode_effect_field(
    tag: u8,
    qname: &str,
    output: &mut IdentityWriter,
) -> Result<(), IdentityCodecError> {
    validate_qname("effect field", qname)?;
    output.push(tag)?;
    output.str32("effect field", qname)
}

/// Canonicalize a bare or full event name through the shared causal codec.
///
/// # Errors
/// Returns a semantic-string error for malformed event identities.
pub fn canonical_event_name_v1(value: &str) -> Result<String, IdentityCodecError> {
    let canonical = canonical_event_type(value).map_err(|_| IdentityCodecError::InvalidString {
        field: "event name",
        index: value.len(),
    })?;
    let member = canonical
        .strip_prefix("EventType/")
        .ok_or(IdentityCodecError::InvalidString {
            field: "event name",
            index: 0,
        })?;
    validate_enum_member("event member", member)?;
    Ok(canonical)
}

/// Decode an exact option-presence byte.
///
/// # Errors
/// Returns [`IdentityCodecError::InvalidOptionByte`] unless `value` is 0 or 1.
pub const fn decode_option_presence_v1(value: u8) -> Result<bool, IdentityCodecError> {
    match value {
        0 => Ok(false),
        1 => Ok(true),
        _ => Err(IdentityCodecError::InvalidOptionByte { value }),
    }
}

pub(crate) fn validate_symbol(field: &'static str, value: &str) -> Result<(), IdentityCodecError> {
    validate_segment(field, value, false)
}

pub(crate) fn validate_governance_text(
    field: &'static str,
    value: &str,
) -> Result<(), IdentityCodecError> {
    if value.len() <= MAX_GOVERNANCE_UTF8_BYTES_V1 {
        Ok(())
    } else {
        Err(IdentityCodecError::InvalidString {
            field,
            index: value.len(),
        })
    }
}

pub(crate) fn validate_qname(field: &'static str, value: &str) -> Result<(), IdentityCodecError> {
    if value.is_empty() || value.len() > 128 {
        return Err(IdentityCodecError::InvalidString {
            field,
            index: value.len(),
        });
    }
    let mut count = 0usize;
    for segment in value.split('/').take(5) {
        if count == 4 {
            return Err(IdentityCodecError::InvalidString {
                field,
                index: value.len(),
            });
        }
        validate_segment(field, segment, false)?;
        count = count.saturating_add(1);
    }
    Ok(())
}

pub(crate) fn validate_enum_type(
    field: &'static str,
    value: &str,
) -> Result<(), IdentityCodecError> {
    validate_segment(field, value, true)
}

pub(crate) fn validate_enum_member(
    field: &'static str,
    value: &str,
) -> Result<(), IdentityCodecError> {
    if value.is_empty() || value.len() > 64 {
        return Err(IdentityCodecError::InvalidString {
            field,
            index: value.len(),
        });
    }
    for (index, byte) in value.bytes().enumerate().take(64) {
        let valid = if index == 0 {
            byte.is_ascii_uppercase()
        } else {
            byte.is_ascii_uppercase() || byte.is_ascii_digit() || byte == b'_'
        };
        if !valid {
            return Err(IdentityCodecError::InvalidString { field, index });
        }
    }
    Ok(())
}

fn validate_segment(
    field: &'static str,
    value: &str,
    enum_type: bool,
) -> Result<(), IdentityCodecError> {
    if value.is_empty() || value.len() > 64 {
        return Err(IdentityCodecError::InvalidString {
            field,
            index: value.len(),
        });
    }
    for (index, byte) in value.bytes().enumerate().take(64) {
        let valid = if enum_type {
            if index == 0 {
                byte.is_ascii_uppercase()
            } else {
                byte.is_ascii_alphanumeric()
            }
        } else if index == 0 {
            byte.is_ascii_lowercase()
        } else {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-'
        };
        if !valid {
            return Err(IdentityCodecError::InvalidString { field, index });
        }
    }
    Ok(())
}

pub(crate) fn canonical_f64_bits(value: f64) -> Result<u64, IdentityCodecError> {
    if !value.is_finite() {
        return Err(IdentityCodecError::NonFiniteValue);
    }
    Ok(if value == 0.0 { 0 } else { value.to_bits() })
}

pub(crate) fn checked_u32(field: &'static str, value: usize) -> Result<u32, IdentityCodecError> {
    u32::try_from(value).map_err(|_| IdentityCodecError::IntegerConversion { field, value })
}

pub(crate) fn checked_add(
    field: &'static str,
    left: usize,
    right: usize,
) -> Result<usize, IdentityCodecError> {
    left.checked_add(right)
        .ok_or(IdentityCodecError::CapacityOverflow { field })
}

fn append_checked(
    output: &mut Vec<u8>,
    field: &'static str,
    value: &[u8],
) -> Result<(), IdentityCodecError> {
    let requested = checked_add(field, output.len(), value.len())?;
    if requested > MAX_IDENTITY_SECTION_BYTES_V1 {
        return Err(IdentityCodecError::ByteLimit {
            field,
            actual: requested,
            maximum: MAX_IDENTITY_SECTION_BYTES_V1,
        });
    }
    output
        .try_reserve_exact(value.len())
        .map_err(|_: TryReserveError| IdentityCodecError::Allocation { field, requested })?;
    output.extend_from_slice(value);
    Ok(())
}
