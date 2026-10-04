-- One current Rust schema. Installed atomically with current_archive.sql.

CREATE SCHEMA babylon_meta;

CREATE SCHEMA babylon_ref;

CREATE SCHEMA babylon_state;

CREATE FUNCTION babylon_state.verify_tick_choice_receipt_v1_continuity() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE
    affected_campaign UUID;
    affected_tick BIGINT;
    affected_receipt BIGINT;
    expected_position BIGINT;
    observed_position BIGINT;
    expected_start NUMERIC(20, 0);
    observed_start NUMERIC(20, 0);
    observed_end NUMERIC(20, 0);
    parent_draw NUMERIC(20, 0);
    parent_selected TEXT;
    selected_matches BIGINT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        affected_campaign := OLD.campaign_id;
        affected_tick := OLD.resolve_tick;
        affected_receipt := OLD.encounter_ordinal;
    ELSE
        affected_campaign := NEW.campaign_id;
        affected_tick := NEW.resolve_tick;
        affected_receipt := NEW.encounter_ordinal;
    END IF;

    expected_position := 0;
    FOR observed_position IN
        SELECT receipt.encounter_ordinal
          FROM babylon_state.tick_choice_receipt_v1 AS receipt
         WHERE receipt.campaign_id = affected_campaign
           AND receipt.resolve_tick = affected_tick
         ORDER BY receipt.encounter_ordinal
    LOOP
        IF observed_position <> expected_position THEN
            RAISE EXCEPTION USING
                ERRCODE = 'P0001',
                MESSAGE = 'tick_choice_receipt_v1_refused_noncontinuous_encounter_order';
        END IF;
        expected_position := expected_position + 1;
    END LOOP;

    SELECT receipt.draw_ticket, receipt.selected_outcome
      INTO parent_draw, parent_selected
      FROM babylon_state.tick_choice_receipt_v1 AS receipt
     WHERE receipt.campaign_id = affected_campaign
       AND receipt.resolve_tick = affected_tick
       AND receipt.encounter_ordinal = affected_receipt;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    expected_position := 0;
    expected_start := 0;
    FOR observed_position, observed_start, observed_end IN
        SELECT branch.position, branch.ticket_start, branch.ticket_end_exclusive
          FROM babylon_state.tick_choice_receipt_branch_v1 AS branch
         WHERE branch.campaign_id = affected_campaign
           AND branch.resolve_tick = affected_tick
           AND branch.encounter_ordinal = affected_receipt
         ORDER BY branch.position
    LOOP
        IF observed_position <> expected_position OR observed_start <> expected_start THEN
            RAISE EXCEPTION USING
                ERRCODE = 'P0001',
                MESSAGE = 'tick_choice_receipt_v1_refused_noncontinuous_branch_order';
        END IF;
        expected_position := expected_position + 1;
        expected_start := observed_end;
    END LOOP;
    IF expected_position = 0 OR expected_start <> 18446744073709551616 THEN
        RAISE EXCEPTION USING
            ERRCODE = 'P0001',
            MESSAGE = 'tick_choice_receipt_v1_refused_incomplete_ticket_measure';
    END IF;

    SELECT pg_catalog.count(*)
      INTO selected_matches
      FROM babylon_state.tick_choice_receipt_branch_v1 AS branch
     WHERE branch.campaign_id = affected_campaign
       AND branch.resolve_tick = affected_tick
       AND branch.encounter_ordinal = affected_receipt
       AND branch.outcome_member = parent_selected
       AND parent_draw >= branch.ticket_start
       AND parent_draw < branch.ticket_end_exclusive;
    IF selected_matches <> 1 THEN
        RAISE EXCEPTION USING
            ERRCODE = 'P0001',
            MESSAGE = 'tick_choice_receipt_v1_refused_selected_outcome_mismatch';
    END IF;

    expected_position := 0;
    FOR observed_position IN
        SELECT carrier.position
          FROM babylon_state.tick_choice_receipt_carrier_element_v1 AS carrier
         WHERE carrier.campaign_id = affected_campaign
           AND carrier.resolve_tick = affected_tick
           AND carrier.encounter_ordinal = affected_receipt
         ORDER BY carrier.position
    LOOP
        IF observed_position <> expected_position THEN
            RAISE EXCEPTION USING
                ERRCODE = 'P0001',
                MESSAGE = 'tick_choice_receipt_v1_refused_noncontinuous_carrier_order';
        END IF;
        expected_position := expected_position + 1;
    END LOOP;
    RETURN NULL;
END
$$;

CREATE FUNCTION babylon_state.lock_tick_event_marker_v2() RETURNS trigger
    LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        'babylon.event-marker.v1:' || NEW.campaign_id::text || ':' || NEW.resolve_tick::text, 0));
    RETURN NEW;
END
$$;

CREATE FUNCTION babylon_state.guard_tick_event_v2_history() RETURNS trigger
    LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE
    affected RECORD;
BEGIN
    FOR affected IN
        SELECT DISTINCT campaign_id FROM new_event_rows ORDER BY campaign_id
    LOOP
        PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
            'babylon.graph-lookup.v1:' || affected.campaign_id::text, 0));
    END LOOP;
    FOR affected IN
        SELECT DISTINCT campaign_id, resolve_tick FROM (
            SELECT campaign_id, resolve_tick FROM new_event_rows
        ) AS changed ORDER BY campaign_id, resolve_tick
    LOOP
        PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
            'babylon.event-marker.v1:' || affected.campaign_id::text || ':' || affected.resolve_tick::text, 0));
        IF EXISTS (SELECT 1 FROM babylon_state.tick_commit
            WHERE campaign_id = affected.campaign_id AND resolve_tick = affected.resolve_tick) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'tick_event_v2_refused_marked_history_mutation';
        END IF;
    END LOOP;
    RETURN NULL;
END
$$;

CREATE TABLE babylon_meta.breadcrumb (
    campaign_id uuid NOT NULL,
    "position" integer NOT NULL,
    entity_id text NOT NULL,
    CONSTRAINT breadcrumb_position_check CHECK (("position" >= 0))
);

CREATE TABLE babylon_meta.campaign (
    campaign_id uuid NOT NULL,
    slug text NOT NULL,
    engine_version text NOT NULL,
    defines_hash text NOT NULL,
    last_tick bigint DEFAULT 0 NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    last_played_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    rng_seed bigint,
    content_digest text,
    CONSTRAINT campaign_last_tick_check CHECK ((last_tick >= 0)),
    CONSTRAINT campaign_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'ABANDONED'::text])))
);

CREATE TABLE babylon_meta.jumplist (
    campaign_id uuid NOT NULL,
    "position" integer NOT NULL,
    entity_id text NOT NULL,
    CONSTRAINT jumplist_position_check CHECK (("position" >= 0))
);

CREATE TABLE babylon_meta.watchlist (
    campaign_id uuid NOT NULL,
    "position" integer NOT NULL,
    entity_id text NOT NULL,
    CONSTRAINT watchlist_position_check CHECK (("position" >= 0))
);

CREATE TABLE babylon_ref.county_h3_land_area (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    cell_id bigint NOT NULL,
    membership_origin smallint NOT NULL,
    county_geoid text NOT NULL COLLATE pg_catalog."C",
    land_area_m2 bigint NOT NULL,
    CONSTRAINT county_h3_land_area_cell_positive CHECK ((cell_id > 0)),
    CONSTRAINT county_h3_land_area_direct_origin CHECK ((membership_origin = 1)),
    CONSTRAINT county_h3_land_area_positive CHECK ((land_area_m2 > 0)),
    CONSTRAINT county_h3_land_area_product_code CHECK ((product_code = 'census_county_h3_land_overlap_mi_2023'::text))
);

CREATE TABLE babylon_ref.county_identity (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    county_id bigint NOT NULL,
    county_geoid text NOT NULL COLLATE pg_catalog."C",
    state_id integer NOT NULL,
    county_fips text NOT NULL COLLATE pg_catalog."C",
    county_name text NOT NULL COLLATE pg_catalog."C",
    CONSTRAINT county_identity_county_id_positive CHECK ((county_id > 0)),
    CONSTRAINT county_identity_fips_format CHECK ((county_fips ~ '^[0-9]{3}$'::text)),
    CONSTRAINT county_identity_geoid_format CHECK ((county_geoid ~ '^[0-9]{5}$'::text)),
    CONSTRAINT county_identity_geoid_suffix CHECK (("right"(county_geoid, 3) = county_fips)),
    CONSTRAINT county_identity_name_nonempty CHECK ((county_name <> ''::text)),
    CONSTRAINT county_identity_product_code CHECK ((product_code = 'dim_county'::text)),
    CONSTRAINT county_identity_state_id_positive CHECK ((state_id > 0))
);

CREATE TABLE babylon_ref.county_place_h3_land_area (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    cell_id bigint NOT NULL,
    membership_origin smallint NOT NULL,
    county_geoid text NOT NULL COLLATE pg_catalog."C",
    place_geoid text NOT NULL COLLATE pg_catalog."C",
    place_land_area_m2 bigint NOT NULL,
    cell_mi_land_area_m2 bigint NOT NULL,
    place_land_area_share_ppb integer NOT NULL,
    CONSTRAINT county_place_h3_land_area_cell_positive CHECK ((cell_id > 0)),
    CONSTRAINT county_place_h3_land_area_denominator_positive CHECK ((cell_mi_land_area_m2 > 0)),
    CONSTRAINT county_place_h3_land_area_direct_origin CHECK ((membership_origin = 1)),
    CONSTRAINT county_place_h3_land_area_numerator_bound CHECK ((place_land_area_m2 <= cell_mi_land_area_m2)),
    CONSTRAINT county_place_h3_land_area_place_positive CHECK ((place_land_area_m2 > 0)),
    CONSTRAINT county_place_h3_land_area_product_code CHECK ((product_code = 'census_county_place_h3_land_overlap_mi_2023'::text)),
    CONSTRAINT county_place_h3_land_area_share_formula CHECK ((place_land_area_share_ppb = (floor((((place_land_area_m2)::numeric * (1000000000)::numeric) / (cell_mi_land_area_m2)::numeric)))::bigint)),
    CONSTRAINT county_place_h3_land_area_share_range CHECK (((place_land_area_share_ppb >= 0) AND (place_land_area_share_ppb <= 1000000000)))
);

CREATE TABLE babylon_ref.h3_cell (
    cell_id bigint NOT NULL,
    resolution smallint NOT NULL,
    immediate_parent bigint,
    ancestor_r4 bigint,
    ancestor_r5 bigint,
    ancestor_r6 bigint,
    ancestor_r7 bigint,
    CONSTRAINT h3_cell_ancestor_r4_matches CHECK (
CASE
    WHEN ((resolution >= 0) AND (resolution <= 3)) THEN (ancestor_r4 IS NULL)
    WHEN ((resolution >= 4) AND (resolution <= 15)) THEN ((ancestor_r4 IS NOT NULL) AND (ancestor_r4 = (((cell_id & (~ ((15)::bigint << 52))) | ((4)::bigint << 52)) | (((1)::bigint << 33) - 1))))
    ELSE false
END),
    CONSTRAINT h3_cell_ancestor_r5_matches CHECK (
CASE
    WHEN ((resolution >= 0) AND (resolution <= 4)) THEN (ancestor_r5 IS NULL)
    WHEN ((resolution >= 5) AND (resolution <= 15)) THEN ((ancestor_r5 IS NOT NULL) AND (ancestor_r5 = (((cell_id & (~ ((15)::bigint << 52))) | ((5)::bigint << 52)) | (((1)::bigint << 30) - 1))))
    ELSE false
END),
    CONSTRAINT h3_cell_ancestor_r6_matches CHECK (
CASE
    WHEN ((resolution >= 0) AND (resolution <= 5)) THEN (ancestor_r6 IS NULL)
    WHEN ((resolution >= 6) AND (resolution <= 15)) THEN ((ancestor_r6 IS NOT NULL) AND (ancestor_r6 = (((cell_id & (~ ((15)::bigint << 52))) | ((6)::bigint << 52)) | (((1)::bigint << 27) - 1))))
    ELSE false
END),
    CONSTRAINT h3_cell_ancestor_r7_matches CHECK (
CASE
    WHEN ((resolution >= 0) AND (resolution <= 6)) THEN (ancestor_r7 IS NULL)
    WHEN ((resolution >= 7) AND (resolution <= 15)) THEN ((ancestor_r7 IS NOT NULL) AND (ancestor_r7 = (((cell_id & (~ ((15)::bigint << 52))) | ((7)::bigint << 52)) | (((1)::bigint << 24) - 1))))
    ELSE false
END),
    CONSTRAINT h3_cell_id_positive CHECK ((cell_id > 0)),
    CONSTRAINT h3_cell_immediate_parent_matches CHECK (
CASE
    WHEN (resolution = 0) THEN (immediate_parent IS NULL)
    WHEN ((resolution >= 1) AND (resolution <= 15)) THEN ((immediate_parent IS NOT NULL) AND (immediate_parent = (((cell_id & (~ ((15)::bigint << 52))) | (((resolution - 1))::bigint << 52)) | (((1)::bigint << (3 * (16 - resolution))) - 1))))
    ELSE false
END),
    CONSTRAINT h3_cell_resolution_matches_id CHECK ((resolution = (((cell_id >> 52) & (15)::bigint))::smallint)),
    CONSTRAINT h3_cell_resolution_range CHECK (((resolution >= 0) AND (resolution <= 15)))
);

CREATE TABLE babylon_ref.h3_land_fraction (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    cell_id bigint NOT NULL,
    membership_origin smallint NOT NULL,
    source_county_geoid text NOT NULL COLLATE pg_catalog."C",
    land_fraction_ppm integer NOT NULL,
    CONSTRAINT h3_land_fraction_cell_positive CHECK ((cell_id > 0)),
    CONSTRAINT h3_land_fraction_direct_origin CHECK ((membership_origin = 1)),
    CONSTRAINT h3_land_fraction_product_code CHECK ((product_code = 'h3_res7_land_mask'::text)),
    CONSTRAINT h3_land_fraction_range CHECK (((land_fraction_ppm >= 0) AND (land_fraction_ppm <= 1000000)))
);

CREATE TABLE babylon_ref.h3_population_count (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    cell_id bigint NOT NULL,
    membership_origin smallint NOT NULL,
    population_count bigint NOT NULL,
    CONSTRAINT h3_population_count_cell_positive CHECK ((cell_id > 0)),
    CONSTRAINT h3_population_count_direct_origin CHECK ((membership_origin = 1)),
    CONSTRAINT h3_population_count_positive CHECK ((population_count > 0)),
    CONSTRAINT h3_population_count_product_code CHECK ((product_code = 'h3_res7_population'::text))
);

