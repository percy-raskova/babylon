-- Each ordinary base table appears once; TOAST is charged to its parent.
SELECT n.nspname AS schema, c.relname AS relation,
       pg_table_size(c.oid) - CASE WHEN c.reltoastrelid=0 THEN 0 ELSE pg_total_relation_size(c.reltoastrelid) END AS base_heap_all_forks_bytes,
       pg_indexes_size(c.oid) AS base_index_bytes,
       CASE WHEN c.reltoastrelid=0 THEN 0 ELSE pg_total_relation_size(c.reltoastrelid) END AS toast_heap_and_index_bytes,
       pg_total_relation_size(c.oid) AS total_bytes,
       c.reltuples AS estimated_rows
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','m') AND n.nspname IN ('babylon_state','babylon_ref','babylon_meta','public')
ORDER BY n.nspname,c.relname;
