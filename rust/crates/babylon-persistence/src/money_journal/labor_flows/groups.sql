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
        EXISTS (SELECT FROM windows w WHERE n.resolve_tick BETWEEN w.first_tick AND w.last_tick)
    UNION ALL
    SELECT $14::bigint,n.node_ordinal,n.kind,n.entity_id,n.purpose,n.scope_kind,n.scope_id,
           n.location_key,n.catchment_key,n.industry_key,n.industry_label,n.longitude,n.latitude
    FROM jsonb_to_recordset($11::text::jsonb) AS n(node_ordinal bigint,kind text,entity_id bytea,purpose text,
        scope_kind text,scope_id bytea,location_key text,catchment_key text,industry_key text,industry_label text,longitude numeric,latitude numeric)
), moves AS (
    SELECT resolve_tick,source_node,destination_node,recorded_micro_hours,unknown_opening
    FROM public.v_observer_labor_movement_v1 m WHERE $13='page' AND m.campaign_id=$1 AND
        EXISTS (SELECT FROM windows w WHERE m.resolve_tick BETWEEN w.first_tick AND w.last_tick)
    UNION ALL
    SELECT $14::bigint,m.source_node,m.destination_node,m.recorded_micro_hours,m.unknown_opening
    FROM jsonb_to_recordset($12::text::jsonb) AS m(source_node bigint,destination_node bigint,
        recorded_micro_hours numeric,unknown_opening boolean)
), scopes AS (
    SELECT n.resolve_tick,n.node_ordinal,n.scope_kind||':'||encode(n.scope_id,'hex') AS principal,
        'company:'||encode(a.company_id,'hex') AS company,a.company_label,
        n.location_key,n.catchment_key,n.industry_key,n.industry_label,
        ($9 IS NULL OR v.location_key IS NOT NULL OR
         (n.longitude IS NOT NULL AND n.latitude IS NOT NULL AND EXISTS (SELECT FROM envelopes e WHERE
          public.ST_Covers(e.area,public.ST_SetSRID(public.ST_MakePoint(n.longitude::double precision,n.latitude::double precision),4269))))) AS in_view
    FROM nodes n LEFT JOIN visible v ON n.location_key=v.location_key
    LEFT JOIN public.v_observer_economic_flow_account_v2 a
        ON a.campaign_id=$1 AND (a.account_kind,a.account_id)=(n.scope_kind,n.scope_id)
), dimensions AS (
    SELECT s.resolve_tick,s.node_ordinal,s.in_view,
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
        l.key AS source_key,r.key AS destination_key,l.label AS source_label,r.label AS destination_label,l.peer_key AS source_peer,r.peer_key AS destination_peer,
        l.in_view AND ($7::text IS NULL OR r.focus_key IS NOT DISTINCT FROM $7) AS show_source,
        r.in_view AND ($7::text IS NULL OR l.focus_key IS NOT DISTINCT FROM $7) AS show_destination,
        ($7 IS NOT NULL OR m.source_node=m.destination_node OR (l.key IS NOT NULL AND l.key=r.key) IS TRUE) AS shared_group,
        (l.node_ordinal IS NOT NULL AND r.node_ordinal IS NOT NULL) AS resolved
    FROM moves m JOIN windows w ON m.resolve_tick BETWEEN w.first_tick AND w.last_tick
    LEFT JOIN dimensions l ON (l.resolve_tick,l.node_ordinal)=(m.resolve_tick,m.source_node)
    LEFT JOIN dimensions r ON (r.resolve_tick,r.node_ordinal)=(m.resolve_tick,m.destination_node)
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
), ranks AS (
    SELECT key,max(label) AS label,row_number() OVER (ORDER BY coalesce(sum(hours) FILTER (WHERE NOT comparison),0) DESC,
        key COLLATE pg_catalog."C" NULLS LAST) AS rank FROM folded GROUP BY key
), page AS (
    SELECT *,rank>$8::bigint AND rank<=$8::bigint+20 AS shown FROM ranks
), entries AS (
    SELECT 'group'::text AS row_kind,key,label,rank,1::bigint AS groups FROM page WHERE shown
    UNION ALL SELECT 'remainder',NULL,NULL,NULL,count(*) FROM page WHERE NOT shown
    UNION ALL SELECT 'total',NULL,NULL,NULL,count(*) FROM page
), amounts AS (
    SELECT e.row_kind,e.key,e.rank,m.comparison,m.direction,
        sum(m.hours) AS hours,sum(m.unknown) AS missing,sum(m.movements) AS movements
    FROM entries e JOIN page p ON e.row_kind='total' OR (e.row_kind='remainder' AND NOT p.shown)
        OR (e.row_kind='group' AND e.key IS NOT DISTINCT FROM p.key)
    JOIN folded m ON m.key IS NOT DISTINCT FROM p.key
    GROUP BY e.row_kind,e.key,e.rank,m.comparison,m.direction
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
