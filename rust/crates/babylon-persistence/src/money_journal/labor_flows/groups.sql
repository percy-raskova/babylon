-- $1 campaign, $2/$3 current window, $4/$5 comparison, $6 grouping, $7 focus,
-- $8 page offset, $9 viewport, $10 previously grouped history, $11/$12 one
-- authenticated historical period's nodes and movements, $13 operation, $14 historical tick.
-- $15 specifies the focus dimension independently of the rank dimension.
-- $16/$17/$18 select a particular peer dimension, key and direction for geographic detail.
WITH windows(first_tick,last_tick,comparison) AS (
    SELECT $2::bigint,$3::bigint,false
    UNION ALL SELECT $4::bigint,$5::bigint,true WHERE $4 IS NOT NULL
), bounds AS (
    SELECT ($9::double precision[])[1] AS west, ($9::double precision[])[2] AS south,
           ($9::double precision[])[3] AS east, ($9::double precision[])[4] AS north
), envelopes AS (
    SELECT public.ST_MakeEnvelope(west,south,east,north,4269) AS area FROM bounds WHERE west<=east
    UNION ALL SELECT public.ST_MakeEnvelope(west,south,180,north,4269) FROM bounds WHERE west>east
    UNION ALL SELECT public.ST_MakeEnvelope(-180,south,east,north,4269) FROM bounds WHERE west>east
), visible AS (
    SELECT DISTINCT l.location_key FROM public.v_observer_economic_flow_location_v1 l
    JOIN envelopes e ON public.ST_Covers(e.area,l.county_internal_point) WHERE l.campaign_id=$1
), nodes AS (
    SELECT resolve_tick,node_ordinal,kind,entity_id,purpose,scope_kind,scope_id,
           location_key,catchment_key,industry_key,industry_label,longitude,latitude
    FROM public.v_observer_labor_node_v1 n WHERE $13::text='page' AND n.campaign_id=$1 AND
        (n.resolve_tick BETWEEN $2 AND $3 OR n.resolve_tick BETWEEN $4 AND $5)
    UNION ALL
    SELECT $14::bigint,n.node_ordinal,n.kind,n.entity_id,n.purpose,n.scope_kind,n.scope_id,
           n.location_key,n.catchment_key,n.industry_key,n.industry_label,n.longitude,n.latitude
    FROM jsonb_to_recordset($11::text::jsonb) AS n(node_ordinal bigint,kind text,entity_id bytea,purpose text,
        scope_kind text,scope_id bytea,location_key text,catchment_key text,industry_key text,industry_label text,longitude numeric,latitude numeric)
), moves AS (
    SELECT resolve_tick,source_node,destination_node,receipt_family,recorded_micro_hours,unknown_opening
    FROM public.v_observer_labor_movement_v1 m WHERE $13='page' AND m.campaign_id=$1 AND
        (m.resolve_tick BETWEEN $2 AND $3 OR m.resolve_tick BETWEEN $4 AND $5)
    UNION ALL
    SELECT $14::bigint,m.source_node,m.destination_node,m.receipt_family,m.recorded_micro_hours,m.unknown_opening
    FROM jsonb_to_recordset($12::text::jsonb) AS m(source_node bigint,destination_node bigint,receipt_family text,
        recorded_micro_hours numeric,unknown_opening boolean)
), company_labels AS MATERIALIZED (
    SELECT company_id,label,foundation_sha256 FROM public.v_observer_economic_company_v1 WHERE campaign_id=$1
), owners AS MATERIALIZED (
    SELECT 'company_cash'::text AS account_kind, company_id AS account_id, company_id, foundation_sha256 FROM company_labels
    UNION ALL
    SELECT 'site_cash',site_id,company_id,foundation_sha256 FROM public.v_observer_economic_company_member_v1 WHERE campaign_id=$1
), company_accounts AS MATERIALIZED (
    -- Only a captured account in this foundation can name its legal principal.
    SELECT jsonb_object_agg(o.account_kind||':'||encode(o.account_id,'hex'),
               jsonb_build_array('company:'||encode(c.company_id,'hex'),c.label)) AS by_principal
    FROM owners o JOIN company_labels c USING(company_id,foundation_sha256)
    JOIN public.v_observer_economic_flow_account_v1 a USING (account_kind,account_id,foundation_sha256)
    WHERE a.campaign_id=$1 AND ($6::text IN ('company','counterparty')
        OR ($7::text IS NOT NULL AND $15::text IN ('company','counterparty')) OR $16::text IN ('company','counterparty'))
), scopes AS (
    SELECT n.resolve_tick,n.node_ordinal,n.kind,n.purpose,n.scope_kind||':'||encode(n.scope_id,'hex') AS principal,
        owner.company->>0 AS company,owner.company->>1 AS company_label,
        n.location_key,n.catchment_key,n.industry_key,n.industry_label,
        ($9 IS NULL OR v.location_key IS NOT NULL OR
         (n.longitude IS NOT NULL AND n.latitude IS NOT NULL AND EXISTS (SELECT FROM envelopes e WHERE
          public.ST_Covers(e.area,public.ST_SetSRID(public.ST_MakePoint(n.longitude::double precision,n.latitude::double precision),4269))))) AS in_view
    FROM nodes n LEFT JOIN visible v ON n.location_key=v.location_key
    CROSS JOIN company_accounts a
    CROSS JOIN LATERAL (SELECT a.by_principal -> (n.scope_kind||':'||encode(n.scope_id,'hex')) AS company) owner
), dimensions AS (
    SELECT s.resolve_tick,s.node_ordinal,s.kind,s.purpose,s.in_view,
        CASE $6::text WHEN 'account' THEN s.principal
      WHEN 'location' THEN s.location_key WHEN 'catchment' THEN s.catchment_key
      WHEN 'industry' THEN s.industry_key WHEN 'company' THEN s.company
      WHEN 'counterparty' THEN coalesce(s.company,s.principal) END AS key,
        CASE $15::text WHEN 'account' THEN s.principal
      WHEN 'location' THEN s.location_key WHEN 'catchment' THEN s.catchment_key
      WHEN 'industry' THEN s.industry_key WHEN 'company' THEN s.company
      WHEN 'counterparty' THEN coalesce(s.company,s.principal) END AS focus_key,
    CASE $16::text WHEN 'account' THEN s.principal
      WHEN 'location' THEN s.location_key WHEN 'catchment' THEN s.catchment_key
      WHEN 'industry' THEN s.industry_key WHEN 'company' THEN s.company
      WHEN 'counterparty' THEN coalesce(s.company,s.principal) END AS peer_key,
        CASE $6::text WHEN 'industry' THEN s.industry_label
      WHEN 'company' THEN s.company_label WHEN 'counterparty' THEN s.company_label END AS label
    FROM scopes s
), endpoints AS (
    SELECT w.comparison,m.recorded_micro_hours,m.unknown_opening,
        l.key AS source_key,recipient.key AS destination_key,l.label AS source_label,r.label AS destination_label,
        l.peer_key AS source_peer,recipient.peer_key AS destination_peer,
        l.in_view AND ($7::text IS NULL OR recipient.focus_key IS NOT DISTINCT FROM $7) AS show_source,
        recipient.in_view AND ($7::text IS NULL OR l.focus_key IS NOT DISTINCT FROM $7) AS show_destination,
        ($7 IS NOT NULL OR m.source_node=m.destination_node OR (l.key IS NOT NULL AND l.key=recipient.key) IS TRUE) AS shared_group,
        (l.node_ordinal IS NOT NULL AND r.node_ordinal IS NOT NULL) AS resolved
    FROM moves m JOIN windows w ON m.resolve_tick BETWEEN w.first_tick AND w.last_tick
    LEFT JOIN dimensions l ON (l.resolve_tick,l.node_ordinal)=(m.resolve_tick,m.source_node)
    LEFT JOIN dimensions r ON (r.resolve_tick,r.node_ordinal)=(m.resolve_tick,m.destination_node)
    -- These releases occurred at the household, site, or consumer process in the
    -- physical receipt. Transport losses and untracked final-demand deliveries
    -- do not identify the destination from the source principal.
    CROSS JOIN LATERAL (SELECT r.kind='sink' AND (r.purpose,l.kind,m.receipt_family) IN (
        ('household_consumption','household_stock','household_consumption'),
        ('household_service_use','household_stock','household_services'),
        ('household_service_use','household_stock','service_performance'),
        ('unallocated_service_expiry','site_stock','service_outputs'),
        ('unused_service_expiry','household_stock','service_performance'),
        ('unused_service_expiry','site_stock','service_performance'),
        ('maintenance_expiry','maintenance','maintenance')
    ) AS at_source) local_use
    -- Place only the geographic endpoint. The sink still has its recorded node
    -- identity and purpose, with no invented account, industry or catchment.
    CROSS JOIN LATERAL (SELECT
        CASE WHEN $6='location' AND local_use.at_source THEN l.key ELSE r.key END AS key,
        CASE WHEN $15='location' AND local_use.at_source THEN l.focus_key ELSE r.focus_key END AS focus_key,
        CASE WHEN $16='location' AND local_use.at_source THEN l.peer_key ELSE r.peer_key END AS peer_key,
        CASE WHEN local_use.at_source THEN l.in_view ELSE r.in_view END AS in_view
    ) recipient
), postings AS (
    SELECT comparison,source_key AS key,source_label AS label,
        CASE WHEN shared_group AND show_destination THEN 'within' ELSE 'outbound' END AS direction,
        recorded_micro_hours AS hours,unknown_opening::integer AS additional
    FROM endpoints WHERE show_source
        AND ($16::text IS NULL OR (source_peer IS NOT DISTINCT FROM $17::text
            AND (CASE WHEN shared_group AND show_destination THEN 'within' ELSE 'outbound' END)=$18::text))
    UNION ALL
    SELECT comparison,destination_key,destination_label,'inbound',recorded_micro_hours,unknown_opening::integer
    FROM endpoints WHERE show_destination AND NOT (shared_group AND show_source)
        AND ($16 IS NULL OR (destination_peer IS NOT DISTINCT FROM $17 AND $18='inbound'))
), grouped AS (
    SELECT comparison,key,max(label) AS label,direction,sum(hours) AS hours,
        sum(additional) AS unknown,count(*)::numeric AS movements FROM postings GROUP BY comparison,key,direction
), combined AS (
    SELECT * FROM grouped UNION ALL
    SELECT * FROM jsonb_to_recordset($10::text::jsonb) AS prior(comparison boolean,key text,label text,
        direction text,hours numeric,unknown numeric,movements numeric)
), folded AS (
    SELECT comparison,key,max(label) AS label,direction,sum(hours) AS hours,sum(unknown) AS unknown,
        sum(movements) AS movements FROM combined GROUP BY comparison,key,direction
), weights AS (
    SELECT f.*,coalesce(sum(hours) FILTER (WHERE NOT comparison) OVER (PARTITION BY key),0) AS current_hours
    FROM folded f
), ranked AS (
    SELECT w.*,dense_rank() OVER (ORDER BY current_hours DESC,key COLLATE pg_catalog."C" NULLS LAST) AS rank
    FROM weights w
), page AS (
    SELECT *,rank>$8::bigint AND rank<=$8::bigint+20 AS shown FROM ranked
), entries AS (
    SELECT 'group'::text AS row_kind,key,max(label) AS label,rank,1::bigint AS groups
    FROM page WHERE shown GROUP BY key,rank
    UNION ALL SELECT 'remainder',NULL,NULL,NULL,count(DISTINCT rank) FROM page WHERE NOT shown
    UNION ALL SELECT 'total',NULL,NULL,NULL,count(DISTINCT rank) FROM page
), amounts AS (
    -- Each folded direction contributes once to its group or remainder, and once to the total.
    SELECT bucket.row_kind,bucket.rank,p.comparison,p.direction,
        sum(p.hours) AS hours,sum(p.unknown) AS missing,sum(p.movements) AS movements
    FROM page p CROSS JOIN LATERAL (VALUES
        ('total'::text,NULL::bigint),
        (CASE WHEN p.shown THEN 'group' ELSE 'remainder' END,CASE WHEN p.shown THEN p.rank END)
    ) AS bucket(row_kind,rank)
    GROUP BY bucket.row_kind,bucket.rank,p.comparison,p.direction
), reported AS (
    SELECT e.row_kind,e.key,e.label,e.rank,e.groups,w.comparison,
        jsonb_object_agg(d.direction,jsonb_build_object('recorded_micro_hours',coalesce(a.hours,0)::text,
          'unknown_basis_movements',coalesce(a.missing,0)::text,'movement_count',coalesce(a.movements,0)::text)) AS directions,
        sum(CASE d.direction WHEN 'inbound' THEN coalesce(a.hours,0) WHEN 'outbound' THEN -coalesce(a.hours,0) ELSE 0 END) AS net
    FROM entries e CROSS JOIN windows w CROSS JOIN (VALUES ('inbound'),('outbound'),('within')) d(direction)
    LEFT JOIN amounts a ON a.row_kind=e.row_kind AND a.rank IS NOT DISTINCT FROM e.rank
        AND a.direction=d.direction AND a.comparison=w.comparison
    GROUP BY e.row_kind,e.key,e.label,e.rank,e.groups,w.comparison
), changes AS (
    SELECT row_kind,key,label,rank,groups,
        jsonb_object_agg(comparison::text,directions||jsonb_build_object('net_recorded_micro_hours',net::text)) AS periods,
        CASE WHEN $4 IS NOT NULL THEN ((max(net) FILTER (WHERE NOT comparison))-(max(net) FILTER (WHERE comparison)))::text END AS change
    FROM reported GROUP BY row_kind,key,label,rank,groups
), rendered AS (
    SELECT row_kind,rank,jsonb_build_object('key',key,'label',coalesce(label,key),'rank',rank,'groups',groups,
        'current',periods->'false','comparison',periods->'true','net_change_recorded_micro_hours',change) AS data FROM changes
)
SELECT NOT EXISTS(SELECT FROM endpoints WHERE NOT resolved) AS valid,
    CASE WHEN $13='fold' THEN (SELECT coalesce(jsonb_agg(to_jsonb(f)),'[]') FROM folded f)
         ELSE (SELECT jsonb_build_object('groups',coalesce(jsonb_agg(data ORDER BY rank) FILTER (WHERE row_kind='group'),'[]'),
              'remainder',(jsonb_agg(data) FILTER (WHERE row_kind='remainder'))->0,
              'total',(jsonb_agg(data) FILTER (WHERE row_kind='total'))->0) FROM rendered)
    END::text AS data
