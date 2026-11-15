# National household lifecycle and trade comparison

Use Superpowers subagent-driven development for this implementation. The Director selected the national household lifecycle as the first playable change and a disrupted trade crossing as the next comparison.

## Goal

Let a household's changing population alter the next period's needs and available time. Show how actual wages, transfers, purchases, service delivery and unpaid provisioning sustain that household. Compare ordinary trade with a disruption after the lifecycle reaches the national campaign.

## Design

Use Babylon's [D–P–D′ design](../../concepts/dpd-lifecycle-circuit.rst) and its companion P–D–P′ circuit. Use the same principal for the demographics, consumption and time of each household budget. Group quarters keep their own budget and zero ordinary households. Employment remains attached to the existing worker member and wage payee. A new eligible resident can enter the labor pool only through a recorded participation and staffing transition.

The existing four-county rule operates on fractional phase populations. Connect whole-person demographic positions to national receipts and restart. Preserve counts at the boundary between the two models. National phase exposures use age as a declared proxy. The 16-plus household time boundary crosses the dependent phase, and a resident can continue to work beyond 65.

## Implementation and verification

- [x] Capture county ages in the national opening.

Build `national_age_reference_2024.csv.gz` from Census B01001 and the project's B01003 and B23025 controls. Check all 3,144 domestic FIPS, sex and age sums, the 15–17 split and total persons per county. Record units, provenance and derivations. Apportion each county total across its household budgets while preserving persons and age-16-plus margins. Capture those bytes and fold the counts with their geography. Identify the source or Designed policy for each foreign market and US dependency.

- [x] Advance a household with the material circuit.

Begin with a two-close test. Record opening and closing populations under 16, aged 16–17, aged 18–64 and aged 65 or more. Record births, deaths and transfers. Give each rate a denominator and four-week unit, and carry integer remainders.

Every surviving opening resident crosses the top of their age band within its duration. A child born during play reaches 16 after 208 completed intervals. Later birthdays keep their due dates. Include a small cohort, a mixed-age group and group quarters.

- [x] Use the closing population for the next period's needs and eligibility.

Compute food needs per person and housing needs per household. Check next-period purchasing limits and time eligibility. Bound employer attendance by the living workforce and available cash. Reconcile member removals, inactivity and wage payees at close. Join actual transfers, fulfilled services and unpaid provisioning on the household receipt. Report unmet need and unfunded claims separately.

- [x] Admit and restore the national campaign.

Bind source data, rules, rates, demographic positions and receipt versions into campaign identity. Follow a household across two closes in the authenticated observer. Exercise missing and malformed inputs, receipt corruption, interrupted commit and restart. Preserve the reader permissions on public finances and household data.

Two committed Wayne receipts matched the paid amounts in the journal. A new client and runtime opened the second close. The restricted reader received no household report. [Wayne period-2 receipt](../../../reports/economic-flows-qualification-2026-11-14-assets/wayne-household-period-2-v10.json) · [Native screen](../../../reports/economic-flows-qualification-2026-11-14-assets/wayne-household-period-2-v10.png)

- [x] Compare years five and twenty against the fixed-population control.

Use thirteen four-week periods per year. Across a closed geography, check that population equals opening plus births less deaths and that all age transfers balance. Reopen at 65 and 260 and compare state and receipt identities. Trace needs and eligible hours into the next period. Compare these results with ordinary seed 319 for output, consumption, unmet need, wages, taxes and investment. Record the observed direction of each change.

- [x] Test a dated disruption on a crossing with paid international freight.

Change only unreserved freight capacity in the comparison. Honor bookings in transit. Follow dispatch, arrival, settlement or refund and the buyer's next input or consumption receipt. Document the political decision and acting parties before introducing a named conflict to ordinary play.

The [national economic report](../../../reports/economic-flows-qualification-2026-11-14.md) holds the executable baseline and qualification results. The [original lifecycle specification](../../../specs/030-dpd-lifecycle-circuit/spec.md) also covers class reproduction, old-age security, inheritance and ideological transmission. The first national receipt measures the demographic and material support it can trace. A generic household grant cannot stand in for a documented pension.
