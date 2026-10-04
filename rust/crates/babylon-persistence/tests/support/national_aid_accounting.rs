//! Independent aid accounting checks over authenticated complete committed receipts.
use babylon_material_circuit::{
    AccountId, AidOutcome, AidReceipt, MoneyLocation, MoneyTransferPurpose,
};
use babylon_persistence::{
    identity::CampaignId,
    observer_reader::{CommittedMaterialReceipts, ObserverEconomyReader},
    runtime_session::{
        OrganizerChoice, OrganizerCommitment, OrganizerMaterialAidPreview, OrganizerSnapshot,
    },
};
use babylon_practice_contract::{OrganizerOutcome, OrganizerPartnerResponse};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};

type Totals = BTreeMap<[u8; 32], (u64, i128, i128)>;
type Movement = (MoneyTransferPurpose, MoneyLocation, MoneyLocation, i128);

#[derive(Default)]
pub(super) struct Audit {
    commands: Vec<(OrganizerCommitment, OrganizerMaterialAidPreview)>,
    dispatched: Totals,
    settled: Totals,
    facts: Vec<serde_json::Value>,
    completed_practices: BTreeSet<[u8; 32]>,
    terminal_practices: BTreeSet<[u8; 32]>,
}
impl Audit {
    pub(super) fn accept(&mut self, commitment: &OrganizerCommitment, before: &OrganizerSnapshot) {
        let kind = match commitment.command.choice {
            OrganizerChoice::RemoteAid => {
                babylon_persistence::runtime_session::OrganizerAidKind::Remote
            }
            OrganizerChoice::LocalAid => {
                babylon_persistence::runtime_session::OrganizerAidKind::Local
            }
            _ => panic!("only actual aid commitments are audited"),
        };
        let preview = before.aid.iter().find(|p| p.kind == kind).unwrap().clone();
        self.commands.push((commitment.clone(), preview));
    }
    pub(super) fn read(
        &mut self,
        admitted: &CommittedMaterialReceipts,
        campaign: CampaignId,
        tick: u64,
        after: &OrganizerSnapshot,
        committed_hash: &str,
    ) -> babylon_tick::material_replay::IdentifiedMaterialTick {
        assert_eq!(admitted.campaign_id, campaign);
        assert_eq!(
            hex(admitted.identity.tick_content_hash().as_bytes()),
            committed_hash
        );
        assert_eq!(admitted.receipts.resolve_tick, tick);
        check_period(&admitted.receipts);
        let mut selected = Vec::new();
        for r in &admitted.receipts.aid {
            let Some((command, preview)) = self.commands.iter().find(|(c, p)| {
                p.mandate_id == r.mandate_id && c.resolves_period == r.dispatch_period
            }) else {
                panic!("material aid must join an actual submitted original command")
            };
            assert_eq!(
                r.commitment_id,
                babylon_material_circuit::aid_commitment_id(
                    preview.mandate_id,
                    command.resolves_period
                )
            );
            assert_eq!(r.donor.as_bytes(), preview.donor_id);
            assert_eq!(r.recipient.as_bytes(), preview.recipient_id);
            assert_eq!(r.good_id.as_bytes(), preview.good_id);
            assert_eq!(r.unit_id.as_bytes(), preview.unit_id);
            assert_eq!(r.payer, organization_payer());
            assert_eq!(r.period, tick);
            assert!(r.quantity > 0 && r.quantity <= preview.maximum_quantity);
            let cash = i128::from(r.quantity)
                .checked_mul(preview.gift_cash_per_unit)
                .unwrap();
            let fulfillment = r
                .quantity
                .checked_mul(preview.fulfillment_hours_per_unit)
                .unwrap();
            let uses_time = r.outcome == AidOutcome::Dispatched
                || (r.outcome == AidOutcome::Granted && r.dispatch_period == tick);
            assert_eq!(
                r.contribution_hours,
                if uses_time { fulfillment } else { 0 }
            );
            assert_eq!(
                r.cash_amount.micro_units(),
                if r.outcome == AidOutcome::Requested {
                    0
                } else {
                    cash
                }
            );
            let key = r.commitment_id.as_bytes();
            if uses_time {
                add_total(&mut self.dispatched, key, r);
            }
            if matches!(r.outcome, AidOutcome::Granted | AidOutcome::Lost) {
                add_total(&mut self.settled, key, r);
            }
            if let Some((q, c, v)) = self.settled.get(&key) {
                let (dq, dc, dv) = self.dispatched.get(&key).unwrap();
                assert!(
                    q <= dq && c <= dc && v <= dv,
                    "no quantity/cash/carrying creation across arrival/loss"
                );
                if q == dq {
                    assert_eq!((c, v), (dc, dv));
                }
            }
            let residual = check_time(admitted, r, command, after);
            selected.push(serde_json::json!({"original_commitment":command.commitment_id,"mandate":r.mandate_id,"dispatch_period":r.dispatch_period,
                "outcome":format!("{:?}",r.outcome),"quantity":r.quantity,"cash_micros":r.cash_amount.micro_units().to_string(),
                "carrying_micros":r.carrying_amount.micro_units().to_string(),"fulfillment_hours":r.contribution_hours,"remaining_shared_hours":residual}));
        }
        let practices = self.check_practices(admitted, after);
        self.facts.push(serde_json::json!({"period":tick,"tick_content_hash":hex(admitted.identity.tick_content_hash().as_bytes()),"canonical_receipt_sha256":hex(&admitted.identity.receipt_digest()),"selected_aid":selected,"independent_practices":practices}));
        admitted.identity
        // The caller releases full typed vectors after this independent audit.
    }
    fn check_practices(
        &mut self,
        admitted: &babylon_persistence::observer_reader::CommittedMaterialReceipts,
        after: &OrganizerSnapshot,
    ) -> Vec<serde_json::Value> {
        let tick = admitted.receipts.resolve_tick;
        let mut facts = Vec::new();
        let mut seen = BTreeSet::new();
        for resolution in &after.aid_resolutions {
            let original = resolution.pending.original_commitment_id;
            assert!(
                seen.insert(original),
                "one resolution per original command and period"
            );
            let (command, preview) = self
                .commands
                .iter()
                .find(|(c, p)| {
                    c.commitment_id == original && p.mandate_id == resolution.pending.mandate_id
                })
                .unwrap();
            let consumed = check_practice_identity(resolution, command, preview, tick);
            let recipient = match command.command.choice {
                OrganizerChoice::LocalAid => 2_616_302,
                OrganizerChoice::RemoteAid => 1_703_101,
                _ => unreachable!(),
            };
            let practice = &resolution.practice;
            if practice.outcome == OrganizerOutcome::AidAwaitingSupport {
                assert!(practice.time_use.is_empty());
                assert_eq!(
                    practice.partner_response,
                    OrganizerPartnerResponse::NotRequested
                );
                assert!(practice.partner_actor_id.is_none());
                assert!(!consumed);
            } else {
                assert!(
                    self.terminal_practices.insert(original),
                    "terminal practice cannot resolve twice"
                );
                if consumed {
                    assert_eq!(practice.partner_actor_id, Some(recipient));
                }
            }
            if practice.outcome == OrganizerOutcome::AidPracticeCompleted {
                assert!(consumed);
                assert_eq!(
                    practice.partner_response,
                    OrganizerPartnerResponse::Participated
                );
                assert_eq!(practice.hours_spent, 2);
                assert_eq!(practice.time_use.len(), 2);
                assert_eq!(
                    practice
                        .time_use
                        .iter()
                        .map(|u| (u.actor_id, u.contributor_id, u.hours))
                        .collect::<BTreeSet<_>>(),
                    BTreeSet::from([(2_616_301, 2_616_301, 2), (recipient, recipient, 2)])
                );
                assert!(self.completed_practices.insert(original));
            } else if practice.outcome == OrganizerOutcome::InsufficientTime {
                assert!(practice.time_use.is_empty());
            } else if practice.outcome == OrganizerOutcome::AidPracticeUncompleted {
                assert!(!practice.time_use.iter().any(|u| u.actor_id == recipient));
                assert_ne!(
                    practice.partner_response,
                    OrganizerPartnerResponse::Participated
                );
            }
            check_support_receipts(admitted, resolution);
            let recipient_hours = check_practice_debits(admitted, resolution, preview, recipient);
            facts.push(serde_json::json!({"original_commitment":original,"mandate":preview.mandate_id,
                "dispatch_period":command.resolves_period,"period":tick,"consumed_support":consumed,
                "partner_actor":practice.partner_actor_id,"partner_response":practice.partner_response,
                "outcome":practice.outcome,"recipient_debited_hours":recipient_hours,
                "finite_practice_completed":practice.outcome==OrganizerOutcome::AidPracticeCompleted}));
        }
        facts
    }
    pub(super) fn practice_report(&self) -> serde_json::Value {
        serde_json::json!({"status":if self.commands.len()==2 && self.completed_practices.len()==2 {"passed"} else {"incomplete"},
            "completed_original_commands":self.completed_practices,"terminal_original_commands":self.terminal_practices,
            "basis":"actual_consumed_support_independent_partner_response_and_authenticated_finite_debits"})
    }
    pub(super) fn report(&self) -> serde_json::Value {
        serde_json::json!({"cash_and_in_kind_postings":"passed","accepted_original_commands":self.commands.len(),"time_partition_and_residual_bound":"passed",
            "exact_final_contribution_debit_ledger":"passed","periods":self.facts})
    }
}
fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut result = String::with_capacity(bytes.len().checked_mul(2).unwrap());
    for byte in bytes {
        write!(&mut result, "{byte:02x}").unwrap();
    }
    result
}
fn add_total(map: &mut Totals, key: [u8; 32], row: &AidReceipt) {
    let entry = map.entry(key).or_default();
    entry.0 = entry.0.checked_add(row.quantity).unwrap();
    entry.1 = entry.1.checked_add(row.cash_amount.micro_units()).unwrap();
    entry.2 = entry
        .2
        .checked_add(row.carrying_amount.micro_units())
        .unwrap();
}
fn check_period(receipts: &MaterialTickReceipts) {
    check_cash(receipts);
    let mut gifts = BTreeMap::<AccountId, (i128, i128)>::new();
    let mut losses = BTreeMap::<AccountId, i128>::new();
    for row in &receipts.aid {
        assert!(row.carrying_amount.micro_units() >= 0);
        if matches!(row.outcome, AidOutcome::Requested | AidOutcome::Unshipped) {
            assert_eq!(row.carrying_amount.micro_units(), 0);
        }
        if row.outcome == AidOutcome::Lost {
            let entry = losses.entry(AccountId::Household(row.donor)).or_default();
            *entry = entry
                .checked_add(row.carrying_amount.micro_units())
                .unwrap();
        }
        if row.outcome == AidOutcome::Granted {
            let carrying = row.carrying_amount.micro_units();
            let cash = row.cash_amount.micro_units();
            add_gift(&mut gifts, AccountId::Household(row.donor), carrying, 0);
            add_gift(&mut gifts, row.payer, cash, 0);
            add_gift(
                &mut gifts,
                AccountId::Household(row.recipient),
                0,
                carrying.checked_add(cash).unwrap(),
            );
            let consumption = receipts
                .household_consumption
                .iter()
                .find(|c| {
                    c.principal_id == row.recipient
                        && c.good_id == row.good_id
                        && c.unit_id == row.unit_id
                })
                .unwrap();
            assert_eq!(consumption.period, receipts.resolve_tick);
            assert_eq!(
                consumption
                    .consumed_quantity
                    .checked_add(consumption.unmet_quantity)
                    .unwrap(),
                consumption.required_quantity
            );
            assert_eq!(
                consumption
                    .consumed_quantity
                    .checked_add(consumption.closing_quantity)
                    .unwrap(),
                consumption.available_quantity
            );
            assert!(
                consumption.available_quantity >= row.quantity,
                "gift units must enter actual recipient pantry before consumption"
            );
        }
    }
    for (account, (expense, income)) in gifts {
        let rows: Vec<_> = receipts
            .income
            .iter()
            .filter(|r| r.account == account)
            .collect();
        assert_eq!(rows.len(), 1);
        let row = rows[0];
        assert_eq!(row.period, receipts.resolve_tick);
        assert_eq!(row.statement.gift_expense.micro_units(), expense);
        assert_eq!(row.statement.gift_income.micro_units(), income);
    }
    for (account, amount) in losses {
        let income = receipts
            .income
            .iter()
            .find(|r| r.account == account)
            .unwrap();
        assert_eq!(income.statement.freight_loss_expense.micro_units(), amount);
    }
    for transfer in &receipts.money_transfers {
        if let MoneyTransferPurpose::AidReservation(id)
        | MoneyTransferPurpose::AidGrant(id)
        | MoneyTransferPurpose::AidRefund(id) = transfer.purpose
        {
            assert!(
                receipts
                    .aid
                    .iter()
                    .any(|r| r.commitment_id == id && r.outcome != AidOutcome::Requested),
                "no unjoined aid cash posting"
            );
        }
    }
}
fn add_gift(
    map: &mut BTreeMap<AccountId, (i128, i128)>,
    account: AccountId,
    expense: i128,
    income: i128,
) {
    let row = map.entry(account).or_default();
    row.0 = row.0.checked_add(expense).unwrap();
    row.1 = row.1.checked_add(income).unwrap();
}
fn check_cash(receipts: &MaterialTickReceipts) {
    let mut expected = BTreeMap::<(u8, [u8; 32]), Movement>::new();
    for row in &receipts.aid {
        let id = row.commitment_id;
        let mut movements = Vec::new();
        if row.period == row.dispatch_period
            && matches!(
                row.outcome,
                AidOutcome::Dispatched | AidOutcome::Granted | AidOutcome::Unshipped
            )
        {
            movements.push((
                1,
                MoneyTransferPurpose::AidReservation(id),
                MoneyLocation::Cash(row.payer),
                MoneyLocation::AidReserve(id),
            ));
        }
        match row.outcome {
            AidOutcome::Granted => movements.push((
                2,
                MoneyTransferPurpose::AidGrant(id),
                MoneyLocation::AidReserve(id),
                MoneyLocation::Cash(AccountId::Household(row.recipient)),
            )),
            AidOutcome::Lost | AidOutcome::Unshipped => movements.push((
                3,
                MoneyTransferPurpose::AidRefund(id),
                MoneyLocation::AidReserve(id),
                MoneyLocation::Cash(row.payer),
            )),
            _ => {}
        }
        for (tag, purpose, debit, credit) in movements {
            let entry = expected
                .entry((tag, id.as_bytes()))
                .or_insert((purpose, debit, credit, 0));
            assert_eq!((entry.0, entry.1, entry.2), (purpose, debit, credit));
            entry.3 = entry.3.checked_add(row.cash_amount.micro_units()).unwrap();
        }
    }
    for (_, (purpose, debit, credit, amount)) in expected {
        let transfers: Vec<_> = receipts
            .money_transfers
            .iter()
            .filter(|t| t.purpose == purpose)
            .collect();
        assert!(!transfers.is_empty());
        let mut actual = 0_i128;
        for t in transfers {
            assert_eq!(t.debit.location, debit);
            assert_eq!(t.credit.location, credit);
            assert!(t.credit.delta.micro_units() > 0);
            assert_eq!(
                t.debit.delta.micro_units(),
                t.credit.delta.micro_units().checked_neg().unwrap()
            );
            actual = actual.checked_add(t.credit.delta.micro_units()).unwrap();
        }
        assert_eq!(actual, amount);
    }
}
fn organization_payer() -> AccountId {
    use sha2::{Digest, Sha256};
    AccountId::Organization(babylon_material_circuit::OrganizationAccountId::from_bytes(
        Sha256::digest(b"NationalWayneAidOrganizationV1\0").into(),
    ))
}
fn check_time(
    admitted: &babylon_persistence::observer_reader::CommittedMaterialReceipts,
    r: &AidReceipt,
    command: &OrganizerCommitment,
    after: &OrganizerSnapshot,
) -> Option<u64> {
    let tick = admitted.receipts.resolve_tick;
    let key = r.commitment_id.as_bytes();
    let uses_time = r.contribution_hours > 0;
    let time = admitted
        .receipts
        .household_time
        .iter()
        .find(|t| t.principal_id == r.donor)
        .unwrap();
    time.validate().unwrap();
    assert!(r.contribution_hours <= time.contribution_available_hours);
    let residual = after
        .aid
        .iter()
        .find(|p| p.donor_id == r.donor.as_bytes())
        .and_then(|p| p.time.as_ref())
        .map(|t| t.remaining_hours);
    let debits: Vec<_> = admitted
        .household_contributions
        .iter()
        .filter(|d| d.contribution.use_id == key)
        .collect();
    if uses_time {
        assert_eq!(
            debits.len(),
            1,
            "fulfillment must debit shared time exactly once"
        );
        let debit = debits[0];
        assert_eq!(debit.period, tick);
        assert_eq!(debit.contribution.principal_id, r.donor);
        assert_eq!(debit.contribution.actor_id, command.command.actor_id);
        assert_eq!(debit.contribution.contributor_id, 2_616_301);
        assert_eq!(debit.contribution.hours, r.contribution_hours);
    } else if r.dispatch_period < tick {
        assert!(
            debits.is_empty(),
            "arrival/loss/refund cannot repeat dispatch time"
        );
    }
    let total = admitted
        .household_contributions
        .iter()
        .filter(|d| d.contribution.principal_id == r.donor)
        .fold(0_u64, |sum, d| {
            assert_eq!(d.period, tick);
            sum.checked_add(d.contribution.hours).unwrap()
        });
    let remaining = time
        .contribution_available_hours
        .checked_sub(total)
        .unwrap();
    if let Some(residual) = residual {
        assert_eq!(residual, remaining, "all aliases share one debited ledger");
    }
    residual
}
pub(super) fn observer() -> ObserverEconomyReader {
    let config: postgres::Config = std::env::var("BABYLON_NATIONAL_STORAGE_OBSERVER_DSN")
        .unwrap()
        .parse()
        .unwrap();
    ObserverEconomyReader::connect(
        &config,
        babylon_persistence::observer_reader::ObserverVisibility::FullObserver,
    )
    .unwrap()
}
fn check_practice_debits(
    admitted: &babylon_persistence::observer_reader::CommittedMaterialReceipts,
    resolution: &babylon_persistence::runtime_session::OrganizerAidResolution,
    preview: &OrganizerMaterialAidPreview,
    recipient: u64,
) -> u64 {
    use sha2::{Digest, Sha256};
    for actor in [2_616_301, recipient] {
        let mut bytes = b"babylon.organizer-household-contribution.v1\0".to_vec();
        bytes.extend_from_slice(&resolution.practice.receipt_id);
        bytes.extend_from_slice(&actor.to_be_bytes());
        bytes.extend_from_slice(&actor.to_be_bytes());
        let id: [u8; 32] = Sha256::digest(bytes).into();
        let recorded = admitted
            .household_contributions
            .iter()
            .filter(|d| d.contribution.use_id == id)
            .count();
        let declared = resolution
            .practice
            .time_use
            .iter()
            .filter(|u| u.actor_id == actor && u.contributor_id == actor)
            .count();
        assert_eq!(
            recorded, declared,
            "no undeclared partner or donor practice debit"
        );
    }
    let mut recipient_hours = 0_u64;
    let mut seen = BTreeSet::new();
    for usage in &resolution.practice.time_use {
        assert!(usage.hours > 0);
        assert!(seen.insert((usage.actor_id, usage.contributor_id)));
        let principal = if usage.actor_id == 2_616_301 {
            assert_eq!(usage.contributor_id, 2_616_301);
            preview.donor_id
        } else {
            assert_eq!(usage.actor_id, recipient);
            assert_eq!(usage.contributor_id, recipient);
            recipient_hours = recipient_hours.checked_add(usage.hours).unwrap();
            preview.recipient_id
        };
        let mut bytes = b"babylon.organizer-household-contribution.v1\0".to_vec();
        bytes.extend_from_slice(&resolution.practice.receipt_id);
        bytes.extend_from_slice(&usage.actor_id.to_be_bytes());
        bytes.extend_from_slice(&usage.contributor_id.to_be_bytes());
        let use_id: [u8; 32] = Sha256::digest(bytes).into();
        let matches: Vec<_> = admitted
            .household_contributions
            .iter()
            .filter(|d| d.contribution.use_id == use_id)
            .collect();
        assert_eq!(matches.len(), 1);
        let debit = matches[0];
        assert_eq!(debit.period, resolution.practice.period);
        assert_eq!(debit.contribution.principal_id.as_bytes(), principal);
        assert_eq!(
            (
                debit.contribution.actor_id,
                debit.contribution.contributor_id,
                debit.contribution.hours
            ),
            (usage.actor_id, usage.contributor_id, usage.hours)
        );
        let gross = admitted
            .receipts
            .household_time
            .iter()
            .find(|t| t.principal_id.as_bytes() == principal)
            .unwrap();
        gross.validate().unwrap();
        assert!(gross.contribution_available_hours > 0);
        let used = admitted
            .household_contributions
            .iter()
            .filter(|d| d.contribution.principal_id.as_bytes() == principal)
            .fold(0_u64, |sum, d| {
                assert_eq!(d.period, gross.period);
                sum.checked_add(d.contribution.hours).unwrap()
            });
        assert!(used <= gross.contribution_available_hours);
    }
    recipient_hours
}
fn check_practice_identity(
    resolution: &babylon_persistence::runtime_session::OrganizerAidResolution,
    command: &OrganizerCommitment,
    preview: &OrganizerMaterialAidPreview,
    tick: u64,
) -> bool {
    let original = command.commitment_id;
    assert_eq!(resolution.pending.dispatch_period, command.resolves_period);
    assert_eq!(
        resolution.pending.admitted_period,
        command.command.expected_period
    );
    assert_eq!(resolution.support.original_commitment_id, original);
    assert_eq!(resolution.support.period, tick);
    assert_eq!(resolution.practice.commitment_id, Some(original));
    assert_eq!(resolution.practice.period, tick);
    assert_eq!(resolution.practice.choice, command.command.choice);
    assert_eq!(resolution.practice.actor_id, command.command.actor_id);
    assert!(resolution.practice.contact_product_id.is_none());
    let consumed = matches!(resolution.support.status,
                babylon_persistence::runtime_session::OrganizerAidSupportStatus::Granted { consumed_quantity, .. } if consumed_quantity > 0);
    assert_eq!(resolution.support.mandate_id, preview.mandate_id);
    assert_eq!(resolution.support.dispatch_period, command.resolves_period);
    assert_eq!(
        resolution.support.recipient_principal_id,
        preview.recipient_id
    );
    assert_eq!(resolution.support.good_id, preview.good_id);
    assert_eq!(resolution.support.unit_id, preview.unit_id);
    assert_eq!(
        resolution.support.material_commitment_id,
        babylon_material_circuit::aid_commitment_id(preview.mandate_id, command.resolves_period)
            .as_bytes()
    );
    assert!(matches!(
        resolution.practice.outcome,
        OrganizerOutcome::AidAwaitingSupport
            | OrganizerOutcome::AidNotProvisioned
            | OrganizerOutcome::AidPracticeCompleted
            | OrganizerOutcome::AidPracticeUncompleted
            | OrganizerOutcome::InsufficientTime
    ));
    if resolution.practice.outcome == OrganizerOutcome::AidNotProvisioned {
        assert!(!consumed);
        assert!(resolution.practice.time_use.is_empty());
    }
    consumed
}
fn check_support_receipts(
    admitted: &babylon_persistence::observer_reader::CommittedMaterialReceipts,
    resolution: &babylon_persistence::runtime_session::OrganizerAidResolution,
) {
    let support = &resolution.support;
    let granted = admitted
        .receipts
        .aid
        .iter()
        .filter(|r| {
            r.commitment_id.as_bytes() == support.material_commitment_id
                && r.outcome == AidOutcome::Granted
        })
        .fold(0_u64, |sum, r| sum.checked_add(r.quantity).unwrap());
    if let babylon_persistence::runtime_session::OrganizerAidSupportStatus::Granted {
        granted_quantity,
        consumed_quantity,
    } = support.status
    {
        assert!(granted > 0);
        assert_eq!(granted, granted_quantity);
        let consumed = admitted
            .receipts
            .household_consumption
            .iter()
            .filter(|r| {
                r.principal_id.as_bytes() == support.recipient_principal_id
                    && r.good_id.as_bytes() == support.good_id
                    && r.unit_id.as_bytes() == support.unit_id
            })
            .fold(0_u64, |sum, r| {
                assert_eq!(r.period, support.period);
                sum.checked_add(r.consumed_quantity).unwrap()
            });
        assert_eq!(consumed, consumed_quantity);
    } else {
        assert_eq!(granted, 0);
    }
}