CREATE TABLE babylon_ref.h3_reference_cohort (
    ref_digest bytea NOT NULL,
    format_version smallint NOT NULL,
    artifact_name text NOT NULL,
    artifact_manifest_version text NOT NULL,
    artifact_digest bytea NOT NULL,
    source_digest bytea NOT NULL,
    source_r5_digest bytea NOT NULL,
    source_r7_digest bytea NOT NULL,
    closure_digest bytea NOT NULL,
    membership_digest bytea NOT NULL,
    direct_cell_count bigint NOT NULL,
    derived_ancestor_count bigint NOT NULL,
    closure_cell_count bigint NOT NULL,
    CONSTRAINT h3_reference_cohort_artifact_digest_length CHECK ((octet_length(artifact_digest) = 32)),
    CONSTRAINT h3_reference_cohort_artifact_manifest_version_length CHECK (((octet_length(artifact_manifest_version) >= 1) AND (octet_length(artifact_manifest_version) <= 64))),
    CONSTRAINT h3_reference_cohort_artifact_name_length CHECK (((octet_length(artifact_name) >= 1) AND (octet_length(artifact_name) <= 255))),
    CONSTRAINT h3_reference_cohort_closure_count_matches CHECK ((((closure_cell_count >= 1) AND (closure_cell_count <= 1048576)) AND (closure_cell_count = (direct_cell_count + derived_ancestor_count)))),
    CONSTRAINT h3_reference_cohort_closure_digest_length CHECK ((octet_length(closure_digest) = 32)),
    CONSTRAINT h3_reference_cohort_derived_count_nonnegative CHECK (((derived_ancestor_count >= 0) AND (derived_ancestor_count <= 1048576))),
    CONSTRAINT h3_reference_cohort_direct_count_positive CHECK (((direct_cell_count >= 1) AND (direct_cell_count <= 65536))),
    CONSTRAINT h3_reference_cohort_format_v1 CHECK ((format_version = 1)),
    CONSTRAINT h3_reference_cohort_membership_digest_length CHECK ((octet_length(membership_digest) = 32)),
    CONSTRAINT h3_reference_cohort_ref_digest_length CHECK ((octet_length(ref_digest) = 32)),
    CONSTRAINT h3_reference_cohort_source_digest_length CHECK ((octet_length(source_digest) = 32)),
    CONSTRAINT h3_reference_cohort_source_r5_digest_length CHECK ((octet_length(source_r5_digest) = 32)),
    CONSTRAINT h3_reference_cohort_source_r7_digest_length CHECK ((octet_length(source_r7_digest) = 32))
);

CREATE TABLE babylon_ref.h3_reference_membership (
    ref_digest bytea NOT NULL,
    cell_id bigint NOT NULL,
    origin smallint NOT NULL,
    CONSTRAINT h3_reference_membership_cell_positive CHECK ((cell_id > 0)),
    CONSTRAINT h3_reference_membership_origin_closed CHECK ((origin = ANY (ARRAY[1, 2]))),
    CONSTRAINT h3_reference_membership_ref_digest_length CHECK ((octet_length(ref_digest) = 32))
);

CREATE TABLE babylon_ref.h3_workplace_count (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    cell_id bigint NOT NULL,
    membership_origin smallint NOT NULL,
    workplace_count bigint NOT NULL,
    CONSTRAINT h3_workplace_count_cell_positive CHECK ((cell_id > 0)),
    CONSTRAINT h3_workplace_count_direct_origin CHECK ((membership_origin = 1)),
    CONSTRAINT h3_workplace_count_positive CHECK ((workplace_count > 0)),
    CONSTRAINT h3_workplace_count_product_code CHECK ((product_code = 'h3_res7_workplace'::text))
);

CREATE TABLE babylon_ref.place_identity (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    place_geoid text NOT NULL COLLATE pg_catalog."C",
    state_fips text NOT NULL COLLATE pg_catalog."C",
    place_fips text NOT NULL COLLATE pg_catalog."C",
    place_ns text NOT NULL COLLATE pg_catalog."C",
    name text NOT NULL COLLATE pg_catalog."C",
    name_lsad text NOT NULL COLLATE pg_catalog."C",
    lsad text NOT NULL COLLATE pg_catalog."C",
    class_fp text NOT NULL COLLATE pg_catalog."C",
    principal_city_indicator text NOT NULL COLLATE pg_catalog."C",
    mtfcc text NOT NULL COLLATE pg_catalog."C",
    functional_status text NOT NULL COLLATE pg_catalog."C",
    CONSTRAINT place_identity_class_format CHECK ((class_fp ~ '^[A-Z0-9]{2}$'::text)),
    CONSTRAINT place_identity_geoid_composition CHECK ((place_geoid = (state_fips || place_fips))),
    CONSTRAINT place_identity_geoid_format CHECK ((place_geoid ~ '^[0-9]{7}$'::text)),
    CONSTRAINT place_identity_lsad_format CHECK ((lsad ~ '^[0-9]{2}$'::text)),
    CONSTRAINT place_identity_mtfcc_format CHECK ((mtfcc ~ '^[A-Z][0-9]{4}$'::text)),
    CONSTRAINT place_identity_name_lsad_nonempty CHECK ((name_lsad <> ''::text)),
    CONSTRAINT place_identity_name_nonempty CHECK ((name <> ''::text)),
    CONSTRAINT place_identity_ns_format CHECK ((place_ns ~ '^[0-9]{8}$'::text)),
    CONSTRAINT place_identity_place_fips_format CHECK ((place_fips ~ '^[0-9]{5}$'::text)),
    CONSTRAINT place_identity_principal_city CHECK ((principal_city_indicator = ANY (ARRAY['N'::text, 'Y'::text]))),
    CONSTRAINT place_identity_product_code CHECK ((product_code = 'census_place_identity_mi_2023'::text)),
    CONSTRAINT place_identity_state CHECK ((state_fips = '26'::text)),
    CONSTRAINT place_identity_status_format CHECK ((functional_status ~ '^[A-Z]$'::text))
);

CREATE TABLE babylon_ref.reference_product (
    ref_digest bytea NOT NULL,
    product_code text NOT NULL COLLATE pg_catalog."C",
    artifact_sha256 bytea NOT NULL,
    semantic_sha256 bytea,
    row_count bigint NOT NULL,
    evidence_class text NOT NULL COLLATE pg_catalog."C",
    measure_unit text COLLATE pg_catalog."C",
    denominator text COLLATE pg_catalog."C",
    CONSTRAINT reference_product_artifact_digest_length CHECK ((octet_length(artifact_sha256) = 32)),
    CONSTRAINT reference_product_code_format CHECK ((product_code ~ '^[a-z0-9_]+$'::text)),
    CONSTRAINT reference_product_denominator CHECK (((denominator IS NULL) OR (denominator = ANY (ARRAY['one_million'::text, 'cell_michigan_land_area_m2'::text])))),
    CONSTRAINT reference_product_evidence_class CHECK ((evidence_class = ANY (ARRAY['Observed'::text, 'Derived'::text]))),
    CONSTRAINT reference_product_measure_unit CHECK (((measure_unit IS NULL) OR (measure_unit = ANY (ARRAY['identity'::text, 'parts_per_million'::text, 'count'::text, 'square_metres'::text])))),
    CONSTRAINT reference_product_ref_digest_length CHECK ((octet_length(ref_digest) = 32)),
    CONSTRAINT reference_product_row_count_positive CHECK ((row_count > 0)),
    CONSTRAINT reference_product_semantic_digest_length CHECK (((semantic_sha256 IS NULL) OR (octet_length(semantic_sha256) = 32)))
);

CREATE TABLE babylon_state.archive_dirty_receipt_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    tick_content_hash bytea NOT NULL,
    CONSTRAINT archive_dirty_receipt_v1_resolve_tick_check CHECK ((resolve_tick >= 1)),
    CONSTRAINT archive_dirty_receipt_v1_tick_content_hash_check CHECK ((octet_length(tick_content_hash) = 32))
);

CREATE TABLE babylon_state.campaign (
    campaign_id uuid NOT NULL,
    replay_layout_version smallint NOT NULL,
    rng_layout_version smallint NOT NULL,
    replay_session_id text NOT NULL COLLATE pg_catalog."C",
    rng_seed bigint NOT NULL,
    defines_hash bytea NOT NULL,
    rules_hash bytea NOT NULL,
    ref_digest bytea NOT NULL,
    geography_scope text NOT NULL COLLATE pg_catalog."C",
    local_h3_ref_digest bytea,
    CONSTRAINT campaign_geography_scope CHECK (((geography_scope = 'michigan-control'::text AND local_h3_ref_digest IS NOT NULL) OR geography_scope = 'national-counties'::text)),
    CONSTRAINT campaign_local_h3_digest_length CHECK ((local_h3_ref_digest IS NULL OR octet_length(local_h3_ref_digest) = 32)),
    CONSTRAINT campaign_defines_hash_length CHECK ((octet_length(defines_hash) = 32)),
    CONSTRAINT campaign_ref_digest_length CHECK ((octet_length(ref_digest) = 32)),
    CONSTRAINT campaign_replay_layout_v1 CHECK ((replay_layout_version = 1)),
    CONSTRAINT campaign_replay_session_ascii_graphic CHECK ((replay_session_id ~ '^[!-~]+$'::text)),
    CONSTRAINT campaign_replay_session_length CHECK (((octet_length(replay_session_id) >= 1) AND (octet_length(replay_session_id) <= 256))),
    CONSTRAINT campaign_rng_layout_v2 CHECK ((rng_layout_version = 2)),
    CONSTRAINT campaign_rules_hash_length CHECK ((octet_length(rules_hash) = 32))
);

CREATE TABLE babylon_state.campaign_foundation (
    campaign_id uuid NOT NULL,
    stable_graph bytea NOT NULL,
    world_registers bytea NOT NULL,
    resolver_manifest bytea NOT NULL,
    prepared_environment bytea NOT NULL,
    replay_session_id text NOT NULL COLLATE pg_catalog."C",
    rng_seed bigint NOT NULL,
    defines_hash bytea NOT NULL,
    rules_hash bytea NOT NULL,
    ref_digest bytea NOT NULL,
    content_bundle_bytes bytea NOT NULL,
    foundation_sha256 bytea NOT NULL,
    CONSTRAINT campaign_foundation_content_bound CHECK (((octet_length(content_bundle_bytes) > 0) AND (octet_length(content_bundle_bytes) <= 67108864))),
    CONSTRAINT campaign_foundation_hashes CHECK (((octet_length(defines_hash) = 32) AND (octet_length(rules_hash) = 32) AND (octet_length(ref_digest) = 32) AND (octet_length(foundation_sha256) = 32)))
);

CREATE TABLE babylon_state.checkpoint_manifest (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    completeness_tag smallint NOT NULL,
    manifest_bytes bytea NOT NULL,
    manifest_sha256 bytea NOT NULL,
    CONSTRAINT checkpoint_manifest_completeness_tag_check CHECK ((completeness_tag = ANY (ARRAY[1, 2]))),
    CONSTRAINT checkpoint_manifest_manifest_sha256_check CHECK ((octet_length(manifest_sha256) = 32)),
    CONSTRAINT checkpoint_manifest_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.checkpoint_section_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    section_tag smallint NOT NULL,
    ordinal bigint NOT NULL,
    source_tag smallint NOT NULL,
    decoded_length bigint NOT NULL CHECK(decoded_length BETWEEN 0 AND 67108864),
    decoded_sha256 bytea NOT NULL CHECK(octet_length(decoded_sha256)=32),
    inline_section_bytes bytea,
    CONSTRAINT checkpoint_section_v1_source_shape CHECK (
      (section_tag=1 AND source_tag=1 AND inline_section_bytes IS NULL) OR
      (section_tag=2 AND source_tag=2 AND inline_section_bytes IS NOT NULL AND octet_length(inline_section_bytes)=decoded_length) OR
      (section_tag BETWEEN 3 AND 8 AND source_tag=3 AND inline_section_bytes IS NULL) OR
      (section_tag=9 AND source_tag=4 AND inline_section_bytes IS NULL)),
    CONSTRAINT checkpoint_section_v1_ordinal_check CHECK (ordinal=0),
    CONSTRAINT checkpoint_section_v1_resolve_tick_check CHECK ((resolve_tick >= 1)),
    CONSTRAINT checkpoint_section_v1_section_tag_check CHECK (((section_tag >= 1) AND (section_tag <= 9)))
);

CREATE TABLE babylon_state.graph_edge_f64_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    edge_type text NOT NULL COLLATE pg_catalog."C",
    source_local_name text NOT NULL COLLATE pg_catalog."C",
    target_local_name text NOT NULL COLLATE pg_catalog."C",
    qname text NOT NULL COLLATE pg_catalog."C",
    value_bits bigint NOT NULL,
    CONSTRAINT graph_edge_f64_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.graph_edge_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    edge_type text NOT NULL COLLATE pg_catalog."C",
    source_local_name text NOT NULL COLLATE pg_catalog."C",
    target_local_name text NOT NULL COLLATE pg_catalog."C",
    strength_bits bigint NOT NULL,
    CONSTRAINT graph_edge_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.graph_hyperedge_f64_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    local_name text NOT NULL COLLATE pg_catalog."C",
    qname text NOT NULL COLLATE pg_catalog."C",
    value_bits bigint NOT NULL,
    CONSTRAINT graph_hyperedge_f64_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.graph_hyperedge_member_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    local_name text NOT NULL COLLATE pg_catalog."C",
    "position" integer NOT NULL,
    member text NOT NULL COLLATE pg_catalog."C",
    CONSTRAINT graph_hyperedge_member_v1_position_check CHECK (("position" >= 0)),
    CONSTRAINT graph_hyperedge_member_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.graph_hyperedge_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    local_name text NOT NULL COLLATE pg_catalog."C",
    hyperedge_type text NOT NULL COLLATE pg_catalog."C",
    CONSTRAINT graph_hyperedge_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.graph_node_currency_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    local_name text NOT NULL COLLATE pg_catalog."C",
    qname text NOT NULL COLLATE pg_catalog."C",
    micro_units numeric(39,0) NOT NULL,
    CONSTRAINT graph_node_currency_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.hex_state_delta_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    cell_id bigint NOT NULL,
    c_bits bigint NOT NULL,
    v_bits bigint NOT NULL,
    s_bits bigint NOT NULL,
    k_bits bigint NOT NULL,
    biocapacity_stock_bits bigint NOT NULL,
    energy_stock_bits bigint NOT NULL,
    raw_material_stock_bits bigint NOT NULL,
    internet_access_pct_bits bigint NOT NULL,
    surveillance_coupling_bits bigint NOT NULL,
    CONSTRAINT hex_state_delta_v1_cell_id_check CHECK ((cell_id > 0)),
    CONSTRAINT hex_state_delta_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.organization_state_field_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    organization_id bytea NOT NULL,
    "position" integer NOT NULL,
    field_name text NOT NULL COLLATE pg_catalog."C",
    value_tag smallint NOT NULL,
    int_value bigint,
    currency_value numeric(39,0),
    real_bits bigint,
    ratio_bits bigint,
    ratio_min_bits bigint,
    ratio_max_bits bigint,
    bool_value boolean,
    enum_type text COLLATE pg_catalog."C",
    enum_member text COLLATE pg_catalog."C",
    stable_key bytea,
    CONSTRAINT organization_state_field_v1_check CHECK ((((value_tag = 1) AND (int_value IS NOT NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 2) AND (int_value IS NULL) AND (currency_value IS NOT NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 3) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NOT NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 4) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NOT NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 5) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NOT NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 6) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NOT NULL) AND (enum_member IS NOT NULL) AND (stable_key IS NULL)) OR (((value_tag >= 7) AND (value_tag <= 9)) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NOT NULL)))),
    CONSTRAINT organization_state_field_v1_position_check CHECK (("position" >= 0)),
    CONSTRAINT organization_state_field_v1_resolve_tick_check CHECK ((resolve_tick >= 1)),
    CONSTRAINT organization_state_field_v1_value_tag_check CHECK (((value_tag >= 1) AND (value_tag <= 9)))
);

