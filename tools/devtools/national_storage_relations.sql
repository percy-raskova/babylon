-- Read each heap's own forks independently of its TOAST table and base indexes.
SELECT n.nspname AS schema, c.relname AS relation,
       pg_relation_size(c.oid, 'main') + pg_relation_size(c.oid, 'fsm')
           + pg_relation_size(c.oid, 'vm') + pg_relation_size(c.oid, 'init') AS base_heap_all_forks_bytes,
       CASE WHEN c.reltoastrelid=0 THEN 0 ELSE pg_total_relation_size(c.reltoastrelid) END AS toast_heap_and_index_bytes,
       c.reltuples AS estimated_rows
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','m') AND n.nspname IN ('babylon_state','babylon_ref','babylon_meta','public')
ORDER BY n.nspname,c.relname;
