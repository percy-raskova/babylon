INSERT INTO babylon_state.economic_company_original_share_v1 (
    campaign_id, site_key, beneficiary_kind, beneficiary_id, original_shares, original_carrying_micros
)
SELECT e.campaign_id,
       (SELECT s.site_key FROM babylon_state.site_principal_v1 s
        WHERE (s.campaign_id,s.foundation_sha256,s.site_id)=(e.campaign_id,e.foundation_sha256,e.site_id)),
       e.beneficiary_kind, e.beneficiary_id, e.original_shares, e.original_carrying_micros
FROM jsonb_populate_recordset(NULL::babylon_state.economic_company_claim_source_v1,$1::text::jsonb) e