CREATE TABLE babylon_state.organization_state_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    organization_id bytea NOT NULL,
    organization_kind_tag smallint NOT NULL,
    organization_kind_int bigint,
    organization_kind_currency numeric(39,0),
    organization_kind_real_bits bigint,
    organization_kind_ratio_bits bigint,
    organization_kind_ratio_min_bits bigint,
    organization_kind_ratio_max_bits bigint,
    organization_kind_bool boolean,
    organization_kind_enum_type text COLLATE pg_catalog."C",
    organization_kind_enum_member text COLLATE pg_catalog."C",
    organization_kind_stable_key bytea,
    CONSTRAINT organization_state_v1_check CHECK ((((organization_kind_tag = 1) AND (organization_kind_int IS NOT NULL) AND (organization_kind_currency IS NULL) AND (organization_kind_real_bits IS NULL) AND (organization_kind_ratio_bits IS NULL) AND (organization_kind_ratio_min_bits IS NULL) AND (organization_kind_ratio_max_bits IS NULL) AND (organization_kind_bool IS NULL) AND (organization_kind_enum_type IS NULL) AND (organization_kind_enum_member IS NULL) AND (organization_kind_stable_key IS NULL)) OR ((organization_kind_tag = 2) AND (organization_kind_int IS NULL) AND (organization_kind_currency IS NOT NULL) AND (organization_kind_real_bits IS NULL) AND (organization_kind_ratio_bits IS NULL) AND (organization_kind_ratio_min_bits IS NULL) AND (organization_kind_ratio_max_bits IS NULL) AND (organization_kind_bool IS NULL) AND (organization_kind_enum_type IS NULL) AND (organization_kind_enum_member IS NULL) AND (organization_kind_stable_key IS NULL)) OR ((organization_kind_tag = 3) AND (organization_kind_int IS NULL) AND (organization_kind_currency IS NULL) AND (organization_kind_real_bits IS NOT NULL) AND (organization_kind_ratio_bits IS NULL) AND (organization_kind_ratio_min_bits IS NULL) AND (organization_kind_ratio_max_bits IS NULL) AND (organization_kind_bool IS NULL) AND (organization_kind_enum_type IS NULL) AND (organization_kind_enum_member IS NULL) AND (organization_kind_stable_key IS NULL)) OR ((organization_kind_tag = 4) AND (organization_kind_int IS NULL) AND (organization_kind_currency IS NULL) AND (organization_kind_real_bits IS NULL) AND (organization_kind_ratio_bits IS NOT NULL) AND (organization_kind_bool IS NULL) AND (organization_kind_enum_type IS NULL) AND (organization_kind_enum_member IS NULL) AND (organization_kind_stable_key IS NULL)) OR ((organization_kind_tag = 5) AND (organization_kind_int IS NULL) AND (organization_kind_currency IS NULL) AND (organization_kind_real_bits IS NULL) AND (organization_kind_ratio_bits IS NULL) AND (organization_kind_ratio_min_bits IS NULL) AND (organization_kind_ratio_max_bits IS NULL) AND (organization_kind_bool IS NOT NULL) AND (organization_kind_enum_type IS NULL) AND (organization_kind_enum_member IS NULL) AND (organization_kind_stable_key IS NULL)) OR ((organization_kind_tag = 6) AND (organization_kind_int IS NULL) AND (organization_kind_currency IS NULL) AND (organization_kind_real_bits IS NULL) AND (organization_kind_ratio_bits IS NULL) AND (organization_kind_ratio_min_bits IS NULL) AND (organization_kind_ratio_max_bits IS NULL) AND (organization_kind_bool IS NULL) AND (organization_kind_enum_type IS NOT NULL) AND (organization_kind_enum_member IS NOT NULL) AND (organization_kind_stable_key IS NULL)) OR (((organization_kind_tag >= 7) AND (organization_kind_tag <= 9)) AND (organization_kind_int IS NULL) AND (organization_kind_currency IS NULL) AND (organization_kind_real_bits IS NULL) AND (organization_kind_ratio_bits IS NULL) AND (organization_kind_ratio_min_bits IS NULL) AND (organization_kind_ratio_max_bits IS NULL) AND (organization_kind_bool IS NULL) AND (organization_kind_enum_type IS NULL) AND (organization_kind_enum_member IS NULL) AND (organization_kind_stable_key IS NOT NULL)))),
    CONSTRAINT organization_state_v1_organization_kind_tag_check CHECK (((organization_kind_tag >= 1) AND (organization_kind_tag <= 9))),
    CONSTRAINT organization_state_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.organization_territory_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    organization_id bytea NOT NULL,
    "position" integer NOT NULL,
    territory_id bytea NOT NULL,
    CONSTRAINT organization_territory_v1_position_check CHECK (("position" >= 0)),
    CONSTRAINT organization_territory_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

-- Exact typed territory fieldsets live once; periods retain integer membership.
CREATE TABLE babylon_state.territory_definition_v1 (
    campaign_id uuid NOT NULL,
    definition_id bigint NOT NULL CHECK (definition_id >= 0),
    first_tick bigint NOT NULL CHECK (first_tick >= 0),
    marker_tick bigint GENERATED ALWAYS AS (NULLIF(first_tick, 0)) STORED,
    territory_id bytea NOT NULL,
    field_count integer NOT NULL CHECK (field_count >= 0),
    canonical_sha256 bytea NOT NULL CHECK (octet_length(canonical_sha256) = 32),
    creation_xid xid8 NOT NULL DEFAULT pg_catalog.pg_current_xact_id(),
    PRIMARY KEY (campaign_id, definition_id)
);
-- A digest narrows candidates. Rust compares complete canonical typed rows.
CREATE INDEX territory_definition_digest_bucket_v1
    ON babylon_state.territory_definition_v1 (campaign_id, canonical_sha256);
CREATE TABLE babylon_state.territory_definition_field_v1 (
    campaign_id uuid NOT NULL,
    definition_id bigint NOT NULL,
    "position" integer NOT NULL,
    field_name text NOT NULL COLLATE pg_catalog."C",
    value_tag smallint NOT NULL,
    int_value bigint,
    currency_value numeric(39,0),
    real_bits bigint,
    ratio_bits bigint,
    ratio_min_bits bigint,
    ratio_max_bits bigint,
    bool_value boolean,
    enum_type text COLLATE pg_catalog."C",
    enum_member text COLLATE pg_catalog."C",
    stable_key bytea,
    CONSTRAINT territory_definition_field_v1_check CHECK ((((value_tag = 1) AND (int_value IS NOT NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 2) AND (int_value IS NULL) AND (currency_value IS NOT NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 3) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NOT NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 4) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NOT NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 5) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NOT NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 6) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NOT NULL) AND (enum_member IS NOT NULL) AND (stable_key IS NULL)) OR (((value_tag >= 7) AND (value_tag <= 9)) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NOT NULL)))),
    CONSTRAINT territory_definition_field_v1_position_check CHECK (("position" >= 0)),
    CONSTRAINT territory_definition_field_v1_value_tag_check CHECK (((value_tag >= 1) AND (value_tag <= 9))),
    PRIMARY KEY (campaign_id, definition_id, "position"),
    UNIQUE (campaign_id, definition_id, field_name),
    FOREIGN KEY (campaign_id, definition_id)
        REFERENCES babylon_state.territory_definition_v1
);

CREATE TABLE babylon_state.territory_tick_manifest_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL CHECK (resolve_tick >= 1),
    territory_count bigint NOT NULL CHECK (territory_count BETWEEN 0 AND 262144),
    PRIMARY KEY (campaign_id, resolve_tick)
);
CREATE TABLE babylon_state.territory_tick_membership_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL CHECK (resolve_tick >= 1),
    definition_id bigint NOT NULL,
    PRIMARY KEY (campaign_id, resolve_tick, definition_id),
    FOREIGN KEY (campaign_id, definition_id)
        REFERENCES babylon_state.territory_definition_v1,
    FOREIGN KEY (campaign_id, resolve_tick)
        REFERENCES babylon_state.territory_tick_manifest_v1
        DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.tick_action_batch_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    layout_version smallint NOT NULL,
    action_batch_digest bytea NOT NULL,
    exact_action_batch_bytes bytea NOT NULL,
    CONSTRAINT tick_action_batch_v1_action_batch_digest_check CHECK ((octet_length(action_batch_digest) = 32)),
    CONSTRAINT tick_action_batch_v1_exact_action_batch_bytes_check CHECK (((octet_length(exact_action_batch_bytes) >= 55) AND (octet_length(exact_action_batch_bytes) <= 9302326))),
    CONSTRAINT tick_action_batch_v1_layout_version_check CHECK ((layout_version = 1)),
    CONSTRAINT tick_action_batch_v1_resolve_tick_check CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.tick_choice_receipt_branch_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    encounter_ordinal bigint NOT NULL,
    "position" bigint NOT NULL,
    outcome_member text NOT NULL COLLATE pg_catalog."C",
    mass_nanounits numeric(20,0) NOT NULL,
    ticket_start numeric(20,0) NOT NULL,
    ticket_end_exclusive numeric(20,0) NOT NULL,
    ticket_count numeric(20,0) NOT NULL,
    CONSTRAINT tick_choice_receipt_branch_v1_count CHECK (((ticket_count >= (0)::numeric) AND (ticket_count <= '18446744073709551616'::numeric))),
    CONSTRAINT tick_choice_receipt_branch_v1_end CHECK (((ticket_end_exclusive >= (0)::numeric) AND (ticket_end_exclusive <= '18446744073709551616'::numeric))),
    CONSTRAINT tick_choice_receipt_branch_v1_interval CHECK (((ticket_end_exclusive >= ticket_start) AND (ticket_count = (ticket_end_exclusive - ticket_start)))),
    CONSTRAINT tick_choice_receipt_branch_v1_mass CHECK (((mass_nanounits >= (0)::numeric) AND (mass_nanounits <= '18446744073709551615'::numeric))),
    CONSTRAINT tick_choice_receipt_branch_v1_position CHECK ((("position" >= 0) AND ("position" <= '4294967295'::bigint))),
    CONSTRAINT tick_choice_receipt_branch_v1_positive_mass CHECK ((((mass_nanounits = (0)::numeric) AND (ticket_count = (0)::numeric)) OR ((mass_nanounits > (0)::numeric) AND (ticket_count > (0)::numeric)))),
    CONSTRAINT tick_choice_receipt_branch_v1_start CHECK (((ticket_start >= (0)::numeric) AND (ticket_start <= '18446744073709551616'::numeric)))
);

CREATE TABLE babylon_state.tick_choice_receipt_carrier_element_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    encounter_ordinal bigint NOT NULL,
    "position" bigint NOT NULL,
    stable_element bytea NOT NULL,
    CONSTRAINT tick_choice_receipt_carrier_element_v1_position CHECK ((("position" >= 0) AND ("position" <= '4294967295'::bigint)))
);

CREATE TABLE babylon_state.tick_choice_receipt_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    encounter_ordinal bigint NOT NULL,
    rule_id text NOT NULL COLLATE pg_catalog."C",
    sample text NOT NULL COLLATE pg_catalog."C",
    slot bigint NOT NULL,
    outcome_enum text NOT NULL COLLATE pg_catalog."C",
    stable_carrier bytea NOT NULL,
    draw_ticket numeric(20,0) NOT NULL,
    selected_outcome text NOT NULL COLLATE pg_catalog."C",
    allocation_digest bytea NOT NULL,
    instance_digest bytea NOT NULL,
    CONSTRAINT tick_choice_receipt_v1_digests CHECK (((octet_length(allocation_digest) = 32) AND (octet_length(instance_digest) = 32))),
    CONSTRAINT tick_choice_receipt_v1_draw CHECK (((draw_ticket >= (0)::numeric) AND (draw_ticket <= '18446744073709551615'::numeric))),
    CONSTRAINT tick_choice_receipt_v1_encounter CHECK (((encounter_ordinal >= 0) AND (encounter_ordinal <= '4294967295'::bigint))),
    CONSTRAINT tick_choice_receipt_v1_resolve_tick CHECK ((resolve_tick >= 1)),
    CONSTRAINT tick_choice_receipt_v1_slot CHECK (((slot >= 0) AND (slot <= '4294967295'::bigint)))
);

CREATE TABLE babylon_state.tick_commit (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    envelope_layout_version smallint NOT NULL,
    tick_content_hash bytea NOT NULL,
    envelope_digest bytea NOT NULL,
    CONSTRAINT tick_commit_content_hash_length CHECK ((octet_length(tick_content_hash) = 32)),
    CONSTRAINT tick_commit_envelope_digest_length CHECK ((octet_length(envelope_digest) = 32)),
    CONSTRAINT tick_commit_envelope_layout_v3 CHECK ((envelope_layout_version = 3)),
    CONSTRAINT tick_commit_resolve_tick_sql_range CHECK ((resolve_tick >= 1))
);

