//! Compact shared recipes and household needs; no site gets its own template copy.
use super::{NationalOpeningError, Result, FUNCTIONS};
use crate::economic_catalog::{
    CommodityAmount, CommodityLabel, HouseholdNeedCoefficient, HouseholdTemplate,
    HouseholdTemplateId, LaborRequirement, RecipeTemplate, RecipeTemplateId,
};
use crate::national_economy::NationalGamePolicy;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_material_circuit::{CommodityDefinition, UnitId};

type Templates = (
    Vec<CommodityDefinition>,
    Vec<CommodityLabel>,
    Vec<RecipeTemplate>,
    Vec<HouseholdTemplate>,
);

pub(super) fn recipe_id(function: EconomicFunction) -> Result<RecipeTemplateId> {
    let index = FUNCTIONS
        .iter()
        .position(|f| *f == function)
        .ok_or(NationalOpeningError::Policy)?;
    Ok(RecipeTemplateId(
        u16::try_from(index + 1).map_err(|_| NationalOpeningError::Arithmetic)?,
    ))
}

pub(super) fn compile(policy: &NationalGamePolicy, unit: UnitId) -> Result<Templates> {
    let commodities = policy
        .commodities
        .values()
        .map(|g| CommodityDefinition {
            good_id: g.good_id,
            unit_id: g.unit_id,
            kind: g.kind,
        })
        .collect();
    let labels = policy
        .commodities
        .iter()
        .map(|(key, g)| CommodityLabel {
            good_id: g.good_id,
            unit_id: g.unit_id,
            key: key.clone(),
            label: g.label.clone(),
            unit_label: g.unit_label.clone(),
        })
        .collect();
    let recipes = policy
        .recipes
        .iter()
        .map(|(function, recipe)| {
            Ok(RecipeTemplate {
                id: recipe_id(*function)?,
                output: commodity(policy, &recipe.output, recipe.output_units_per_batch)?,
                inputs: recipe
                    .inputs
                    .iter()
                    .map(|(key, n)| commodity(policy, key, *n))
                    .collect::<Result<Vec<_>>>()?,
                labor: Some(LaborRequirement {
                    unit_id: unit,
                    hours_per_batch: recipe.labor_hours_per_batch,
                }),
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let needs = policy
        .household_needs
        .iter()
        .map(|n| {
            let good = policy
                .commodities
                .get(&n.key)
                .ok_or(NationalOpeningError::Policy)?;
            Ok(HouseholdNeedCoefficient {
                good_id: good.good_id,
                unit_id: good.unit_id,
                basis: n.basis,
                units_per_basis: n.units_per_basis,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    Ok((
        commodities,
        labels,
        recipes,
        vec![HouseholdTemplate {
            id: HouseholdTemplateId(1),
            needs,
        }],
    ))
}
fn commodity(policy: &NationalGamePolicy, key: &str, quantity: u64) -> Result<CommodityAmount> {
    let good = policy
        .commodities
        .get(key)
        .ok_or(NationalOpeningError::Policy)?;
    if quantity == 0 {
        return Err(NationalOpeningError::Policy);
    }
    Ok(CommodityAmount {
        good_id: good.good_id,
        unit_id: good.unit_id,
        quantity,
    })
}
