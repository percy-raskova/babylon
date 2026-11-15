INSERT INTO babylon_state.economic_company_member_key_v1 (
    campaign_id, site_key, company_id, county_geoid, opening_employed, original_cash_micros,
    cash_floor_micros, swept_micros, original_capital_micros
)
SELECT e.campaign_id,
       (SELECT s.site_key FROM babylon_state.site_principal_v1 s
        WHERE (s.campaign_id,s.foundation_sha256,s.site_id)=(e.campaign_id,e.foundation_sha256,e.site_id)
          AND e.original_cash_micros=e.swept_micros+e.remaining_cash_micros
          AND e.original_capital_micros=e.swept_micros+e.remaining_capital_micros),
       e.company_id, e.county_geoid, e.opening_employed, e.original_cash_micros,
       e.cash_floor_micros, e.swept_micros, e.original_capital_micros
FROM jsonb_populate_recordset(NULL::babylon_state.economic_company_member_v1,$1::text::jsonb) e