CREATE TABLE babylon_state.world_register_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    register_name text NOT NULL COLLATE pg_catalog."C",
    value_tag smallint NOT NULL,
    int_value bigint,
    currency_value numeric(39,0),
    real_bits bigint,
    ratio_bits bigint,
    ratio_min_bits bigint,
    ratio_max_bits bigint,
    bool_value boolean,
    enum_type text COLLATE pg_catalog."C",
    enum_member text COLLATE pg_catalog."C",
    stable_key bytea,
    CONSTRAINT world_register_v1_check CHECK ((((value_tag = 1) AND (int_value IS NOT NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 2) AND (int_value IS NULL) AND (currency_value IS NOT NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 3) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NOT NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 4) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NOT NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 5) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NOT NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NULL)) OR ((value_tag = 6) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NOT NULL) AND (enum_member IS NOT NULL) AND (stable_key IS NULL)) OR (((value_tag >= 7) AND (value_tag <= 9)) AND (int_value IS NULL) AND (currency_value IS NULL) AND (real_bits IS NULL) AND (ratio_bits IS NULL) AND (ratio_min_bits IS NULL) AND (ratio_max_bits IS NULL) AND (bool_value IS NULL) AND (enum_type IS NULL) AND (enum_member IS NULL) AND (stable_key IS NOT NULL)))),
    CONSTRAINT world_register_v1_resolve_tick_check CHECK ((resolve_tick >= 1)),
    CONSTRAINT world_register_v1_value_tag_check CHECK (((value_tag >= 1) AND (value_tag <= 9)))
);

CREATE TRIGGER tick_event_v2_marker_lock BEFORE INSERT ON babylon_state.tick_commit FOR EACH ROW EXECUTE FUNCTION babylon_state.lock_tick_event_marker_v2();

ALTER TABLE ONLY babylon_meta.breadcrumb
    ADD CONSTRAINT breadcrumb_pkey PRIMARY KEY (campaign_id, "position");

ALTER TABLE ONLY babylon_meta.campaign
    ADD CONSTRAINT campaign_pkey PRIMARY KEY (campaign_id);

ALTER TABLE ONLY babylon_meta.campaign
    ADD CONSTRAINT campaign_slug_key UNIQUE (slug);

ALTER TABLE ONLY babylon_meta.jumplist
    ADD CONSTRAINT jumplist_pkey PRIMARY KEY (campaign_id, "position");

ALTER TABLE ONLY babylon_meta.watchlist
    ADD CONSTRAINT watchlist_campaign_id_entity_id_key UNIQUE (campaign_id, entity_id);

ALTER TABLE ONLY babylon_meta.watchlist
    ADD CONSTRAINT watchlist_pkey PRIMARY KEY (campaign_id, "position");

ALTER TABLE ONLY babylon_ref.county_h3_land_area
    ADD CONSTRAINT county_h3_land_area_pkey PRIMARY KEY (ref_digest, cell_id, county_geoid);

ALTER TABLE ONLY babylon_ref.county_identity
    ADD CONSTRAINT county_identity_county_id_key UNIQUE (ref_digest, county_id);

ALTER TABLE ONLY babylon_ref.county_identity
    ADD CONSTRAINT county_identity_pkey PRIMARY KEY (ref_digest, county_geoid);

ALTER TABLE ONLY babylon_ref.county_place_h3_land_area
    ADD CONSTRAINT county_place_h3_land_area_pkey PRIMARY KEY (ref_digest, cell_id, county_geoid, place_geoid);

ALTER TABLE ONLY babylon_ref.h3_cell
    ADD CONSTRAINT h3_cell_pkey PRIMARY KEY (cell_id);

ALTER TABLE ONLY babylon_ref.h3_land_fraction
    ADD CONSTRAINT h3_land_fraction_pkey PRIMARY KEY (ref_digest, cell_id);

ALTER TABLE ONLY babylon_ref.h3_population_count
    ADD CONSTRAINT h3_population_count_pkey PRIMARY KEY (ref_digest, cell_id);

ALTER TABLE ONLY babylon_ref.h3_reference_cohort
    ADD CONSTRAINT h3_reference_cohort_artifact_identity UNIQUE (format_version, artifact_digest);

ALTER TABLE ONLY babylon_ref.h3_reference_cohort
    ADD CONSTRAINT h3_reference_cohort_pkey PRIMARY KEY (ref_digest);

ALTER TABLE ONLY babylon_ref.h3_reference_membership
    ADD CONSTRAINT h3_reference_membership_pkey PRIMARY KEY (ref_digest, cell_id);

ALTER TABLE ONLY babylon_ref.h3_workplace_count
    ADD CONSTRAINT h3_workplace_count_pkey PRIMARY KEY (ref_digest, cell_id);

ALTER TABLE ONLY babylon_ref.place_identity
    ADD CONSTRAINT place_identity_pkey PRIMARY KEY (ref_digest, place_geoid);

ALTER TABLE ONLY babylon_ref.reference_product
    ADD CONSTRAINT reference_product_pkey PRIMARY KEY (ref_digest, product_code);

ALTER TABLE ONLY babylon_state.archive_dirty_receipt_v1
    ADD CONSTRAINT archive_dirty_receipt_v1_pkey PRIMARY KEY (campaign_id, resolve_tick);

ALTER TABLE ONLY babylon_state.campaign_foundation
    ADD CONSTRAINT campaign_foundation_pkey PRIMARY KEY (campaign_id);

ALTER TABLE ONLY babylon_state.campaign
    ADD CONSTRAINT campaign_pkey PRIMARY KEY (campaign_id);

ALTER TABLE ONLY babylon_state.checkpoint_manifest
    ADD CONSTRAINT checkpoint_manifest_pkey PRIMARY KEY (campaign_id, resolve_tick);

ALTER TABLE ONLY babylon_state.checkpoint_section_v1
    ADD CONSTRAINT checkpoint_section_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, section_tag, ordinal);

ALTER TABLE ONLY babylon_state.graph_edge_f64_v1
    ADD CONSTRAINT graph_edge_f64_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, edge_type, source_local_name, target_local_name, qname);

ALTER TABLE ONLY babylon_state.graph_edge_v1
    ADD CONSTRAINT graph_edge_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, edge_type, source_local_name, target_local_name);

ALTER TABLE ONLY babylon_state.graph_hyperedge_f64_v1
    ADD CONSTRAINT graph_hyperedge_f64_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, local_name, qname);

ALTER TABLE ONLY babylon_state.graph_hyperedge_member_v1
    ADD CONSTRAINT graph_hyperedge_member_v1_campaign_id_resolve_tick_local_na_key UNIQUE (campaign_id, resolve_tick, local_name, member);

ALTER TABLE ONLY babylon_state.graph_hyperedge_member_v1
    ADD CONSTRAINT graph_hyperedge_member_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, local_name, "position");

ALTER TABLE ONLY babylon_state.graph_hyperedge_v1
    ADD CONSTRAINT graph_hyperedge_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, local_name);

ALTER TABLE ONLY babylon_state.graph_node_currency_v1
    ADD CONSTRAINT graph_node_currency_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, local_name, qname);

ALTER TABLE ONLY babylon_state.hex_state_delta_v1
    ADD CONSTRAINT hex_state_delta_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, cell_id);

ALTER TABLE ONLY babylon_state.organization_state_field_v1
    ADD CONSTRAINT organization_state_field_v1_campaign_id_resolve_tick_organi_key UNIQUE (campaign_id, resolve_tick, organization_id, field_name);

ALTER TABLE ONLY babylon_state.organization_state_field_v1
    ADD CONSTRAINT organization_state_field_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, organization_id, "position");

ALTER TABLE ONLY babylon_state.organization_state_v1
    ADD CONSTRAINT organization_state_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, organization_id);

ALTER TABLE ONLY babylon_state.organization_territory_v1
    ADD CONSTRAINT organization_territory_v1_campaign_id_resolve_tick_organiza_key UNIQUE (campaign_id, resolve_tick, organization_id, territory_id);

ALTER TABLE ONLY babylon_state.organization_territory_v1
    ADD CONSTRAINT organization_territory_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, organization_id, "position");

ALTER TABLE ONLY babylon_state.tick_action_batch_v1
    ADD CONSTRAINT tick_action_batch_v1_pkey PRIMARY KEY (campaign_id, resolve_tick);

ALTER TABLE ONLY babylon_state.tick_choice_receipt_branch_v1
    ADD CONSTRAINT tick_choice_receipt_branch_v1_member_key UNIQUE (campaign_id, resolve_tick, encounter_ordinal, outcome_member);

ALTER TABLE ONLY babylon_state.tick_choice_receipt_branch_v1
    ADD CONSTRAINT tick_choice_receipt_branch_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, encounter_ordinal, "position");

ALTER TABLE ONLY babylon_state.tick_choice_receipt_carrier_element_v1
    ADD CONSTRAINT tick_choice_receipt_carrier_element_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, encounter_ordinal, "position");

ALTER TABLE ONLY babylon_state.tick_choice_receipt_v1
    ADD CONSTRAINT tick_choice_receipt_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, encounter_ordinal);

ALTER TABLE ONLY babylon_state.tick_commit
    ADD CONSTRAINT tick_commit_pkey PRIMARY KEY (campaign_id, resolve_tick);

ALTER TABLE ONLY babylon_state.world_register_v1
    ADD CONSTRAINT world_register_v1_pkey PRIMARY KEY (campaign_id, resolve_tick, register_name);

CREATE INDEX county_h3_land_area_county_idx ON babylon_ref.county_h3_land_area USING btree (ref_digest, county_geoid, cell_id);

CREATE INDEX county_place_h3_land_area_place_idx ON babylon_ref.county_place_h3_land_area USING btree (ref_digest, place_geoid, cell_id, county_geoid);

CREATE INDEX h3_reference_membership_cell_id_idx ON babylon_ref.h3_reference_membership USING btree (cell_id, ref_digest);

CREATE UNIQUE INDEX h3_reference_membership_origin_key ON babylon_ref.h3_reference_membership USING btree (ref_digest, cell_id, origin);

CREATE CONSTRAINT TRIGGER tick_choice_receipt_branch_v1_continuity AFTER INSERT OR DELETE OR UPDATE ON babylon_state.tick_choice_receipt_branch_v1 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.verify_tick_choice_receipt_v1_continuity();

CREATE CONSTRAINT TRIGGER tick_choice_receipt_carrier_element_v1_continuity AFTER INSERT OR DELETE OR UPDATE ON babylon_state.tick_choice_receipt_carrier_element_v1 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.verify_tick_choice_receipt_v1_continuity();

CREATE CONSTRAINT TRIGGER tick_choice_receipt_v1_continuity AFTER INSERT OR DELETE OR UPDATE ON babylon_state.tick_choice_receipt_v1 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.verify_tick_choice_receipt_v1_continuity();





