"""Read-only stage snapshot. Does not create, commit or alter a campaign."""

import argparse
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psycopg
from psycopg import sql

if TYPE_CHECKING:
    from tools.devtools.national_storage_qualification import package_claim_from_headers
else:
    # The frozen operator executes beside its exact captured helper, outside
    # the repository package tree. It never imports mutable checkout code.
    from national_storage_qualification import package_claim_from_headers

type Row = tuple[Any, ...]


def required_row(cursor: psycopg.Cursor[Row], width: int, context: str) -> Row:
    """Refuse an absent or unexpected SQL result before reading its columns."""
    row = cursor.fetchone()
    if row is None or len(row) != width:
        raise RuntimeError("missing or malformed collector result: " + context)
    return row


parser = argparse.ArgumentParser()
parser.add_argument("stage")
parser.add_argument("--campaign", required=True)
args = parser.parse_args()
here = Path(__file__).resolve().parent
out = Path(os.environ["BABYLON_STORAGE_REPORT_DIRECTORY"])
out.mkdir(exist_ok=True)
target = out / (args.stage + ".json")
assert not target.exists(), "preserve existing evidence; use a new stage name"
with psycopg.connect(
    os.environ["BABYLON_STORAGE_DSN"], options="-c search_path=pg_catalog -c jit=off"
) as connection:
    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    assert (
        required_row(
            connection.execute("SELECT current_setting('babylon.disposable_runtime',true)"),
            1,
            "disposable canary",
        )[0]
        == os.environ["BABYLON_STORAGE_CANARY"]
    )
    for schema, relation, expected in [
        (
            "babylon_state",
            "material_tick_v3",
            [
                "campaign_id",
                "resolve_tick",
                "identity_bytes",
                "register_storage_bytes",
                "receipt_storage_bytes",
                "lookup_delta_bytes",
            ],
        ),
        (
            "public",
            "v_observer_material_state_v1",
            [
                "campaign_id",
                "resolve_tick",
                "register_storage_bytes",
                "receipt_storage_bytes",
                "identity_bytes",
                "tick_content_hash",
                "lookup_delta_bytes",
            ],
        ),
    ]:
        actual = [
            r[0]
            for r in connection.execute(
                "SELECT a.attname FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
                (schema, relation),
            ).fetchall()
        ]
        assert actual == expected, (
            "unsupported current encoded storage shape: " + schema + "." + relation
        )
    relations = connection.execute((here / "national_storage_relations.sql").read_text()).fetchall()
    metadata = required_row(
        connection.execute(
            "SELECT current_database(),current_setting('server_version'),pg_database_size(current_database()),pg_current_wal_lsn()::text"
        ),
        4,
        "database metadata",
    )
    markers: dict[str, dict[str, int]] = {}
    for relation in ["tick_commit", "material_tick_v3"]:
        query = sql.SQL(
            "SELECT count(*),coalesce(max(resolve_tick),0) FROM babylon_state.{} WHERE campaign_id=%s::uuid"
        ).format(sql.Identifier(relation))
        count, maximum = required_row(
            connection.execute(query, (args.campaign,)), 2, relation + " markers"
        )
        assert count == maximum, "noncontiguous per-campaign durable rows: " + relation
        markers[relation] = {"count": count, "maximum_resolve_tick": maximum}
    assert markers["tick_commit"] == markers["material_tick_v3"], (
        "material rows lack matching acknowledged markers"
    )
    columns: dict[str, Row] = {}
    expected_columns = {
        "material_campaign_foundation_v3": {
            "content_sha256",
            "initial_register_bytes",
            "foundation_sha256",
        },
        "material_tick_v3": {
            "identity_bytes",
            "register_storage_bytes",
            "receipt_storage_bytes",
            "lookup_delta_bytes",
        },
        "campaign_foundation": {
            "stable_graph",
            "world_registers",
            "resolver_manifest",
            "prepared_environment",
            "defines_hash",
            "rules_hash",
            "ref_digest",
            "content_bundle_bytes",
            "foundation_sha256",
        },
        "checkpoint_manifest": {"manifest_bytes", "manifest_sha256"},
        "checkpoint_section_v1": {"inline_section_bytes", "decoded_sha256"},
    }
    for relation in expected_columns:
        assert (
            required_row(
                connection.execute("SELECT to_regclass(%s)", ("babylon_state." + relation,)),
                1,
                relation + " catalog identity",
            )[0]
            is not None
        ), "missing expected relation: " + relation
    for relation, filters in [
        ("material_campaign_foundation_v3", "campaign_id=%s::uuid"),
        ("material_tick_v3", "campaign_id=%s::uuid"),
        ("campaign_foundation", "campaign_id=%s::uuid"),
        ("checkpoint_manifest", "campaign_id=%s::uuid"),
        ("checkpoint_section_v1", "campaign_id=%s::uuid"),
    ]:
        names = connection.execute(
            "SELECT a.attname FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='babylon_state' AND c.relname=%s AND a.atttypid='bytea'::regtype AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
            (relation,),
        ).fetchall()
        assert {name for (name,) in names} == expected_columns[relation], (
            "unexpected bytea columns: " + relation
        )
        for (column,) in names:
            query = sql.SQL(
                "SELECT count(*),coalesce(sum(octet_length({c})),0),coalesce(sum(pg_column_size({c})),0),coalesce(array_agg(DISTINCT pg_column_compression({c})),ARRAY[]::text[]) FROM babylon_state.{r} WHERE "
            ).format(c=sql.Identifier(column), r=sql.Identifier(relation)) + sql.SQL(filters)
            columns[relation + "." + column] = required_row(
                connection.execute(query, (args.campaign,)),
                4,
                relation + "." + column + " storage aggregate",
            )
    # Every index diagnostic is separate: these are already included in relation totals.
    indexes = connection.execute(
        "SELECT n.nspname,t.relname,i.relname,pg_total_relation_size(i.oid) FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_class t ON t.oid=x.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname IN ('babylon_state','babylon_ref','babylon_meta','public') ORDER BY n.nspname,t.relname,i.relname"
    ).fetchall()
    package_claims: list[dict[str, object]] = []
    for (
        tick,
        state_head,
        receipt_head,
        delta_head,
        state_len,
        receipt_len,
        delta_len,
    ) in connection.execute(
        "SELECT resolve_tick,substring(register_storage_bytes FROM 1 FOR 192),substring(receipt_storage_bytes FROM 1 FOR 192),substring(lookup_delta_bytes FROM 1 FOR 192),octet_length(register_storage_bytes),octet_length(receipt_storage_bytes),octet_length(lookup_delta_bytes) FROM babylon_state.material_tick_v3 WHERE campaign_id=%s::uuid ORDER BY resolve_tick",
        (args.campaign,),
    ).fetchall():
        state_head, receipt_head, delta_head = map(bytes, (state_head, receipt_head, delta_head))
        package_claims.append(
            package_claim_from_headers(
                tick, state_head, receipt_head, delta_head, state_len, receipt_len, delta_len
            ).model_dump()
        )
    county_geoids = [
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT county_geoid FROM babylon_meta.territory_county_map_v1 WHERE campaign_id=%s::uuid ORDER BY county_geoid",
            (args.campaign,),
        ).fetchall()
    ]
    hashes = connection.execute(
        "SELECT marker.resolve_tick,encode(marker.tick_content_hash,'hex'),encode(marker.envelope_digest,'hex'),encode(sha256(material.register_storage_bytes),'hex'),encode(sha256(material.receipt_storage_bytes),'hex') FROM babylon_state.tick_commit marker JOIN babylon_state.material_tick_v3 material USING(campaign_id,resolve_tick) WHERE marker.campaign_id=%s::uuid ORDER BY marker.resolve_tick",
        (args.campaign,),
    ).fetchall()
    assert len(hashes) == markers["tick_commit"]["count"]
    lookup_hashes = connection.execute(
        "SELECT material.resolve_tick,encode(sha256(material.lookup_delta_bytes),'hex') FROM babylon_state.tick_commit marker JOIN babylon_state.material_tick_v3 material USING(campaign_id,resolve_tick) WHERE marker.campaign_id=%s::uuid ORDER BY material.resolve_tick",
        (args.campaign,),
    ).fetchall()
    assert len(lookup_hashes) == markers["tick_commit"]["count"]
    result = {
        "stage": args.stage,
        "campaign": args.campaign,
        "database": metadata[0],
        "server": metadata[1],
        "database_bytes": metadata[2],
        "wal_lsn_container_wide": metadata[3],
        "relations_columns": [
            "schema",
            "relation",
            "base_heap_all_forks_bytes",
            "base_index_bytes",
            "toast_heap_and_index_bytes",
            "total_bytes",
            "estimated_rows",
        ],
        "relations": relations,
        "index_diagnostics_not_additional_totals": indexes,
        "actual_rust_storage_package_claims": package_claims,
        "acknowledged_markers": markers,
        "bytea_columns_count_canonical_octets_column_storage_compression": columns,
        "county_geoids": county_geoids,
        "marker_and_encoded_package_hashes": hashes,
        "lookup_delta_hashes": lookup_hashes,
    }
    for row in relations:
        assert row[2] + row[3] + row[4] == row[5], "double-counting or size-query inconsistency"
    with target.open("x", encoding="utf-8") as evidence:
        evidence.write(json.dumps(result, indent=2, default=str) + "\n")
