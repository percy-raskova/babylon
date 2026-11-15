-- $1 campaign; $2/$3 and $4/$5 inclusive current/comparison intervals; $6 dimension;
-- $7 offset; $8 optional NAD83 viewport; $9 one authenticated period; $10 optional focus.
-- $11 compact grouped history; $12 stage ('fold' accumulates history; 'page' ranks with retained facts).
WITH windows(first_tick,last_tick,is_compare) AS (
  SELECT $2::bigint,$3::bigint,false
  UNION ALL SELECT $4::bigint,$5::bigint,true WHERE $4 IS NOT NULL
), historical AS (
  SELECT t AS resolve_tick,pk AS payer_kind,decode(p,'hex') AS payer_id,
    rk AS recipient_kind,decode(r,'hex') AS recipient_id,n AS amount_micros
  FROM jsonb_to_recordset($9::text::jsonb) AS h(t bigint,pk text,p text,rk text,r text,n numeric)
), payments AS (
  SELECT s.resolve_tick,s.payer_kind,s.payer_id,s.recipient_kind,s.recipient_id,s.amount_micros
  FROM public.v_observer_economic_payment_v1 s WHERE $12::text='page' AND s.campaign_id=$1
    AND EXISTS(SELECT 1 FROM windows w WHERE s.resolve_tick BETWEEN w.first_tick AND w.last_tick)
  UNION ALL SELECT * FROM historical
), bounds AS (
  SELECT ($8::double precision[])[1] AS west, ($8::double precision[])[2] AS south,
         ($8::double precision[])[3] AS east, ($8::double precision[])[4] AS north
), rectangles AS (
  SELECT public.ST_MakeEnvelope(west,south,east,north,4269) AS box FROM bounds WHERE west<=east
  UNION ALL SELECT public.ST_MakeEnvelope(west,south,180,north,4269) FROM bounds WHERE west>east
  UNION ALL SELECT public.ST_MakeEnvelope(-180,south,east,north,4269) FROM bounds WHERE west>east
), visible_locations AS (
  SELECT DISTINCT l.location_key FROM rectangles b JOIN public.v_observer_economic_flow_location_v1 l
    ON l.campaign_id=$1 AND public.ST_Covers(b.box,l.county_internal_point)
), dimensions AS (
  SELECT a.account_kind,a.account_id,
    CASE $6::text WHEN 'account' THEN a.account_kind||':'||encode(a.account_id,'hex')
      WHEN 'location' THEN a.location_key WHEN 'industry' THEN a.industry_key ELSE a.catchment_key END AS key,
    CASE $6::text WHEN 'industry' THEN a.industry_label END AS label,
    ($8 IS NULL OR v.location_key IS NOT NULL) AS in_view
  FROM public.v_observer_economic_flow_account_v1 a LEFT JOIN visible_locations v USING(location_key)
  WHERE a.campaign_id=$1
), edges AS (
  SELECT w.is_compare, s.amount_micros, p.key AS pk, r.key AS rk, p.label AS pl,r.label AS rl,
    p.in_view AND ($10::text IS NULL OR r.key=$10) AS show_payer,
    r.in_view AND ($10::text IS NULL OR p.key=$10) AS show_recipient,
    (s.payer_kind,s.payer_id)=(s.recipient_kind,s.recipient_id) AS same_account,
    p.account_id IS NOT NULL AND r.account_id IS NOT NULL AS classified
  FROM payments s JOIN windows w ON s.resolve_tick BETWEEN w.first_tick AND w.last_tick
  LEFT JOIN dimensions p ON (p.account_kind,p.account_id)=(s.payer_kind,s.payer_id)
  LEFT JOIN dimensions r ON (r.account_kind,r.account_id)=(s.recipient_kind,s.recipient_id)
), classified_edges AS (
  SELECT *, show_payer AND show_recipient AND (same_account OR (pk IS NOT NULL AND pk=rk) IS TRUE) AS internal FROM edges
), postings AS (
  SELECT pk AS key,pl AS label,is_compare,0::numeric AS incoming,
      CASE WHEN internal THEN 0 ELSE amount_micros END AS outgoing,
      CASE WHEN internal THEN amount_micros ELSE 0 END AS inside
  FROM classified_edges WHERE show_payer
  UNION ALL
  SELECT rk,rl,is_compare,amount_micros,0,0 FROM classified_edges WHERE show_recipient AND NOT internal
), this_period AS (
  SELECT key,max(label) AS label,
    coalesce(sum(incoming) FILTER(WHERE NOT is_compare),0) AS i,
    coalesce(sum(outgoing) FILTER(WHERE NOT is_compare),0) AS o,
    coalesce(sum(inside) FILTER(WHERE NOT is_compare),0) AS t,
    coalesce(sum(incoming) FILTER(WHERE is_compare),0) AS ci,
    coalesce(sum(outgoing) FILTER(WHERE is_compare),0) AS co,
    coalesce(sum(inside) FILTER(WHERE is_compare),0) AS ct
  FROM postings GROUP BY key
), accumulated AS (
  SELECT * FROM this_period
  UNION ALL
  SELECT * FROM jsonb_to_recordset($11::text::jsonb) AS h(key text,label text,i numeric,o numeric,t numeric,ci numeric,co numeric,ct numeric)
), grouped AS (
  SELECT key,max(label) AS label,sum(i) AS i,sum(o) AS o,sum(t) AS t,sum(ci) AS ci,sum(co) AS co,sum(ct) AS ct
  FROM accumulated GROUP BY key
), ranked AS (
  SELECT *,row_number() OVER(ORDER BY i+o+t DESC, key COLLATE pg_catalog."C" NULLS LAST) AS rank
  FROM grouped
), paged AS (
  SELECT *, rank>$7::bigint AND rank<=$7::bigint+20 AS shown FROM ranked
), summaries AS (
  SELECT 'group' AS kind,key,label,rank,1::bigint AS groups,i,o,t,ci,co,ct FROM paged WHERE shown
  UNION ALL
  SELECT s.kind,NULL,NULL,NULL,count(p.rank),
    coalesce(sum(p.i),0),coalesce(sum(p.o),0),coalesce(sum(p.t),0),
    coalesce(sum(p.ci),0),coalesce(sum(p.co),0),coalesce(sum(p.ct),0)
  FROM (VALUES ('remainder'),('total')) AS s(kind)
  LEFT JOIN paged p ON s.kind='total' OR NOT p.shown GROUP BY s.kind
), rendered AS (
  SELECT kind,rank,jsonb_build_object('key',key,'label',coalesce(label,key),'rank',rank,'groups',groups,
    'current',jsonb_build_object('inflow_micros',i::text,'outflow_micros',o::text,'internal_micros',t::text,'net_micros',(i-o)::text),
    'comparison',CASE WHEN $4 IS NOT NULL THEN jsonb_build_object('inflow_micros',ci::text,'outflow_micros',co::text,'internal_micros',ct::text,'net_micros',(ci-co)::text) END,
    'net_change_micros',CASE WHEN $4 IS NOT NULL THEN ((i-o)-(ci-co))::text END
  ) AS data FROM summaries
)
SELECT NOT EXISTS (SELECT 1 FROM edges WHERE NOT classified) AS valid,
  CASE WHEN $12='fold' THEN (SELECT coalesce(jsonb_agg(to_jsonb(g)),'[]'::jsonb) FROM grouped g)
  ELSE (SELECT jsonb_build_object('groups',coalesce(jsonb_agg(data ORDER BY rank) FILTER(WHERE kind='group'),'[]'::jsonb),
    'remainder',(jsonb_agg(data) FILTER(WHERE kind='remainder'))->0,
    'total',(jsonb_agg(data) FILTER(WHERE kind='total'))->0) FROM rendered) END::text AS result