ALTER TABLE ONLY babylon_meta.breadcrumb
    ADD CONSTRAINT breadcrumb_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES babylon_meta.campaign(campaign_id) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_meta.jumplist
    ADD CONSTRAINT jumplist_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES babylon_meta.campaign(campaign_id) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_meta.watchlist
    ADD CONSTRAINT watchlist_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES babylon_meta.campaign(campaign_id) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_ref.county_h3_land_area
    ADD CONSTRAINT county_h3_land_area_county_fkey FOREIGN KEY (ref_digest, county_geoid) REFERENCES babylon_ref.county_identity(ref_digest, county_geoid) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.county_h3_land_area
    ADD CONSTRAINT county_h3_land_area_membership_fkey FOREIGN KEY (ref_digest, cell_id, membership_origin) REFERENCES babylon_ref.h3_reference_membership(ref_digest, cell_id, origin) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.county_h3_land_area
    ADD CONSTRAINT county_h3_land_area_product_fkey FOREIGN KEY (ref_digest, product_code) REFERENCES babylon_ref.reference_product(ref_digest, product_code) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.county_identity
    ADD CONSTRAINT county_identity_product_fkey FOREIGN KEY (ref_digest, product_code) REFERENCES babylon_ref.reference_product(ref_digest, product_code) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.county_place_h3_land_area
    ADD CONSTRAINT county_place_h3_land_area_county_cell_fkey FOREIGN KEY (ref_digest, cell_id, county_geoid) REFERENCES babylon_ref.county_h3_land_area(ref_digest, cell_id, county_geoid) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.county_place_h3_land_area
    ADD CONSTRAINT county_place_h3_land_area_membership_fkey FOREIGN KEY (ref_digest, cell_id, membership_origin) REFERENCES babylon_ref.h3_reference_membership(ref_digest, cell_id, origin) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.county_place_h3_land_area
    ADD CONSTRAINT county_place_h3_land_area_place_fkey FOREIGN KEY (ref_digest, place_geoid) REFERENCES babylon_ref.place_identity(ref_digest, place_geoid) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.county_place_h3_land_area
    ADD CONSTRAINT county_place_h3_land_area_product_fkey FOREIGN KEY (ref_digest, product_code) REFERENCES babylon_ref.reference_product(ref_digest, product_code) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_cell
    ADD CONSTRAINT h3_cell_ancestor_r4_fkey FOREIGN KEY (ancestor_r4) REFERENCES babylon_ref.h3_cell(cell_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_cell
    ADD CONSTRAINT h3_cell_ancestor_r5_fkey FOREIGN KEY (ancestor_r5) REFERENCES babylon_ref.h3_cell(cell_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_cell
    ADD CONSTRAINT h3_cell_ancestor_r6_fkey FOREIGN KEY (ancestor_r6) REFERENCES babylon_ref.h3_cell(cell_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_cell
    ADD CONSTRAINT h3_cell_ancestor_r7_fkey FOREIGN KEY (ancestor_r7) REFERENCES babylon_ref.h3_cell(cell_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_cell
    ADD CONSTRAINT h3_cell_immediate_parent_fkey FOREIGN KEY (immediate_parent) REFERENCES babylon_ref.h3_cell(cell_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_land_fraction
    ADD CONSTRAINT h3_land_fraction_county_fkey FOREIGN KEY (ref_digest, source_county_geoid) REFERENCES babylon_ref.county_identity(ref_digest, county_geoid) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_land_fraction
    ADD CONSTRAINT h3_land_fraction_membership_fkey FOREIGN KEY (ref_digest, cell_id, membership_origin) REFERENCES babylon_ref.h3_reference_membership(ref_digest, cell_id, origin) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_land_fraction
    ADD CONSTRAINT h3_land_fraction_product_fkey FOREIGN KEY (ref_digest, product_code) REFERENCES babylon_ref.reference_product(ref_digest, product_code) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_population_count
    ADD CONSTRAINT h3_population_count_membership_fkey FOREIGN KEY (ref_digest, cell_id, membership_origin) REFERENCES babylon_ref.h3_reference_membership(ref_digest, cell_id, origin) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_population_count
    ADD CONSTRAINT h3_population_count_product_fkey FOREIGN KEY (ref_digest, product_code) REFERENCES babylon_ref.reference_product(ref_digest, product_code) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_reference_membership
    ADD CONSTRAINT h3_reference_membership_cell_fkey FOREIGN KEY (cell_id) REFERENCES babylon_ref.h3_cell(cell_id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_reference_membership
    ADD CONSTRAINT h3_reference_membership_cohort_fkey FOREIGN KEY (ref_digest) REFERENCES babylon_ref.h3_reference_cohort(ref_digest) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_workplace_count
    ADD CONSTRAINT h3_workplace_count_membership_fkey FOREIGN KEY (ref_digest, cell_id, membership_origin) REFERENCES babylon_ref.h3_reference_membership(ref_digest, cell_id, origin) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.h3_workplace_count
    ADD CONSTRAINT h3_workplace_count_product_fkey FOREIGN KEY (ref_digest, product_code) REFERENCES babylon_ref.reference_product(ref_digest, product_code) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.place_identity
    ADD CONSTRAINT place_identity_product_fkey FOREIGN KEY (ref_digest, product_code) REFERENCES babylon_ref.reference_product(ref_digest, product_code) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_ref.reference_product
    ADD CONSTRAINT reference_product_cohort_fkey FOREIGN KEY (ref_digest) REFERENCES babylon_ref.h3_reference_cohort(ref_digest) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_state.campaign_foundation
    ADD CONSTRAINT campaign_foundation_campaign_fkey FOREIGN KEY (campaign_id) REFERENCES babylon_state.campaign(campaign_id);

ALTER TABLE ONLY babylon_state.campaign
    ADD CONSTRAINT campaign_local_h3_reference_fkey FOREIGN KEY (local_h3_ref_digest) REFERENCES babylon_ref.h3_reference_cohort(ref_digest) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_state.graph_hyperedge_member_v1
    ADD CONSTRAINT graph_hyperedge_member_v1_campaign_id_resolve_tick_local_n_fkey FOREIGN KEY (campaign_id, resolve_tick, local_name) REFERENCES babylon_state.graph_hyperedge_v1(campaign_id, resolve_tick, local_name) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_state.organization_state_field_v1
    ADD CONSTRAINT organization_state_field_v1_campaign_id_resolve_tick_organ_fkey FOREIGN KEY (campaign_id, resolve_tick, organization_id) REFERENCES babylon_state.organization_state_v1(campaign_id, resolve_tick, organization_id) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_state.organization_territory_v1
    ADD CONSTRAINT organization_territory_v1_campaign_id_resolve_tick_organiz_fkey FOREIGN KEY (campaign_id, resolve_tick, organization_id) REFERENCES babylon_state.organization_state_v1(campaign_id, resolve_tick, organization_id) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_state.tick_action_batch_v1
    ADD CONSTRAINT tick_action_batch_v1_campaign_id_resolve_tick_fkey FOREIGN KEY (campaign_id, resolve_tick) REFERENCES babylon_state.tick_commit(campaign_id, resolve_tick) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_state.tick_choice_receipt_branch_v1
    ADD CONSTRAINT tick_choice_receipt_branch_v1_parent_fkey FOREIGN KEY (campaign_id, resolve_tick, encounter_ordinal) REFERENCES babylon_state.tick_choice_receipt_v1(campaign_id, resolve_tick, encounter_ordinal) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_state.tick_choice_receipt_carrier_element_v1
    ADD CONSTRAINT tick_choice_receipt_carrier_element_v1_parent_fkey FOREIGN KEY (campaign_id, resolve_tick, encounter_ordinal) REFERENCES babylon_state.tick_choice_receipt_v1(campaign_id, resolve_tick, encounter_ordinal) ON DELETE CASCADE;

ALTER TABLE ONLY babylon_state.tick_choice_receipt_v1
    ADD CONSTRAINT tick_choice_receipt_v1_tick_fkey FOREIGN KEY (campaign_id, resolve_tick) REFERENCES babylon_state.tick_commit(campaign_id, resolve_tick) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE ONLY babylon_state.tick_commit
    ADD CONSTRAINT tick_commit_campaign_fkey FOREIGN KEY (campaign_id) REFERENCES babylon_state.campaign(campaign_id) DEFERRABLE INITIALLY DEFERRED;

REVOKE ALL ON FUNCTION babylon_state.verify_tick_choice_receipt_v1_continuity() FROM PUBLIC;


ALTER TABLE babylon_state.territory_definition_v1
    ADD CONSTRAINT territory_definition_campaign_v1 FOREIGN KEY (campaign_id)
        REFERENCES babylon_state.campaign(campaign_id),
    ADD CONSTRAINT territory_definition_marker_v1 FOREIGN KEY (campaign_id, marker_tick)
        REFERENCES babylon_state.tick_commit(campaign_id, resolve_tick)
        DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE babylon_state.territory_tick_manifest_v1
    ADD CONSTRAINT territory_manifest_marker_v1 FOREIGN KEY (campaign_id, resolve_tick)
        REFERENCES babylon_state.tick_commit(campaign_id, resolve_tick)
        DEFERRABLE INITIALLY DEFERRED;

CREATE VIEW babylon_state.territory_state_v1 AS
SELECT m.campaign_id, m.resolve_tick, d.territory_id, d.field_count, d.canonical_sha256
FROM babylon_state.territory_tick_membership_v1 m
JOIN babylon_state.territory_definition_v1 d USING (campaign_id, definition_id)
JOIN babylon_state.tick_commit t USING (campaign_id, resolve_tick);
CREATE VIEW babylon_state.territory_state_field_v1 AS
SELECT m.campaign_id, m.resolve_tick, d.territory_id, f.position, f.field_name,
       f.value_tag, f.int_value, f.currency_value, f.real_bits, f.ratio_bits,
       f.ratio_min_bits, f.ratio_max_bits, f.bool_value, f.enum_type,
       f.enum_member, f.stable_key
FROM babylon_state.territory_tick_membership_v1 m
JOIN babylon_state.territory_definition_v1 d USING (campaign_id, definition_id)
JOIN babylon_state.territory_definition_field_v1 f USING (campaign_id, definition_id)
JOIN babylon_state.tick_commit t USING (campaign_id, resolve_tick);
REVOKE ALL ON babylon_state.territory_definition_v1,
    babylon_state.territory_definition_field_v1,
    babylon_state.territory_tick_manifest_v1,
    babylon_state.territory_tick_membership_v1,
    babylon_state.territory_state_v1,
    babylon_state.territory_state_field_v1 FROM PUBLIC;

CREATE TABLE babylon_state.material_campaign_foundation_v3 (
    campaign_id uuid PRIMARY KEY REFERENCES babylon_state.campaign(campaign_id),
    preset_id text NOT NULL CHECK (octet_length(preset_id) BETWEEN 1 AND 128),
    duration_kind text NOT NULL,
    final_period bigint,
    CONSTRAINT material_campaign_duration CHECK (
        (duration_kind = 'continuous' AND final_period IS NULL)
        OR (duration_kind = 'finite' AND final_period IS NOT NULL AND final_period > 0)
    ),
    content_sha256 bytea NOT NULL CHECK (octet_length(content_sha256) = 32),
    initial_register_bytes bytea NOT NULL CHECK (octet_length(initial_register_bytes) <= 1000000000),
    foundation_sha256 bytea NOT NULL CHECK (octet_length(foundation_sha256) = 32)
);
CREATE TABLE babylon_state.material_tick_v3 (
    campaign_id uuid NOT NULL REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id),
    resolve_tick bigint NOT NULL CHECK (resolve_tick > 0),
    identity_bytes bytea NOT NULL CHECK (octet_length(identity_bytes) <= 1024),
    register_storage_bytes bytea NOT NULL CHECK (octet_length(register_storage_bytes) <= 1003922634),
    receipt_storage_bytes bytea NOT NULL CHECK (octet_length(receipt_storage_bytes) <= 872614764),
    lookup_delta_bytes bytea NOT NULL CHECK (octet_length(lookup_delta_bytes) <= 1003907274),
    PRIMARY KEY (campaign_id, resolve_tick)
);
CREATE FUNCTION babylon_state.require_material_tick_v3() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF NEW.envelope_layout_version <> 3 THEN
        RAISE EXCEPTION 'material campaign version mismatch';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM babylon_state.material_tick_v3 t WHERE t.campaign_id = NEW.campaign_id AND t.resolve_tick = NEW.resolve_tick) THEN
        RAISE EXCEPTION 'material tick missing before commit marker';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER material_tick_marker_v3 BEFORE INSERT ON babylon_state.tick_commit FOR EACH ROW EXECUTE FUNCTION babylon_state.require_material_tick_v3();
REVOKE ALL ON FUNCTION babylon_state.require_material_tick_v3() FROM PUBLIC;
REVOKE ALL ON babylon_state.material_campaign_foundation_v3, babylon_state.material_tick_v3 FROM PUBLIC;

CREATE TABLE babylon_meta.territory_county_map_v1 (
    campaign_id UUID NOT NULL,
    territory_local_name TEXT COLLATE pg_catalog."C" NOT NULL CHECK (
        pg_catalog.octet_length(territory_local_name) BETWEEN 1 AND 256
    ),
    county_geoid TEXT COLLATE pg_catalog."C" NOT NULL CHECK (county_geoid ~ '^[0-9]{5}$'),
    PRIMARY KEY (campaign_id, territory_local_name),
    FOREIGN KEY (campaign_id) REFERENCES babylon_meta.campaign(campaign_id) ON DELETE CASCADE
);
REVOKE ALL ON TABLE babylon_meta.territory_county_map_v1 FROM PUBLIC;

CREATE TABLE babylon_meta.current_schema (
    singleton BOOLEAN PRIMARY KEY CHECK (singleton),
    schema_sha256 BYTEA NOT NULL CHECK (octet_length(schema_sha256) = 32)
);
REVOKE ALL ON babylon_meta.current_schema FROM PUBLIC;

-- Immutable accepted organizer inputs. The marker transaction consumes one
-- period's accepted input together with its authoritative register and reports.
CREATE TABLE babylon_state.organizer_command_v1 (
    campaign_id UUID NOT NULL REFERENCES babylon_state.campaign(campaign_id) ON DELETE CASCADE,
    nonce BYTEA NOT NULL CHECK (octet_length(nonce)=16),
    resolves_period BIGINT NOT NULL CHECK (resolves_period > 0),
    command_bytes BYTEA NOT NULL CHECK (octet_length(command_bytes) BETWEEN 1 AND 8192),
    commitment_bytes BYTEA NOT NULL CHECK (octet_length(commitment_bytes) BETWEEN 1 AND 8192),
    commitment_sha256 BYTEA NOT NULL CHECK (octet_length(commitment_sha256)=32),
    consumed_period BIGINT CHECK (consumed_period=resolves_period),
    PRIMARY KEY (campaign_id,nonce),
    UNIQUE (campaign_id,resolves_period),
    FOREIGN KEY (campaign_id,consumed_period) REFERENCES babylon_state.tick_commit(campaign_id,resolve_tick) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.organizer_subject_v1 (
    campaign_id UUID NOT NULL REFERENCES babylon_state.campaign(campaign_id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL CHECK (actor_id ~ '^[1-9][0-9]{0,19}$'),
    subject_kind TEXT NOT NULL CHECK (subject_kind IN ('workplace','organization')),
    subject_id TEXT NOT NULL CHECK (subject_id ~ '^[1-9][0-9]{0,19}$'),
    title TEXT NOT NULL CHECK (octet_length(title) BETWEEN 1 AND 4096),
    PRIMARY KEY (campaign_id,actor_id,subject_kind,subject_id)
);
CREATE TABLE babylon_state.organizer_observation_v1 (
    campaign_id UUID NOT NULL REFERENCES babylon_state.campaign(campaign_id) ON DELETE CASCADE,
    observation_id BYTEA NOT NULL CHECK (octet_length(observation_id)=32),
    actor_id TEXT NOT NULL CHECK (actor_id ~ '^[1-9][0-9]{0,19}$'),
    subject_id TEXT NOT NULL CHECK (subject_id ~ '^[1-9][0-9]{0,19}$'),
    observed_period BIGINT NOT NULL CHECK (observed_period >= 0),
    acquired_period BIGINT NOT NULL CHECK (acquired_period >= observed_period),
    observation_bytes BYTEA NOT NULL CHECK (octet_length(observation_bytes) BETWEEN 1 AND 8192),
    PRIMARY KEY (campaign_id,observation_id)
);
CREATE TABLE babylon_state.organizer_receipt_v1 (
    campaign_id UUID NOT NULL REFERENCES babylon_state.campaign(campaign_id) ON DELETE CASCADE,
    receipt_id BYTEA NOT NULL CHECK (octet_length(receipt_id)=32),
    actor_id TEXT NOT NULL CHECK (actor_id ~ '^[1-9][0-9]{0,19}$'),
    resolve_tick BIGINT NOT NULL CHECK (resolve_tick >= 1),
    receipt_bytes BYTEA NOT NULL CHECK (octet_length(receipt_bytes) BETWEEN 1 AND 8192),
    PRIMARY KEY (campaign_id,receipt_id),
    FOREIGN KEY (campaign_id,resolve_tick) REFERENCES babylon_state.tick_commit(campaign_id,resolve_tick) DEFERRABLE INITIALLY DEFERRED
);
REVOKE ALL ON babylon_state.organizer_command_v1, babylon_state.organizer_subject_v1,
    babylon_state.organizer_observation_v1, babylon_state.organizer_receipt_v1 FROM PUBLIC;

REVOKE ALL ON FUNCTION babylon_state.lock_tick_event_marker_v2() FROM PUBLIC;
REVOKE ALL ON FUNCTION babylon_state.guard_tick_event_v2_history() FROM PUBLIC;

-- Replace graph_node_v1 and graph_node_f64_v1 tables and their PK ALTERs.
CREATE TABLE babylon_state.graph_string_lookup_v1 (
 campaign_id uuid NOT NULL REFERENCES babylon_state.campaign_foundation(campaign_id),
 string_id bigint NOT NULL CHECK(string_id>=0), first_tick bigint NOT NULL CHECK(first_tick>=0),
 marker_tick bigint GENERATED ALWAYS AS (NULLIF(first_tick,0)) STORED,
 value text NOT NULL COLLATE pg_catalog."C",
 PRIMARY KEY(campaign_id,string_id),
 FOREIGN KEY(campaign_id,marker_tick) REFERENCES babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED
);
-- MD5 is only an index accelerator. Full UTF-8 text equality in the
-- serialized insertion guard preserves exact identity even for collisions.
CREATE INDEX graph_string_lookup_value_bucket_v1 ON babylon_state.graph_string_lookup_v1
 (campaign_id, pg_catalog.md5(value));
CREATE FUNCTION babylon_state.graph_lookup_marker_lock_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
BEGIN
 PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||NEW.campaign_id::text,0));
 RETURN NEW;
END $$;
-- BEFORE triggers run in name order: obtain the campaign lock before the
-- existing event-marker lock, matching graph lookup/chunk insertion order.
CREATE TRIGGER "00_graph_lookup_marker_lock_v1" BEFORE INSERT ON babylon_state.tick_commit FOR EACH ROW EXECUTE FUNCTION babylon_state.graph_lookup_marker_lock_v1();
CREATE TABLE babylon_state.graph_node_lookup_v1 (
 campaign_id uuid NOT NULL, node_id bigint NOT NULL CHECK(node_id>=0),
 first_tick bigint NOT NULL CHECK(first_tick>=0),
 marker_tick bigint GENERATED ALWAYS AS (NULLIF(first_tick,0)) STORED,
 name_id bigint NOT NULL, type_id bigint NOT NULL,
 PRIMARY KEY(campaign_id,node_id), UNIQUE(campaign_id,name_id,type_id),
 FOREIGN KEY(campaign_id,name_id) REFERENCES babylon_state.graph_string_lookup_v1,
 FOREIGN KEY(campaign_id,type_id) REFERENCES babylon_state.graph_string_lookup_v1,
 FOREIGN KEY(campaign_id,marker_tick) REFERENCES babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED
);
-- Exact public admission bounds: babylon_graph::stable_state::{MAX_STABLE_GRAPH_NODES,MAX_STABLE_GRAPH_ATTRIBUTES}.
-- Both source validation and loaded-row canonical validation enforce these values.
CREATE TABLE babylon_state.graph_node_manifest_v1 (
 campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>=1),
 node_count bigint NOT NULL CHECK(node_count BETWEEN 0 AND 262144),
 f64_count bigint NOT NULL CHECK(f64_count BETWEEN 0 AND 524288),
 node_chunks bigint NOT NULL CHECK(node_chunks>=0), f64_chunks bigint NOT NULL CHECK(f64_chunks>=0),
 PRIMARY KEY(campaign_id,resolve_tick),
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.graph_node_chunk_v1 (
 campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL, ordinal bigint NOT NULL CHECK(ordinal>=0),
 node_ids bigint[] NOT NULL,
 PRIMARY KEY(campaign_id,resolve_tick,ordinal),
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.graph_node_manifest_v1 DEFERRABLE INITIALLY DEFERRED,
 CHECK(array_ndims(node_ids)=1 AND array_lower(node_ids,1)=1 AND cardinality(node_ids) BETWEEN 1 AND 4096 AND array_position(node_ids,NULL) IS NULL)
);
CREATE TABLE babylon_state.graph_node_f64_chunk_v1 (
 campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL, qname_id bigint NOT NULL,
 ordinal bigint NOT NULL CHECK(ordinal>=0), node_ids bigint[] NOT NULL, value_bits bigint[] NOT NULL,
 PRIMARY KEY(campaign_id,resolve_tick,qname_id,ordinal),
 FOREIGN KEY(campaign_id,qname_id) REFERENCES babylon_state.graph_string_lookup_v1,
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.graph_node_manifest_v1 DEFERRABLE INITIALLY DEFERRED,
 CHECK(array_ndims(node_ids)=1 AND array_lower(node_ids,1)=1 AND cardinality(node_ids) BETWEEN 1 AND 4096 AND array_position(node_ids,NULL) IS NULL),
 CHECK(array_ndims(value_bits)=1 AND array_lower(value_bits,1)=1 AND cardinality(value_bits)=cardinality(node_ids) AND array_position(value_bits,NULL) IS NULL)
);
CREATE VIEW babylon_state.graph_node_v1 AS
 SELECT c.campaign_id,c.resolve_tick,s.value AS local_name,t.value AS node_type
 FROM babylon_state.graph_node_chunk_v1 c
 JOIN babylon_state.tick_commit m USING(campaign_id,resolve_tick)
 CROSS JOIN LATERAL unnest(c.node_ids) u(node_id)
 JOIN babylon_state.graph_node_lookup_v1 n ON n.campaign_id=c.campaign_id AND n.node_id=u.node_id
 JOIN babylon_state.graph_string_lookup_v1 s ON s.campaign_id=n.campaign_id AND s.string_id=n.name_id
 JOIN babylon_state.graph_string_lookup_v1 t ON t.campaign_id=n.campaign_id AND t.string_id=n.type_id;
CREATE VIEW babylon_state.graph_node_f64_v1 AS
 SELECT c.campaign_id,c.resolve_tick,s.value AS local_name,q.value AS qname,u.value_bits
 FROM babylon_state.graph_node_f64_chunk_v1 c
 JOIN babylon_state.tick_commit m USING(campaign_id,resolve_tick)
 CROSS JOIN LATERAL unnest(c.node_ids,c.value_bits) u(node_id,value_bits)
 JOIN babylon_state.graph_node_lookup_v1 n ON n.campaign_id=c.campaign_id AND n.node_id=u.node_id
 JOIN babylon_state.graph_string_lookup_v1 s ON s.campaign_id=n.campaign_id AND s.string_id=n.name_id
 JOIN babylon_state.graph_string_lookup_v1 q ON q.campaign_id=c.campaign_id AND q.string_id=c.qname_id;
REVOKE ALL ON babylon_state.graph_string_lookup_v1,babylon_state.graph_node_lookup_v1,babylon_state.graph_node_manifest_v1,babylon_state.graph_node_chunk_v1,babylon_state.graph_node_f64_chunk_v1,babylon_state.graph_node_v1,babylon_state.graph_node_f64_v1 FROM PUBLIC;
CREATE FUNCTION babylon_state.graph_lookup_immutable_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
BEGIN
 RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_lookup_append_only';
END $$;
CREATE TRIGGER graph_string_lookup_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.graph_string_lookup_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_immutable_v1();
CREATE TRIGGER graph_node_lookup_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.graph_node_lookup_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_immutable_v1();
-- Share the marker's existing advisory lock namespace; serialize late inserts
-- against marker admission, without scanning the entire tick once per row.
CREATE FUNCTION babylon_state.graph_chunk_insert_guard_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE a RECORD;
BEGIN
 FOR a IN SELECT DISTINCT campaign_id FROM graph_new_rows ORDER BY campaign_id LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||a.campaign_id::text,0));
 END LOOP;
 FOR a IN SELECT DISTINCT campaign_id,resolve_tick FROM graph_new_rows ORDER BY campaign_id,resolve_tick LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||a.campaign_id::text||':'||a.resolve_tick::text,0));
  IF EXISTS(SELECT 1 FROM babylon_state.tick_commit WHERE campaign_id=a.campaign_id AND resolve_tick=a.resolve_tick) THEN
   RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_refused_marked_history_mutation';
  END IF;
 END LOOP;
 RETURN NULL;
