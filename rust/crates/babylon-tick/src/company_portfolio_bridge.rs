//! Transfer closed material evidence and the stamped BSL decision across the period boundary.
use crate::company_graph::{
    self, DEFER_WEIGHT, EVIDENCE_PERIOD, EVIDENCE_RULE, FIELDS, LARGER_WEIGHT, MODEST_WEIGHT,
    REPLACEMENT_WEIGHT, SELECTED_PORTFOLIO, SELECTION_PERIOD,
};
use crate::material_staffing::{self, MaterialStaffingError, StaffingEffectContext};
use babylon_bsl::causal_contract::{
    self, AuditReceipt, ContractError, EvidenceClass, RuleContract, RuleRole,
};
use babylon_bsl::structural_verbs::EffectExecutor;
use babylon_bsl::types::{BslType, FieldKind};
use babylon_bsl::write_log::CollectingWriteLog;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use babylon_material_circuit::{
    CompanyId, CompanyPortfolio, CompanyPortfolioEvidence, CompanyPortfolioRegister,
    CompanyPortfolioSelection,
};

pub(crate) const DECISION_RULE: &str = "company/portfolio-investment";
const WEIGHTS: [&str; 4] = [
    DEFER_WEIGHT,
    REPLACEMENT_WEIGHT,
    MODEST_WEIGHT,
    LARGER_WEIGHT,
];

/// Identifies the company whose graph carrier or investment decision failed validation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CompanyGraphError {
    Field(&'static str),
    Carrier {
        company: CompanyId,
        cause: MaterialStaffingError,
    },
    StaleEvidence {
        company: CompanyId,
        period: u64,
    },
    InadmissibleSelection {
        company: CompanyId,
        value: u64,
    },
    Audit(ContractError),
}

fn node(
    graph: &impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    company: CompanyId,
) -> Result<NodeId, CompanyGraphError> {
    let key = company_graph::company_key(context.resolver.scenario_scope(), company);
    material_staffing::resolve_node(graph, context, &key, "COMPANY")
        .map_err(|cause| CompanyGraphError::Carrier { company, cause })
}

fn validate_fields(context: StaffingEffectContext<'_>) -> Result<(), CompanyGraphError> {
    for field in FIELDS {
        if !context
            .types
            .fields
            .get(field)
            .is_some_and(|decl| decl.kind == FieldKind::Extensive && decl.ty == BslType::Int)
        {
            return Err(CompanyGraphError::Field(field));
        }
    }
    Ok(())
}

/// Read the selected alternative only from the completed graph and bind its input weights
/// to that same period's independently decoded material evidence.
pub(crate) fn selections(
    graph: &impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    register: &CompanyPortfolioRegister,
) -> Result<Vec<CompanyPortfolioSelection>, CompanyGraphError> {
    validate_fields(context)?;
    register
        .companies
        .iter()
        .map(|row| read_selection(graph, context, row))
        .collect()
}

fn read_selection(
    graph: &impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    row: &CompanyPortfolioEvidence,
) -> Result<CompanyPortfolioSelection, CompanyGraphError> {
    let company = row.company;
    let subject = node(graph, context, company)?;
    let read = |field| {
        material_staffing::read_stock(graph, subject, field, &context)
            .map_err(|cause| CompanyGraphError::Carrier { company, cause })
    };
    let stale = CompanyGraphError::StaleEvidence {
        company,
        period: row.period,
    };
    if read(EVIDENCE_PERIOD)? != row.period || read(SELECTION_PERIOD)? != row.period {
        return Err(stale);
    }
    for (field, weight) in WEIGHTS.into_iter().zip(row.weights) {
        if read(field)? != u64::from(weight) {
            return Err(stale);
        }
    }
    let value = read(SELECTED_PORTFOLIO)?;
    let index = u8::try_from(value)
        .ok()
        .filter(|v| row.weights.get(usize::from(*v)).is_some_and(|w| *w > 0));
    let portfolio = index
        .and_then(CompanyPortfolio::from_index)
        .ok_or(CompanyGraphError::InadmissibleSelection { company, value })?;
    Ok(CompanyPortfolioSelection {
        company,
        evidence_period: row.period,
        portfolio,
    })
}

/// Write through the same observed executor used by BSL so each native field has an audit receipt.
pub(crate) fn publish(
    graph: &mut impl GraphSubstrate,
    context: StaffingEffectContext<'_>,
    register: &CompanyPortfolioRegister,
) -> Result<Vec<AuditReceipt>, CompanyGraphError> {
    validate_fields(context)?;
    let mut log = CollectingWriteLog::new();
    {
        let mut executor =
            EffectExecutor::observed(context.types, context.enums, EVIDENCE_RULE, &mut log);
        for row in &register.companies {
            let company = row.company;
            let subject = node(graph, context, company)?;
            let values = WEIGHTS
                .into_iter()
                .zip(row.weights.map(u64::from))
                .chain(std::iter::once((EVIDENCE_PERIOD, row.period)));
            for (field, value) in values {
                let write = material_staffing::typed_write(subject, field, value)
                    .map_err(|cause| CompanyGraphError::Carrier { company, cause })?;
                executor
                    .apply_pending_write(&write, graph)
                    .map_err(|error| CompanyGraphError::Carrier {
                        company,
                        cause: error.into(),
                    })?;
            }
        }
    }
    let contract = RuleContract {
        rule_id: EVIDENCE_RULE.to_owned(),
        role: RuleRole::Mechanic,
        evidence: EvidenceClass::Derived,
    };
    causal_contract::reduce_audit_receipts(&contract, &[], &log.records)
        .map_err(CompanyGraphError::Audit)
}
