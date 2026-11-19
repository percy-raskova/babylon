-- Keep the county key set independent of the complete, authenticated one-period position scan.
WITH county_nodes AS MATERIALIZED (
    SELECT node_ordinal FROM public.v_observer_labor_node_v1
    WHERE campaign_id=$1 AND resolve_tick=$2 AND location_key=$3
), buckets AS MATERIALIZED (
    SELECT CASE WHEN node_ordinal IN (SELECT node_ordinal FROM county_nodes) THEN side END AS side,
           sum(recorded_micro_hours)::text AS hours, count(*) AS positions,
           count(*) FILTER (WHERE unknown_opening) AS unknown_positions
    FROM public.v_observer_labor_position_v1
    WHERE campaign_id=$1 AND resolve_tick=$2
    GROUP BY 1
), coverage AS (
    SELECT position_count=COALESCE((SELECT sum(positions) FROM buckets),0) AS complete
    FROM public.v_observer_labor_period_v1
    WHERE campaign_id=$1 AND resolve_tick=$2 AND detail_retained
)
SELECT complete,side,hours,positions,unknown_positions
FROM coverage LEFT JOIN buckets ON buckets.side IS NOT NULL