END $$;
CREATE TRIGGER graph_node_chunk_insert_guard_v1 AFTER INSERT ON babylon_state.graph_node_chunk_v1 REFERENCING NEW TABLE AS graph_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_chunk_insert_guard_v1();
CREATE TRIGGER graph_node_f64_chunk_insert_guard_v1 AFTER INSERT ON babylon_state.graph_node_f64_chunk_v1 REFERENCING NEW TABLE AS graph_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_chunk_insert_guard_v1();
CREATE TRIGGER graph_node_manifest_insert_guard_v1 AFTER INSERT ON babylon_state.graph_node_manifest_v1 REFERENCING NEW TABLE AS graph_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_chunk_insert_guard_v1();
CREATE TRIGGER graph_node_chunk_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.graph_node_chunk_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_immutable_v1();
CREATE TRIGGER graph_node_f64_chunk_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.graph_node_f64_chunk_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_immutable_v1();
CREATE TRIGGER graph_node_manifest_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.graph_node_manifest_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_immutable_v1();
CREATE FUNCTION babylon_state.graph_node_marker_complete_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE m babylon_state.graph_node_manifest_v1%ROWTYPE; bad boolean;
BEGIN
 SELECT * INTO m FROM babylon_state.graph_node_manifest_v1 WHERE campaign_id=NEW.campaign_id AND resolve_tick=NEW.resolve_tick;
 IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_manifest_missing'; END IF;
 SELECT count(*)<>m.node_chunks OR coalesce(sum(cardinality(node_ids)),0)<>m.node_count
  OR (count(*)>0 AND (min(ordinal)<>0 OR max(ordinal)<>count(*)-1)) INTO bad
 FROM babylon_state.graph_node_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_chunk_gap_or_count'; END IF;
 SELECT count(*)<>m.f64_chunks OR coalesce(sum(cardinality(node_ids)),0)<>m.f64_count INTO bad
 FROM babylon_state.graph_node_f64_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick;
 IF bad OR EXISTS(SELECT 1 FROM babylon_state.graph_node_f64_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick GROUP BY qname_id HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1) THEN
  RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_chunk_gap_or_count';
 END IF;
 -- Validate array refs and one current type per local name in one set operation.
 WITH members AS (SELECT u.node_id FROM babylon_state.graph_node_chunk_v1 c CROSS JOIN LATERAL unnest(c.node_ids) u(node_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick),
 joined AS (SELECT a.node_id,n.name_id,n.first_tick,s.first_tick AS name_tick,t.first_tick AS type_tick FROM members a LEFT JOIN babylon_state.graph_node_lookup_v1 n ON n.campaign_id=m.campaign_id AND n.node_id=a.node_id LEFT JOIN babylon_state.graph_string_lookup_v1 s ON s.campaign_id=m.campaign_id AND s.string_id=n.name_id LEFT JOIN babylon_state.graph_string_lookup_v1 t ON t.campaign_id=m.campaign_id AND t.string_id=n.type_id)
 SELECT count(*)<>count(name_id) OR count(*)<>count(DISTINCT name_id) OR coalesce(bool_or(first_tick>m.resolve_tick OR name_tick>m.resolve_tick OR type_tick>m.resolve_tick),false) INTO bad FROM joined;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_reference_or_duplicate'; END IF;
 WITH members AS (SELECT u.node_id FROM babylon_state.graph_node_chunk_v1 c CROSS JOIN LATERAL unnest(c.node_ids) u(node_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick),
 attrs AS (SELECT c.qname_id,u.node_id FROM babylon_state.graph_node_f64_chunk_v1 c CROSS JOIN LATERAL unnest(c.node_ids) u(node_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick),
 joined AS (SELECT a.node_id,a.qname_id,b.node_id AS member_id,q.first_tick FROM attrs a LEFT JOIN members b USING(node_id) LEFT JOIN babylon_state.graph_string_lookup_v1 q ON q.campaign_id=m.campaign_id AND q.string_id=a.qname_id)
 SELECT count(*)<>count(member_id) OR count(*)<>count(DISTINCT (node_id,qname_id)) OR coalesce(bool_or(first_tick>m.resolve_tick),false) INTO bad FROM joined;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_reference_or_duplicate'; END IF;
 -- Dense append-only IDs make count-based assignment explicit and checked.
 IF EXISTS(SELECT 1 FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(string_id)<>0 OR max(string_id)<>count(*)-1)
 OR EXISTS(SELECT 1 FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(node_id)<>0 OR max(node_id)<>count(*)-1) THEN
  RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_lookup_gap';
 END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER graph_node_marker_complete_v1 AFTER INSERT ON babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.graph_node_marker_complete_v1();
CREATE FUNCTION babylon_state.graph_lookup_insert_guard_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE a RECORD;
BEGIN
 FOR a IN SELECT DISTINCT campaign_id FROM graph_new_rows ORDER BY campaign_id LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||a.campaign_id::text,0));
 END LOOP;
 IF TG_TABLE_NAME='graph_string_lookup_v1' THEN
  IF EXISTS(SELECT 1 FROM graph_new_rows n JOIN babylon_state.graph_string_lookup_v1 t
    ON t.campaign_id=n.campaign_id
    AND pg_catalog.md5(t.value)=pg_catalog.md5(n.value)
    AND t.value=n.value AND t.string_id<>n.string_id) THEN
   RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_lookup_duplicate_string';
  END IF;
 END IF;
 -- Foundation additions share the first marker lock too. Checking without
 -- this lock permits a concurrent first marker to publish before this insert.
 FOR a IN SELECT DISTINCT campaign_id FROM graph_new_rows WHERE first_tick=0 ORDER BY campaign_id LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||a.campaign_id::text||':1',0));
  IF EXISTS(SELECT 1 FROM babylon_state.tick_commit WHERE campaign_id=a.campaign_id) THEN
   RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_lookup_refused_late_foundation';
  END IF;
 END LOOP;
 FOR a IN SELECT DISTINCT campaign_id,first_tick FROM graph_new_rows WHERE first_tick>0 ORDER BY campaign_id,first_tick LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||a.campaign_id::text||':'||a.first_tick::text,0));
  IF EXISTS(SELECT 1 FROM babylon_state.tick_commit WHERE campaign_id=a.campaign_id AND resolve_tick=a.first_tick) THEN
   RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_lookup_refused_marked_history_mutation';
  END IF;
 END LOOP;
 RETURN NULL;
END $$;
CREATE TRIGGER graph_string_lookup_insert_guard_v1 AFTER INSERT ON babylon_state.graph_string_lookup_v1 REFERENCING NEW TABLE AS graph_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_insert_guard_v1();
CREATE TRIGGER graph_node_lookup_insert_guard_v1 AFTER INSERT ON babylon_state.graph_node_lookup_v1 REFERENCING NEW TABLE AS graph_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_insert_guard_v1();

REVOKE ALL ON FUNCTION babylon_state.graph_lookup_marker_lock_v1(),babylon_state.graph_lookup_immutable_v1(),babylon_state.graph_chunk_insert_guard_v1(),babylon_state.graph_node_marker_complete_v1(),babylon_state.graph_lookup_insert_guard_v1() FROM PUBLIC;

-- Designed bounded physical chunks; logical ordinal/position bounds retain u32.
CREATE FUNCTION babylon_state.event_array_valid_v1(a anyarray,n integer,nullable boolean) RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path TO 'pg_catalog' AS $$
 SELECT coalesce(array_ndims(a)=1 AND array_lower(a,1)=1 AND cardinality(a)=n AND (nullable OR array_position(a,NULL) IS NULL),false)
