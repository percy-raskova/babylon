-- Restore 2824cf38e in the task-owned disposable source clone only.
-- CASCADE removes the current views, indexes and foreign keys on these derived rows.
DROP TABLE
    babylon_state.company_accounting_checkpoint_v1,
    babylon_state.company_accounting_period_v1,
    babylon_state.company_elimination_v1,
    babylon_state.company_realization_entry_v1,
    babylon_state.company_statement_balance_v1,
    babylon_state.company_statement_cash_flow_v1,
    babylon_state.company_statement_income_v1,
    babylon_state.economic_company_claim_source_v1,
    babylon_state.economic_company_claim_v1,
    babylon_state.economic_company_member_v1,
    babylon_state.economic_company_v1,
    babylon_state.economic_flow_account_v1,
    babylon_state.economic_flow_location_v1,
    babylon_state.economic_payment_v1,
    babylon_state.labor_checkpoint_v1,
    babylon_state.labor_movement_v1,
    babylon_state.labor_node_v1,
    babylon_state.labor_period_v1,
    babylon_state.labor_position_v1,
    babylon_state.money_journal_period_v1,
    babylon_state.money_movement_total_v1,
    babylon_state.money_movement_v1,
    babylon_state.site_statement_v1,
    babylon_state.site_stock_balance_v1 CASCADE;

ALTER TABLE babylon_state.material_tick_v3
    DROP CONSTRAINT material_tick_v3_receipt_storage_bytes_check,
    ADD CONSTRAINT material_tick_v3_receipt_storage_bytes_check
        CHECK (octet_length(receipt_storage_bytes) <= 925437040);

UPDATE babylon_meta.current_schema
SET schema_sha256 = decode('f984e7ee59fa650fc470f884b4663a6fc773c44ed4494254727273e50093d071', 'hex');