$$;
CREATE TABLE babylon_state.event_text_lookup_v1 (
 campaign_id uuid NOT NULL REFERENCES babylon_state.campaign_foundation(campaign_id),
 text_id bigint NOT NULL CHECK(text_id>=0),first_tick bigint NOT NULL CHECK(first_tick>=0),
 marker_tick bigint GENERATED ALWAYS AS(NULLIF(first_tick,0)) STORED,
 value text COLLATE pg_catalog."C" NOT NULL,
 PRIMARY KEY(campaign_id,text_id),
 FOREIGN KEY(campaign_id,marker_tick) REFERENCES babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED
);
-- Nonunique hash access does not impose B-tree tuple-size limits. Identity and
-- duplicate admission compare complete exact values, including hash collisions.
CREATE INDEX event_text_exact_access_v1 ON babylon_state.event_text_lookup_v1 USING hash(value);
CREATE TABLE babylon_state.event_key_lookup_v1 (
 campaign_id uuid NOT NULL REFERENCES babylon_state.campaign_foundation(campaign_id),
 key_id bigint NOT NULL CHECK(key_id>=0),first_tick bigint NOT NULL CHECK(first_tick>=0),
 marker_tick bigint GENERATED ALWAYS AS(NULLIF(first_tick,0)) STORED,
 value bytea NOT NULL,
 PRIMARY KEY(campaign_id,key_id),
 FOREIGN KEY(campaign_id,marker_tick) REFERENCES babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED
);
-- Nonunique hash access does not impose B-tree tuple-size limits. Identity and
-- duplicate admission compare complete exact values, including hash collisions.
CREATE INDEX event_key_exact_access_v1 ON babylon_state.event_key_lookup_v1 USING hash(value);
CREATE TABLE babylon_state.event_manifest_v1 (
 campaign_id uuid NOT NULL,resolve_tick bigint NOT NULL CHECK(resolve_tick>=1),
 event_count bigint NOT NULL CHECK(event_count BETWEEN 0 AND 4294967296),field_count bigint NOT NULL CHECK(field_count>=0),
 parent_chunks bigint NOT NULL CHECK(parent_chunks>=0),field_chunks bigint NOT NULL CHECK(field_chunks>=0),
 PRIMARY KEY(campaign_id,resolve_tick),
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.event_parent_chunk_v1 (
 campaign_id uuid NOT NULL,resolve_tick bigint NOT NULL,chunk bigint NOT NULL CHECK(chunk>=0),
 event_ordinals bigint[] NOT NULL,type_ids bigint[] NOT NULL,rule_ids bigint[] NOT NULL,choice_ordinals bigint[] NOT NULL,
 PRIMARY KEY(campaign_id,resolve_tick,chunk),
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.event_manifest_v1 DEFERRABLE INITIALLY DEFERRED,
 CHECK(cardinality(event_ordinals) BETWEEN 1 AND 4096),
 CHECK(babylon_state.event_array_valid_v1(event_ordinals,cardinality(event_ordinals),false)),
 CHECK(babylon_state.event_array_valid_v1(type_ids,cardinality(event_ordinals),false)),
 CHECK(babylon_state.event_array_valid_v1(rule_ids,cardinality(event_ordinals),false)),
 CHECK(babylon_state.event_array_valid_v1(choice_ordinals,cardinality(event_ordinals),true))
);
CREATE TABLE babylon_state.event_field_chunk_v1 (
 campaign_id uuid NOT NULL,resolve_tick bigint NOT NULL,chunk bigint NOT NULL CHECK(chunk>=0),value_tag smallint NOT NULL CHECK(value_tag BETWEEN 1 AND 9),
 event_ordinals bigint[] NOT NULL,positions bigint[] NOT NULL,name_ids bigint[] NOT NULL,
 int_values bigint[],currency_values numeric(39,0)[],real_bits bigint[],ratio_bits bigint[],ratio_mins bigint[],ratio_maxs bigint[],bool_values boolean[],enum_types bigint[],enum_members bigint[],key_ids bigint[],key_scenario_ids bigint[],
 PRIMARY KEY(campaign_id,resolve_tick,chunk),
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.event_manifest_v1 DEFERRABLE INITIALLY DEFERRED,
 CHECK(cardinality(event_ordinals) BETWEEN 1 AND 4096),
 CHECK(babylon_state.event_array_valid_v1(event_ordinals,cardinality(event_ordinals),false)),
 CHECK(babylon_state.event_array_valid_v1(positions,cardinality(event_ordinals),false)),
 CHECK(babylon_state.event_array_valid_v1(name_ids,cardinality(event_ordinals),false)),
 CHECK(CASE WHEN value_tag=1 THEN int_values IS NOT NULL AND babylon_state.event_array_valid_v1(int_values,cardinality(event_ordinals),false) ELSE int_values IS NULL END),
 CHECK(CASE WHEN value_tag=2 THEN currency_values IS NOT NULL AND babylon_state.event_array_valid_v1(currency_values,cardinality(event_ordinals),false) ELSE currency_values IS NULL END),
 CHECK(CASE WHEN value_tag=3 THEN real_bits IS NOT NULL AND babylon_state.event_array_valid_v1(real_bits,cardinality(event_ordinals),false) ELSE real_bits IS NULL END),
 CHECK(CASE WHEN value_tag=4 THEN ratio_bits IS NOT NULL AND babylon_state.event_array_valid_v1(ratio_bits,cardinality(event_ordinals),false) ELSE ratio_bits IS NULL END),
 CHECK(CASE WHEN value_tag=4 THEN ratio_mins IS NOT NULL AND babylon_state.event_array_valid_v1(ratio_mins,cardinality(event_ordinals),true) ELSE ratio_mins IS NULL END),
 CHECK(CASE WHEN value_tag=4 THEN ratio_maxs IS NOT NULL AND babylon_state.event_array_valid_v1(ratio_maxs,cardinality(event_ordinals),true) ELSE ratio_maxs IS NULL END),
 CHECK(CASE WHEN value_tag=5 THEN bool_values IS NOT NULL AND babylon_state.event_array_valid_v1(bool_values,cardinality(event_ordinals),false) ELSE bool_values IS NULL END),
 CHECK(CASE WHEN value_tag=6 THEN enum_types IS NOT NULL AND babylon_state.event_array_valid_v1(enum_types,cardinality(event_ordinals),false) ELSE enum_types IS NULL END),
 CHECK(CASE WHEN value_tag=6 THEN enum_members IS NOT NULL AND babylon_state.event_array_valid_v1(enum_members,cardinality(event_ordinals),false) ELSE enum_members IS NULL END),
 CHECK(CASE WHEN value_tag>=7 THEN key_ids IS NOT NULL AND babylon_state.event_array_valid_v1(key_ids,cardinality(event_ordinals),false) ELSE key_ids IS NULL END),
 CHECK(CASE WHEN value_tag=7 THEN key_scenario_ids IS NOT NULL AND babylon_state.event_array_valid_v1(key_scenario_ids,cardinality(event_ordinals),false) ELSE key_scenario_ids IS NULL END)
);
-- Raw expanded views are the guard's complete source, without marker filtering.
-- Public/runtime logical views below remain marker-bound; raw sources ungranted.
CREATE VIEW babylon_state.event_parent_expanded_v1 AS
 SELECT c.campaign_id,c.resolve_tick,u.ordinal,t.value AS event_type,r.value AS emitting_rule,u.choice_receipt_ordinal
 FROM babylon_state.event_parent_chunk_v1 c
 CROSS JOIN LATERAL unnest(c.event_ordinals,c.type_ids,c.rule_ids,c.choice_ordinals) u(ordinal,type_id,rule_id,choice_receipt_ordinal)
 LEFT JOIN babylon_state.event_text_lookup_v1 t ON t.campaign_id=c.campaign_id AND t.text_id=u.type_id
 LEFT JOIN babylon_state.event_text_lookup_v1 r ON r.campaign_id=c.campaign_id AND r.text_id=u.rule_id;
CREATE VIEW babylon_state.event_field_expanded_v1 AS
 SELECT c.campaign_id,c.resolve_tick,u.ordinal,u.position,n.value AS field_name,c.value_tag,
 u.int_value,u.currency_value::numeric(39,0) AS currency_value,u.real_bits,u.ratio_bits,u.ratio_min_bits,u.ratio_max_bits,u.bool_value,e.value AS enum_type,m.value AS enum_member,CASE WHEN c.value_tag=7 AND ns.string_id IS NOT NULL AND nn.string_id IS NOT NULL THEN
 pg_catalog.decode('626162796c6f6e2e737461626c652d656c656d656e74000000000101','hex') || pg_catalog.int4send(pg_catalog.octet_length(pg_catalog.convert_to(ns.value,'UTF8'))) || pg_catalog.convert_to(ns.value,'UTF8') || pg_catalog.int4send(pg_catalog.octet_length(pg_catalog.convert_to(nn.value,'UTF8'))) || pg_catalog.convert_to(nn.value,'UTF8')
 ELSE k.value END AS stable_key
 FROM babylon_state.event_field_chunk_v1 c
 CROSS JOIN LATERAL unnest(c.event_ordinals,c.positions,c.name_ids,c.int_values,c.currency_values,c.real_bits,c.ratio_bits,c.ratio_mins,c.ratio_maxs,c.bool_values,c.enum_types,c.enum_members,c.key_ids,c.key_scenario_ids)
 u(ordinal,position,name_id,int_value,currency_value,real_bits,ratio_bits,ratio_min_bits,ratio_max_bits,bool_value,enum_type_id,enum_member_id,key_id,key_scenario_id)
 LEFT JOIN babylon_state.event_text_lookup_v1 n ON n.campaign_id=c.campaign_id AND n.text_id=u.name_id
 LEFT JOIN babylon_state.event_text_lookup_v1 e ON e.campaign_id=c.campaign_id AND e.text_id=u.enum_type_id
 LEFT JOIN babylon_state.event_text_lookup_v1 m ON m.campaign_id=c.campaign_id AND m.text_id=u.enum_member_id
 LEFT JOIN babylon_state.event_key_lookup_v1 k ON c.value_tag IN(8,9) AND k.campaign_id=c.campaign_id AND k.key_id=u.key_id
 LEFT JOIN babylon_state.graph_string_lookup_v1 ns ON c.value_tag=7 AND ns.campaign_id=c.campaign_id AND ns.string_id=u.key_scenario_id
 LEFT JOIN babylon_state.graph_string_lookup_v1 nn ON c.value_tag=7 AND nn.campaign_id=c.campaign_id AND nn.string_id=u.key_id;
CREATE VIEW babylon_state.tick_event_v2 AS SELECT c.* FROM babylon_state.event_parent_expanded_v1 c JOIN babylon_state.tick_commit marker USING(campaign_id,resolve_tick);
CREATE VIEW babylon_state.tick_event_field_v2 AS SELECT c.* FROM babylon_state.event_field_expanded_v1 c JOIN babylon_state.tick_commit marker USING(campaign_id,resolve_tick);
CREATE FUNCTION babylon_state.event_storage_immutable_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
BEGIN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_append_only'; END $$;
CREATE FUNCTION babylon_state.event_lookup_insert_guard_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE a RECORD;
BEGIN
 FOR a IN SELECT DISTINCT campaign_id FROM new_event_rows ORDER BY campaign_id LOOP
 PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||a.campaign_id::text,0));
 END LOOP;
 IF EXISTS(SELECT 1 FROM new_event_rows n JOIN babylon_state.tick_commit m USING(campaign_id) WHERE n.first_tick=0) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_lookup_refused_late_foundation'; END IF;
 FOR a IN SELECT DISTINCT campaign_id,first_tick FROM new_event_rows WHERE first_tick>0 ORDER BY campaign_id,first_tick LOOP
 PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||a.campaign_id::text||':'||a.first_tick::text,0));
 IF EXISTS(SELECT 1 FROM babylon_state.tick_commit WHERE campaign_id=a.campaign_id AND resolve_tick=a.first_tick) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_lookup_refused_marked_history_mutation'; END IF;
 END LOOP; RETURN NULL;
END $$;
CREATE TRIGGER event_text_lookup_v1_immutable BEFORE UPDATE OR DELETE ON babylon_state.event_text_lookup_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.event_storage_immutable_v1();
CREATE TRIGGER event_text_lookup_v1_insert_guard AFTER INSERT ON babylon_state.event_text_lookup_v1 REFERENCING NEW TABLE AS new_event_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.event_lookup_insert_guard_v1();
CREATE TRIGGER event_key_lookup_v1_immutable BEFORE UPDATE OR DELETE ON babylon_state.event_key_lookup_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.event_storage_immutable_v1();
CREATE TRIGGER event_key_lookup_v1_insert_guard AFTER INSERT ON babylon_state.event_key_lookup_v1 REFERENCING NEW TABLE AS new_event_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.event_lookup_insert_guard_v1();
CREATE TRIGGER event_manifest_v1_immutable BEFORE UPDATE OR DELETE ON babylon_state.event_manifest_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.event_storage_immutable_v1();
CREATE TRIGGER event_manifest_v1_insert_guard AFTER INSERT ON babylon_state.event_manifest_v1 REFERENCING NEW TABLE AS new_event_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.guard_tick_event_v2_history();
CREATE TRIGGER event_parent_chunk_v1_immutable BEFORE UPDATE OR DELETE ON babylon_state.event_parent_chunk_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.event_storage_immutable_v1();
CREATE TRIGGER event_parent_chunk_v1_insert_guard AFTER INSERT ON babylon_state.event_parent_chunk_v1 REFERENCING NEW TABLE AS new_event_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.guard_tick_event_v2_history();
CREATE TRIGGER event_field_chunk_v1_immutable BEFORE UPDATE OR DELETE ON babylon_state.event_field_chunk_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.event_storage_immutable_v1();
CREATE TRIGGER event_field_chunk_v1_insert_guard AFTER INSERT ON babylon_state.event_field_chunk_v1 REFERENCING NEW TABLE AS new_event_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.guard_tick_event_v2_history();
CREATE FUNCTION babylon_state.event_storage_marker_complete_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE m babylon_state.event_manifest_v1%ROWTYPE;bad boolean;
BEGIN
 SELECT * INTO m FROM babylon_state.event_manifest_v1 WHERE campaign_id=NEW.campaign_id AND resolve_tick=NEW.resolve_tick;
 IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_manifest_missing'; END IF;
 SELECT count(*)<>m.parent_chunks OR coalesce(sum(cardinality(event_ordinals)),0)<>m.event_count OR (count(*)>0 AND (min(chunk)<>0 OR max(chunk)<>count(*)-1)) INTO bad FROM babylon_state.event_parent_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_parent_chunk_count_or_gap'; END IF;
 SELECT count(*)<>m.field_chunks OR coalesce(sum(cardinality(event_ordinals)),0)<>m.field_count OR (count(*)>0 AND (min(chunk)<>0 OR max(chunk)<>count(*)-1)) INTO bad FROM babylon_state.event_field_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_field_chunk_count_or_gap'; END IF;
 -- Expand once, then perform set joins; never scan all parents for each field.
 WITH parents AS MATERIALIZED (SELECT * FROM babylon_state.event_parent_expanded_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick),
 fields AS MATERIALIZED (SELECT * FROM babylon_state.event_field_expanded_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick)
 SELECT EXISTS(SELECT 1 FROM parents GROUP BY ordinal HAVING count(*)<>1)
 OR EXISTS(SELECT 1 FROM parents HAVING count(*)>0 AND (min(ordinal)<>0 OR max(ordinal)<>count(*)-1))
 OR EXISTS(SELECT 1 FROM parents e LEFT JOIN babylon_state.tick_choice_receipt_v1 r ON r.campaign_id=e.campaign_id AND r.resolve_tick=e.resolve_tick AND r.encounter_ordinal=e.choice_receipt_ordinal WHERE e.ordinal NOT BETWEEN 0 AND 4294967295 OR e.event_type IS NULL OR e.emitting_rule IS NULL OR (e.choice_receipt_ordinal IS NOT NULL AND (e.choice_receipt_ordinal NOT BETWEEN 0 AND 4294967295 OR r.encounter_ordinal IS NULL)))
 OR EXISTS(SELECT 1 FROM fields GROUP BY ordinal,position HAVING count(*)<>1)
 OR EXISTS(SELECT 1 FROM fields GROUP BY ordinal HAVING min(position)<>0 OR max(position)<>count(*)-1)
 OR EXISTS(SELECT 1 FROM fields f LEFT JOIN parents e USING(ordinal) WHERE f.position NOT BETWEEN 0 AND 4294967295 OR f.field_name IS NULL OR (f.value_tag=6 AND (f.enum_type IS NULL OR f.enum_member IS NULL)) OR (f.value_tag>=7 AND f.stable_key IS NULL) OR e.ordinal IS NULL)
 OR EXISTS(SELECT 1 FROM fields GROUP BY ordinal,field_name HAVING count(*)<>1)
 OR EXISTS(SELECT 1 FROM (SELECT field_name,lead(field_name) OVER(PARTITION BY ordinal ORDER BY position) AS next_name FROM fields) ordered WHERE field_name>=next_name)
 INTO bad;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_parent_field_choice_or_order'; END IF;
 -- Check every scalar lookup dependency, not merely successful inner joins.
 IF EXISTS(SELECT 1 FROM babylon_state.event_parent_chunk_v1 c CROSS JOIN LATERAL unnest(c.type_ids||c.rule_ids) u(id) LEFT JOIN babylon_state.event_text_lookup_v1 t ON t.campaign_id=c.campaign_id AND t.text_id=u.id WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick AND (t.text_id IS NULL OR t.first_tick>m.resolve_tick))
 OR EXISTS(SELECT 1 FROM babylon_state.event_field_chunk_v1 c CROSS JOIN LATERAL unnest(c.name_ids||coalesce(c.enum_types,'{}'::bigint[])||coalesce(c.enum_members,'{}'::bigint[])) u(id) LEFT JOIN babylon_state.event_text_lookup_v1 t ON t.campaign_id=c.campaign_id AND t.text_id=u.id WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick AND (t.text_id IS NULL OR t.first_tick>m.resolve_tick))
 OR EXISTS(SELECT 1 FROM babylon_state.event_field_chunk_v1 c CROSS JOIN LATERAL unnest(c.key_ids) u(id) LEFT JOIN babylon_state.event_key_lookup_v1 k ON k.campaign_id=c.campaign_id AND k.key_id=u.id WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick AND c.value_tag IN(8,9) AND (k.key_id IS NULL OR k.first_tick>m.resolve_tick))
 OR EXISTS(SELECT 1 FROM babylon_state.event_field_chunk_v1 c CROSS JOIN LATERAL unnest(c.key_ids,c.key_scenario_ids) u(name_id,scenario_id) LEFT JOIN babylon_state.graph_string_lookup_v1 n ON n.campaign_id=c.campaign_id AND n.string_id=u.name_id LEFT JOIN babylon_state.graph_string_lookup_v1 s ON s.campaign_id=c.campaign_id AND s.string_id=u.scenario_id WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick AND c.value_tag=7 AND (n.string_id IS NULL OR s.string_id IS NULL OR n.first_tick>m.resolve_tick OR s.first_tick>m.resolve_tick OR (n.first_tick>0 AND n.first_tick<>m.resolve_tick AND NOT EXISTS(SELECT 1 FROM babylon_state.tick_commit p WHERE p.campaign_id=n.campaign_id AND p.resolve_tick=n.first_tick)) OR (s.first_tick>0 AND s.first_tick<>m.resolve_tick AND NOT EXISTS(SELECT 1 FROM babylon_state.tick_commit p WHERE p.campaign_id=s.campaign_id AND p.resolve_tick=s.first_tick)))) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_lookup_reference'; END IF;
 IF EXISTS(SELECT 1 FROM babylon_state.event_field_chunk_v1 c CROSS JOIN LATERAL unnest(c.key_ids) u(id) JOIN babylon_state.event_key_lookup_v1 k ON k.campaign_id=c.campaign_id AND k.key_id=u.id WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick AND c.value_tag IN(8,9) AND NOT CASE WHEN octet_length(k.value)>27 THEN substring(k.value FROM 1 FOR 27)=pg_catalog.decode('626162796c6f6e2e737461626c652d656c656d656e740000000001','hex') AND pg_catalog.get_byte(k.value,27)=CASE WHEN c.value_tag=8 THEN 3 ELSE 2 END ELSE false END) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_key_kind'; END IF;
 IF EXISTS(SELECT 1 FROM babylon_state.event_text_lookup_v1 WHERE campaign_id=m.campaign_id GROUP BY value HAVING count(*)<>1)
 OR EXISTS(SELECT 1 FROM babylon_state.event_text_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(text_id)<>0 OR max(text_id)<>count(*)-1) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_text_lookup_duplicate_or_gap'; END IF;
 IF EXISTS(SELECT 1 FROM babylon_state.event_key_lookup_v1 WHERE campaign_id=m.campaign_id GROUP BY value HAVING count(*)<>1)
 OR EXISTS(SELECT 1 FROM babylon_state.event_key_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(key_id)<>0 OR max(key_id)<>count(*)-1) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='event_storage_key_lookup_duplicate_or_gap'; END IF;
 RETURN NEW; END $$;
CREATE CONSTRAINT TRIGGER event_storage_marker_complete_v1 AFTER INSERT ON babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.event_storage_marker_complete_v1();
REVOKE ALL ON babylon_state.event_text_lookup_v1 FROM PUBLIC;
REVOKE ALL ON babylon_state.event_key_lookup_v1 FROM PUBLIC;
REVOKE ALL ON babylon_state.event_manifest_v1 FROM PUBLIC;
REVOKE ALL ON babylon_state.event_parent_chunk_v1 FROM PUBLIC;
REVOKE ALL ON babylon_state.event_field_chunk_v1 FROM PUBLIC;
REVOKE ALL ON babylon_state.event_parent_expanded_v1 FROM PUBLIC;
REVOKE ALL ON babylon_state.event_field_expanded_v1 FROM PUBLIC;
REVOKE ALL ON babylon_state.tick_event_v2 FROM PUBLIC;
REVOKE ALL ON babylon_state.tick_event_field_v2 FROM PUBLIC;
REVOKE ALL ON FUNCTION babylon_state.event_array_valid_v1(anyarray,integer,boolean),babylon_state.event_storage_immutable_v1(),babylon_state.event_lookup_insert_guard_v1(),babylon_state.event_storage_marker_complete_v1() FROM PUBLIC;

-- Territory definitions, typed fields and period memberships are append-only.
CREATE FUNCTION babylon_state.territory_immutable_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
BEGIN
 RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_append_only';
END $$;
CREATE TRIGGER territory_definition_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.territory_definition_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.territory_immutable_v1();
CREATE TRIGGER territory_definition_field_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.territory_definition_field_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.territory_immutable_v1();
CREATE TRIGGER territory_tick_manifest_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.territory_tick_manifest_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.territory_immutable_v1();
CREATE TRIGGER territory_tick_membership_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.territory_tick_membership_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.territory_immutable_v1();
CREATE FUNCTION babylon_state.territory_definition_insert_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
BEGIN
 PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||NEW.campaign_id::text,0));
 IF NEW.first_tick=0 THEN
  IF EXISTS(SELECT 1 FROM babylon_state.tick_commit WHERE campaign_id=NEW.campaign_id) THEN
   RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_late_opening_definition';
  END IF;
 ELSE
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||NEW.campaign_id::text||':'||NEW.first_tick::text,0));
  IF EXISTS(SELECT 1 FROM babylon_state.tick_commit WHERE campaign_id=NEW.campaign_id AND resolve_tick=NEW.first_tick) THEN
   RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_refused_marked_history_mutation';
  END IF;
 END IF;
 NEW.creation_xid := pg_catalog.pg_current_xact_id();
 RETURN NEW;
END $$;
CREATE TRIGGER territory_definition_insert_v1 BEFORE INSERT ON babylon_state.territory_definition_v1 FOR EACH ROW EXECUTE FUNCTION babylon_state.territory_definition_insert_v1();
CREATE FUNCTION babylon_state.territory_field_insert_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE a RECORD;
BEGIN
 FOR a IN SELECT DISTINCT n.campaign_id,d.creation_xid FROM territory_new_rows n
  JOIN babylon_state.territory_definition_v1 d USING(campaign_id,definition_id)
  ORDER BY n.campaign_id,d.creation_xid LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||a.campaign_id::text,0));
  IF a.creation_xid<>pg_catalog.pg_current_xact_id() THEN
   RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_definition_fields_sealed';
  END IF;
 END LOOP;
 -- A creating transaction can already have inserted a marker or forced its
 -- deferred completeness check. Reject both later mutation and overfilling.
 IF EXISTS(
  SELECT 1 FROM territory_new_rows n
  JOIN babylon_state.territory_definition_v1 d USING(campaign_id,definition_id)
  WHERE EXISTS(SELECT 1 FROM babylon_state.tick_commit t
    WHERE t.campaign_id=d.campaign_id AND t.resolve_tick=d.first_tick)
   OR EXISTS(SELECT 1 FROM babylon_state.territory_tick_membership_v1 m
    JOIN babylon_state.tick_commit t USING(campaign_id,resolve_tick)
    WHERE m.campaign_id=d.campaign_id AND m.definition_id=d.definition_id)
 ) THEN
  RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_refused_marked_history_mutation';
 END IF;
 IF EXISTS(
  SELECT 1 FROM (SELECT DISTINCT campaign_id,definition_id FROM territory_new_rows) n
  JOIN babylon_state.territory_definition_v1 d USING(campaign_id,definition_id)
  WHERE (SELECT count(*) FROM babylon_state.territory_definition_field_v1 f
    WHERE f.campaign_id=d.campaign_id AND f.definition_id=d.definition_id)>d.field_count
 ) THEN
  RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_definition_field_count_or_order';
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER territory_field_insert_v1 AFTER INSERT ON babylon_state.territory_definition_field_v1 REFERENCING NEW TABLE AS territory_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.territory_field_insert_v1();
CREATE FUNCTION babylon_state.territory_definition_complete_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE bad boolean;
BEGIN
 SELECT count(*)<>NEW.field_count OR
  (count(*)>0 AND (min(position)<>0 OR max(position)<>count(*)-1)) INTO bad
 FROM babylon_state.territory_definition_field_v1
 WHERE campaign_id=NEW.campaign_id AND definition_id=NEW.definition_id;
 IF bad OR EXISTS(
  SELECT 1 FROM (SELECT field_name,
    lag(field_name) OVER(ORDER BY position) AS previous_name
   FROM babylon_state.territory_definition_field_v1
   WHERE campaign_id=NEW.campaign_id AND definition_id=NEW.definition_id) f
  WHERE previous_name>=field_name
 ) THEN
  RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_definition_field_count_or_order';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER territory_definition_complete_v1 AFTER INSERT ON babylon_state.territory_definition_v1 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.territory_definition_complete_v1();
CREATE FUNCTION babylon_state.territory_tick_insert_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE a RECORD;
BEGIN
 FOR a IN SELECT DISTINCT campaign_id FROM territory_new_rows ORDER BY campaign_id LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||a.campaign_id::text,0));
 END LOOP;
 FOR a IN SELECT DISTINCT campaign_id,resolve_tick FROM territory_new_rows ORDER BY campaign_id,resolve_tick LOOP
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||a.campaign_id::text||':'||a.resolve_tick::text,0));
  IF EXISTS(SELECT 1 FROM babylon_state.tick_commit WHERE campaign_id=a.campaign_id AND resolve_tick=a.resolve_tick) THEN
   RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_refused_marked_history_mutation';
  END IF;
 END LOOP;
 RETURN NULL;
END $$;
CREATE TRIGGER territory_manifest_insert_v1 AFTER INSERT ON babylon_state.territory_tick_manifest_v1 REFERENCING NEW TABLE AS territory_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.territory_tick_insert_v1();
CREATE TRIGGER territory_membership_insert_v1 AFTER INSERT ON babylon_state.territory_tick_membership_v1 REFERENCING NEW TABLE AS territory_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.territory_tick_insert_v1();
CREATE FUNCTION babylon_state.territory_marker_complete_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
DECLARE expected bigint; bad boolean;
BEGIN
 SELECT territory_count INTO expected FROM babylon_state.territory_tick_manifest_v1
 WHERE campaign_id=NEW.campaign_id AND resolve_tick=NEW.resolve_tick;
 IF NOT FOUND THEN
  RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_manifest_missing';
 END IF;
 SELECT count(*)<>expected OR count(*)<>count(DISTINCT d.territory_id)
  OR coalesce(bool_or(d.first_tick>NEW.resolve_tick OR
   (d.first_tick>0 AND d.first_tick<NEW.resolve_tick AND t.resolve_tick IS NULL)),false)
 INTO bad FROM babylon_state.territory_tick_membership_v1 m
 JOIN babylon_state.territory_definition_v1 d USING(campaign_id,definition_id)
 LEFT JOIN babylon_state.tick_commit t ON t.campaign_id=d.campaign_id AND t.resolve_tick=d.first_tick
 WHERE m.campaign_id=NEW.campaign_id AND m.resolve_tick=NEW.resolve_tick;
 IF bad THEN
  RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_membership_count_identity_or_time';
 END IF;
 IF EXISTS(SELECT 1 FROM babylon_state.territory_definition_v1
  WHERE campaign_id=NEW.campaign_id
  HAVING min(definition_id)<>0 OR max(definition_id)<>count(*)-1) THEN
  RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='territory_definition_id_gap';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER territory_marker_complete_v1 BEFORE INSERT ON babylon_state.tick_commit FOR EACH ROW EXECUTE FUNCTION babylon_state.territory_marker_complete_v1();
REVOKE ALL ON FUNCTION babylon_state.territory_immutable_v1(),
 babylon_state.territory_definition_insert_v1(),babylon_state.territory_field_insert_v1(),
 babylon_state.territory_definition_complete_v1(),babylon_state.territory_tick_insert_v1(),
 babylon_state.territory_marker_complete_v1() FROM PUBLIC;
