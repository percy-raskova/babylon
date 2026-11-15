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
    receipt_storage_bytes bytea NOT NULL CHECK (octet_length(receipt_storage_bytes) <= 947588276),
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
CREATE TABLE babylon_state.organizer_encounter_v1 (
    campaign_id UUID NOT NULL REFERENCES babylon_state.campaign(campaign_id) ON DELETE CASCADE,
    receipt_id BYTEA NOT NULL CHECK (octet_length(receipt_id)=32),
    actor_id TEXT NOT NULL CHECK (actor_id ~ '^[1-9][0-9]{0,19}$'),
    subject_id TEXT NOT NULL CHECK (subject_id ~ '^[1-9][0-9]{0,19}$'),
    resolve_tick BIGINT NOT NULL CHECK (resolve_tick >= 1),
    encounter_bytes BYTEA NOT NULL CHECK (octet_length(encounter_bytes) BETWEEN 1 AND 1257),
    PRIMARY KEY (campaign_id,receipt_id),
    FOREIGN KEY (campaign_id,resolve_tick) REFERENCES babylon_state.tick_commit(campaign_id,resolve_tick) DEFERRABLE INITIALLY DEFERRED
);
REVOKE ALL ON babylon_state.organizer_command_v1, babylon_state.organizer_subject_v1,
    babylon_state.organizer_observation_v1, babylon_state.organizer_receipt_v1,
    babylon_state.organizer_encounter_v1 FROM PUBLIC;

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
CREATE TABLE babylon_state.graph_node_vector_v1 (
 campaign_id uuid NOT NULL, vector_id bigint NOT NULL CHECK(vector_id>=0),
 first_tick bigint NOT NULL CHECK(first_tick>=1), node_ids bigint[] NOT NULL,
 PRIMARY KEY(campaign_id,vector_id),
 FOREIGN KEY(campaign_id,first_tick) REFERENCES babylon_state.tick_commit DEFERRABLE INITIALLY DEFERRED,
 CHECK(array_ndims(node_ids)=1 AND array_lower(node_ids,1)=1 AND cardinality(node_ids) BETWEEN 1 AND 4096 AND array_position(node_ids,NULL) IS NULL)
);
-- Hash collisions are candidates only: the insertion guard compares full arrays.
CREATE INDEX graph_vector_exact_access_v1 ON babylon_state.graph_node_vector_v1 USING hash(node_ids);
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
 vector_id bigint NOT NULL,
 PRIMARY KEY(campaign_id,resolve_tick,ordinal),
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.graph_node_manifest_v1 DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(campaign_id,vector_id) REFERENCES babylon_state.graph_node_vector_v1 DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.graph_node_f64_chunk_v1 (
 campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL, qname_id bigint NOT NULL,
 ordinal bigint NOT NULL CHECK(ordinal>=0), vector_id bigint NOT NULL, value_bits bigint[] NOT NULL,
 PRIMARY KEY(campaign_id,resolve_tick,qname_id,ordinal),
 FOREIGN KEY(campaign_id,qname_id) REFERENCES babylon_state.graph_string_lookup_v1,
 FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.graph_node_manifest_v1 DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(campaign_id,vector_id) REFERENCES babylon_state.graph_node_vector_v1 DEFERRABLE INITIALLY DEFERRED,
 CHECK(array_ndims(value_bits)=1 AND array_lower(value_bits,1)=1 AND cardinality(value_bits) BETWEEN 1 AND 4096 AND array_position(value_bits,NULL) IS NULL)
);
-- Restrict vectors to this committed period before expanding their node IDs.
-- Materializing its campaign dictionaries once avoids an index probe per field.
CREATE VIEW babylon_state.graph_node_v1 AS
SELECT marker.campaign_id, marker.resolve_tick, projected.local_name, projected.node_type
FROM babylon_state.tick_commit marker
CROSS JOIN LATERAL (
    WITH names AS MATERIALIZED (
        SELECT string_id, value FROM babylon_state.graph_string_lookup_v1
        WHERE campaign_id = marker.campaign_id
    ), nodes AS MATERIALIZED (
        SELECT node_id, name_id, type_id FROM babylon_state.graph_node_lookup_v1
        WHERE campaign_id = marker.campaign_id
    ), chunks AS MATERIALIZED (
        SELECT vector.node_ids FROM babylon_state.graph_node_chunk_v1 chunk
        JOIN babylon_state.graph_node_vector_v1 vector USING (campaign_id, vector_id)
        WHERE chunk.campaign_id = marker.campaign_id AND chunk.resolve_tick = marker.resolve_tick
    ), members AS MATERIALIZED (
        SELECT member.node_id FROM chunks
        CROSS JOIN LATERAL unnest(chunks.node_ids) member(node_id)
    )
    SELECT name.value AS local_name, kind.value AS node_type
    FROM members JOIN nodes USING (node_id)
    JOIN names name ON name.string_id = nodes.name_id
    JOIN names kind ON kind.string_id = nodes.type_id
    OFFSET 0
) projected;
CREATE VIEW babylon_state.graph_node_f64_v1 AS
SELECT marker.campaign_id, marker.resolve_tick, projected.local_name, projected.qname, projected.value_bits
FROM babylon_state.tick_commit marker
CROSS JOIN LATERAL (
    WITH names AS MATERIALIZED (
        SELECT string_id, value FROM babylon_state.graph_string_lookup_v1
        WHERE campaign_id = marker.campaign_id
    ), nodes AS MATERIALIZED (
        SELECT node_id, name_id, type_id FROM babylon_state.graph_node_lookup_v1
        WHERE campaign_id = marker.campaign_id
    ), chunks AS MATERIALIZED (
        SELECT vector.node_ids, chunk.qname_id, chunk.value_bits
        FROM babylon_state.graph_node_f64_chunk_v1 chunk
        JOIN babylon_state.graph_node_vector_v1 vector USING (campaign_id, vector_id)
        WHERE chunk.campaign_id = marker.campaign_id AND chunk.resolve_tick = marker.resolve_tick
    ), members AS MATERIALIZED (
        SELECT member.node_id, chunks.qname_id, member.value_bits FROM chunks
        CROSS JOIN LATERAL unnest(chunks.node_ids, chunks.value_bits) member(node_id, value_bits)
    )
    SELECT name.value AS local_name, field.value AS qname, members.value_bits
    FROM members JOIN nodes USING (node_id)
    JOIN names name ON name.string_id = nodes.name_id
    JOIN names field ON field.string_id = members.qname_id
    OFFSET 0
) projected;
REVOKE ALL ON babylon_state.graph_node_vector_v1,babylon_state.graph_string_lookup_v1,babylon_state.graph_node_lookup_v1,babylon_state.graph_node_manifest_v1,babylon_state.graph_node_chunk_v1,babylon_state.graph_node_f64_chunk_v1,babylon_state.graph_node_v1,babylon_state.graph_node_f64_v1 FROM PUBLIC;
CREATE FUNCTION babylon_state.graph_lookup_immutable_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO 'pg_catalog' AS $$
BEGIN
 RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_lookup_append_only';
END $$;
CREATE TRIGGER graph_string_lookup_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.graph_string_lookup_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_immutable_v1();
CREATE TRIGGER graph_node_vector_immutable_v1 BEFORE UPDATE OR DELETE ON babylon_state.graph_node_vector_v1 FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_immutable_v1();
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
 -- References are direct, campaign-owned and from this tick or a durable origin.
 IF EXISTS(
  SELECT 1 FROM (
   SELECT campaign_id,vector_id FROM babylon_state.graph_node_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick
   UNION ALL SELECT campaign_id,vector_id FROM babylon_state.graph_node_f64_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick
  ) c LEFT JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id)
  WHERE v.vector_id IS NULL OR v.first_tick>m.resolve_tick OR (v.first_tick<>m.resolve_tick AND NOT EXISTS(SELECT 1 FROM babylon_state.tick_commit p WHERE p.campaign_id=v.campaign_id AND p.resolve_tick=v.first_tick))
 ) THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_vector_reference'; END IF;
 IF EXISTS(SELECT 1 FROM babylon_state.graph_node_f64_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick AND cardinality(c.value_bits)<>cardinality(v.node_ids)) THEN
  RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_vector_length';
 END IF;

 SELECT count(*)<>m.node_chunks OR coalesce(sum(cardinality(v.node_ids)),0)<>m.node_count
  OR (count(*)>0 AND (min(ordinal)<>0 OR max(ordinal)<>count(*)-1)) INTO bad
 FROM babylon_state.graph_node_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_chunk_gap_or_count'; END IF;
 SELECT count(*)<>m.f64_chunks OR coalesce(sum(cardinality(v.node_ids)),0)<>m.f64_count INTO bad
 FROM babylon_state.graph_node_f64_chunk_v1 c JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id) WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick;
 IF bad OR EXISTS(SELECT 1 FROM babylon_state.graph_node_f64_chunk_v1 WHERE campaign_id=m.campaign_id AND resolve_tick=m.resolve_tick GROUP BY qname_id HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1) THEN
  RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_chunk_gap_or_count';
 END IF;
 -- Validate array refs and one current type per local name in one set operation.
 WITH chunks AS MATERIALIZED (
  SELECT v.node_ids FROM babylon_state.graph_node_chunk_v1 c
  JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id)
  WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick
 ), members AS MATERIALIZED (
  SELECT u.node_id FROM chunks c CROSS JOIN LATERAL unnest(c.node_ids) u(node_id)
 ), nodes AS MATERIALIZED (
  SELECT node_id,name_id,type_id,first_tick FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=m.campaign_id
 ), strings AS MATERIALIZED (
  SELECT string_id,first_tick FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=m.campaign_id
 ), joined AS (
  SELECT a.node_id,n.name_id,n.first_tick,s.first_tick AS name_tick,t.first_tick AS type_tick
  FROM members a LEFT JOIN nodes n USING(node_id)
  LEFT JOIN strings s ON s.string_id=n.name_id LEFT JOIN strings t ON t.string_id=n.type_id
 )
 SELECT count(*)<>count(name_id) OR count(*)<>count(DISTINCT name_id) OR coalesce(bool_or(first_tick>m.resolve_tick OR name_tick>m.resolve_tick OR type_tick>m.resolve_tick),false) INTO bad FROM joined;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_node_reference_or_duplicate'; END IF;
 WITH chunks AS MATERIALIZED (
  SELECT v.node_ids FROM babylon_state.graph_node_chunk_v1 c
  JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id)
  WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick
 ), members AS MATERIALIZED (
  SELECT u.node_id FROM chunks c CROSS JOIN LATERAL unnest(c.node_ids) u(node_id)
 ), attribute_chunks AS MATERIALIZED (
  SELECT c.qname_id,v.node_ids FROM babylon_state.graph_node_f64_chunk_v1 c
  JOIN babylon_state.graph_node_vector_v1 v USING(campaign_id,vector_id)
  WHERE c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick
 ), attrs AS MATERIALIZED (
  SELECT c.qname_id,u.node_id FROM attribute_chunks c CROSS JOIN LATERAL unnest(c.node_ids) u(node_id)
 )
 -- The planner cannot derive expanded vector lengths from chunk estimates.
 -- Set difference checks membership once even for a not-yet-analyzed period.
 SELECT EXISTS (
  SELECT node_id FROM attrs EXCEPT SELECT node_id FROM members
 ) OR EXISTS (
  SELECT 1 FROM attrs GROUP BY node_id,qname_id HAVING count(*)>1
 ) OR EXISTS (
  SELECT qname_id FROM attribute_chunks
  INTERSECT
  SELECT string_id FROM babylon_state.graph_string_lookup_v1
  WHERE campaign_id=m.campaign_id AND first_tick>m.resolve_tick
 ) INTO bad;
 IF bad THEN RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_f64_reference_or_duplicate'; END IF;
 -- Dense append-only IDs make count-based assignment explicit and checked.
 IF EXISTS(SELECT 1 FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(string_id)<>0 OR max(string_id)<>count(*)-1)
 OR EXISTS(SELECT 1 FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=m.campaign_id HAVING min(node_id)<>0 OR max(node_id)<>count(*)-1)
 OR EXISTS(SELECT 1 FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=m.campaign_id HAVING min(vector_id)<>0 OR max(vector_id)<>count(*)-1) THEN
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
 IF TG_TABLE_NAME='graph_node_vector_v1' THEN
  IF EXISTS(SELECT 1 FROM graph_new_rows n JOIN babylon_state.graph_node_vector_v1 v ON v.campaign_id=n.campaign_id AND v.node_ids=n.node_ids AND v.vector_id<>n.vector_id) THEN
   RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_vector_duplicate';
  END IF;
  IF EXISTS(SELECT 1 FROM graph_new_rows v CROSS JOIN LATERAL unnest(v.node_ids) u(node_id) LEFT JOIN babylon_state.graph_node_lookup_v1 n ON n.campaign_id=v.campaign_id AND n.node_id=u.node_id WHERE n.node_id IS NULL OR n.first_tick>v.first_tick OR (n.first_tick>0 AND n.first_tick<>v.first_tick AND NOT EXISTS(SELECT 1 FROM babylon_state.tick_commit p WHERE p.campaign_id=n.campaign_id AND p.resolve_tick=n.first_tick))) THEN
   RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='graph_vector_node_reference';
  END IF;
 END IF;
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
CREATE TRIGGER graph_node_vector_insert_guard_v1 AFTER INSERT ON babylon_state.graph_node_vector_v1 REFERENCING NEW TABLE AS graph_new_rows FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.graph_lookup_insert_guard_v1();
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
 OR EXISTS(SELECT 1 FROM fields f WHERE f.ordinal IS NULL OR f.position NOT BETWEEN 0 AND 4294967295 OR f.field_name IS NULL OR (f.value_tag=6 AND (f.enum_type IS NULL OR f.enum_member IS NULL)) OR (f.value_tag>=7 AND f.stable_key IS NULL))
 OR EXISTS(SELECT f.ordinal FROM fields f WHERE f.ordinal IS NOT NULL EXCEPT SELECT e.ordinal FROM parents e)
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

-- Derived money evidence is published by the database owner after observer authentication.
-- It is independent of tick adjudication and never supplies simulation inputs.
CREATE TABLE babylon_state.money_journal_period_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL CHECK (resolve_tick > 0),
    journal_version smallint NOT NULL CHECK (journal_version = 1),
    tick_content_hash bytea NOT NULL CHECK (octet_length(tick_content_hash) = 32),
    envelope_digest bytea NOT NULL CHECK (octet_length(envelope_digest) = 32),
    schema_sha256 bytea NOT NULL CHECK (octet_length(schema_sha256) = 32),
    foundation_sha256 bytea NOT NULL CHECK (octet_length(foundation_sha256) = 32),
    content_sha256 bytea NOT NULL CHECK (octet_length(content_sha256) = 32),
    source_identity_bytes bytea NOT NULL CHECK (octet_length(source_identity_bytes) BETWEEN 1 AND 1024),
    receipt_sha256 bytea NOT NULL CHECK (octet_length(receipt_sha256) = 32),
    movement_sha256 bytea NOT NULL CHECK (octet_length(movement_sha256) = 32),
    movement_count bigint NOT NULL CHECK (movement_count >= 0),
    payment_sha256 bytea NOT NULL CHECK (octet_length(payment_sha256) = 32),
    payment_count bigint NOT NULL CHECK (payment_count BETWEEN 0 AND movement_count),
    site_accounting_sha256 bytea NOT NULL CHECK (octet_length(site_accounting_sha256) = 32),
    site_accounting_directory bytea NOT NULL
        CHECK (pg_catalog.sha256(site_accounting_directory) = site_accounting_sha256),
    site_monetary_books boolean NOT NULL,
    site_count bigint NOT NULL CHECK (site_count BETWEEN 0 AND 16777215
        AND octet_length(site_accounting_directory)::bigint = 64 * site_count),
    site_stock_count bigint NOT NULL CHECK (site_stock_count >= 0),
    detail_retained boolean NOT NULL,
    PRIMARY KEY (campaign_id, resolve_tick),
    FOREIGN KEY (campaign_id, resolve_tick) REFERENCES babylon_state.tick_commit(campaign_id, resolve_tick),
    FOREIGN KEY (campaign_id) REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id)
);
-- Keep large directories uncompressed so the selected-site reader can fetch a single TOAST slice.
ALTER TABLE babylon_state.money_journal_period_v1 ALTER COLUMN site_accounting_directory SET STORAGE EXTERNAL;
-- Ordinals are native source keys. Explicit slots also preserve gaps.
CREATE FUNCTION babylon_state.movement_slots_v1(slots smallint[])
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path = pg_catalog AS $$
    SELECT cardinality(slots) BETWEEN 1 AND 128
       AND array_ndims(slots)=1 AND array_lower(slots,1)=1
       AND slots=ARRAY(SELECT DISTINCT s FROM unnest(slots) AS u(s)
                       WHERE s BETWEEN 0 AND 127 ORDER BY s)
$$;
REVOKE ALL ON FUNCTION babylon_state.movement_slots_v1(smallint[]) FROM PUBLIC;
CREATE TABLE babylon_state.money_movement_block_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL,
    block_ordinal bigint NOT NULL CHECK (block_ordinal BETWEEN 0 AND 72057594037927935),
    slots smallint[] NOT NULL CHECK (babylon_state.movement_slots_v1(slots)),
    purpose text[] NOT NULL,
    reference_kind text[] NOT NULL,
    reference_id bytea[] NOT NULL,
    payer_key integer[] NOT NULL,
    recipient_key integer[] NOT NULL,
    amount_micros numeric[] NOT NULL,
    CHECK (array_dims(purpose) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(reference_kind) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(reference_id) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(payer_key) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(recipient_key) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(amount_micros) IS NOT DISTINCT FROM array_dims(slots)),
    PRIMARY KEY(campaign_id,resolve_tick,block_ordinal),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.money_journal_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE FUNCTION babylon_state.money_movement_values_v1(a_purpose text[], a_reference_kind text[], a_reference_id bytea[], a_payer_key integer[], a_recipient_key integer[], a_amount_micros numeric[])
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path = pg_catalog AS $$
    SELECT NOT EXISTS (
        SELECT FROM unnest(a_purpose, a_reference_kind, a_reference_id, a_payer_key, a_recipient_key, a_amount_micros)
            AS r(purpose, reference_kind, reference_id, payer_key, recipient_key, amount_micros)
        WHERE (r.amount_micros IS NOT NULL AND scale(r.amount_micros)=0
            AND r.amount_micros BETWEEN 1 AND 170141183460469231731687303715884105727
            AND CASE
                WHEN r.purpose IN ('purchase_reservation','delivery_settlement','purchase_refund') THEN
                    r.reference_kind IN ('delivery','local_final_demand','service') AND octet_length(r.reference_id)=32
                WHEN r.purpose IN ('shift_reservation','wage_payment','shift_cancellation') THEN
                    r.reference_kind='shift' AND octet_length(r.reference_id)=32
                WHEN r.purpose IN ('tax','public_transfer','household_transfer','ownership_distribution',
                        'capital_contribution','transport_service','mutual_aid') THEN
                    r.reference_kind IS NULL AND r.reference_id IS NULL
                ELSE false END
            AND CASE
                WHEN r.purpose IN ('purchase_reservation','shift_reservation') THEN
                    r.payer_key IS NOT NULL AND r.recipient_key IS NULL
                WHEN r.purpose IN ('purchase_refund','shift_cancellation') THEN
                    r.payer_key IS NULL AND r.recipient_key IS NOT NULL
                WHEN r.purpose IN ('delivery_settlement','wage_payment') THEN
                    r.payer_key IS NOT NULL AND r.recipient_key IS NOT NULL
                ELSE r.payer_key<>r.recipient_key END) IS NOT TRUE
    )
$$;
ALTER TABLE babylon_state.money_movement_block_v1 ADD CHECK (babylon_state.money_movement_values_v1(purpose,reference_kind,reference_id,payer_key,recipient_key,amount_micros));
CREATE VIEW babylon_state.money_movement_v1 AS
SELECT b.campaign_id,b.resolve_tick,b.block_ordinal*128+r.slot AS ordinal,
       r.purpose,r.reference_kind,r.reference_id,r.payer_key,r.recipient_key,r.amount_micros
FROM babylon_state.money_movement_block_v1 b
CROSS JOIN LATERAL unnest(b.slots,b.purpose,b.reference_kind,b.reference_id,b.payer_key,b.recipient_key,b.amount_micros)
    AS r(slot,purpose,reference_kind,reference_id,payer_key,recipient_key,amount_micros);
REVOKE ALL ON babylon_state.money_movement_block_v1,babylon_state.money_movement_v1 FROM PUBLIC;
REVOKE ALL ON FUNCTION babylon_state.money_movement_values_v1(text[],text[],bytea[],integer[],integer[],numeric[]) FROM PUBLIC;
-- NUMERIC aggregates intentionally exceed i128: individual transfers remain bounded.
CREATE TABLE babylon_state.money_movement_total_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    purpose text NOT NULL CHECK (purpose IN ('purchase_reservation','delivery_settlement','purchase_refund',
        'shift_reservation','wage_payment','shift_cancellation','tax','public_transfer',
        'household_transfer','ownership_distribution','capital_contribution','transport_service','mutual_aid')),
    movement_count bigint NOT NULL CHECK (movement_count > 0),
    amount_micros numeric NOT NULL CHECK (scale(amount_micros) = 0 AND amount_micros > 0
        AND amount_micros <= movement_count::numeric * 170141183460469231731687303715884105727),
    PRIMARY KEY (campaign_id, resolve_tick, purpose),
    FOREIGN KEY (campaign_id, resolve_tick) REFERENCES babylon_state.money_journal_period_v1(campaign_id, resolve_tick)
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
REVOKE ALL ON babylon_state.money_journal_period_v1, babylon_state.money_movement_v1,
    babylon_state.money_movement_total_v1 FROM PUBLIC;

-- Source datum is TIGER NAD83. These internal points locate a county for display.
CREATE TABLE babylon_state.economic_flow_location_v1 (
    campaign_id uuid NOT NULL,
    foundation_sha256 bytea NOT NULL CHECK (octet_length(foundation_sha256) = 32),
    location_key text NOT NULL CHECK (location_key ~ '^county:[0-9]{5}$'),
    longitude numeric NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    latitude numeric NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    county_internal_point public.geometry(Point,4269) GENERATED ALWAYS AS
        (public.ST_SetSRID(public.ST_MakePoint(longitude::double precision, latitude::double precision),4269)) STORED,
    PRIMARY KEY (campaign_id, location_key),
    FOREIGN KEY (campaign_id) REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX economic_flow_location_point_v1 ON babylon_state.economic_flow_location_v1
    USING gist (county_internal_point);
REVOKE ALL ON babylon_state.economic_flow_location_v1 FROM PUBLIC;

-- Captured opening membership and exact beneficial ownership, shared by all journal periods.
CREATE TABLE babylon_state.economic_company_v1 (
    campaign_id uuid NOT NULL,
    foundation_sha256 bytea NOT NULL CHECK (octet_length(foundation_sha256) = 32),
    company_id bytea NOT NULL CHECK (octet_length(company_id) = 32),
    industry_key text NOT NULL CHECK (industry_key <> ''),
    label text NOT NULL CHECK (label <> ''),
    band text NOT NULL CHECK (band IN ('first_national','second_national','regional')),
    division smallint CHECK (division BETWEEN 1 AND 9),
    employed numeric(20,0) NOT NULL CHECK (employed BETWEEN 1 AND 18446744073709551615),
    sites numeric(20,0) NOT NULL CHECK (sites BETWEEN 1 AND 18446744073709551615),
    opening_cash_micros numeric(39,0) NOT NULL CHECK (opening_cash_micros BETWEEN 0 AND 170141183460469231731687303715884105727),
    subsidiary_capital_micros numeric(39,0) NOT NULL CHECK (subsidiary_capital_micros BETWEEN 0 AND 170141183460469231731687303715884105727),
    original_capital_micros numeric(39,0) NOT NULL CHECK (original_capital_micros BETWEEN 0 AND 170141183460469231731687303715884105727),
    common_denominator numeric(39,0) NOT NULL CHECK (common_denominator BETWEEN 1 AND 340282366920938463463374607431768211455),
    total_weight numeric(39,0) NOT NULL CHECK (total_weight BETWEEN 1 AND 340282366920938463463374607431768211455),
    CHECK ((band='regional') = (division IS NOT NULL)),
    CHECK (original_capital_micros = opening_cash_micros + subsidiary_capital_micros),
    CHECK (total_weight = original_capital_micros * common_denominator),
    PRIMARY KEY (campaign_id,company_id),
    UNIQUE (campaign_id,foundation_sha256,company_id),
    FOREIGN KEY (campaign_id) REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id)
);
REVOKE ALL ON babylon_state.economic_company_v1 FROM PUBLIC;

-- Account geography and operating function come from the captured foundation.
-- A missing classification is distinct from a zero balance or zero payments.
CREATE TABLE babylon_state.economic_flow_account_v1 (
    campaign_id uuid NOT NULL,
    account_key integer NOT NULL CHECK (account_key >= 0),
    foundation_sha256 bytea NOT NULL CHECK (octet_length(foundation_sha256) = 32),
    account_kind text NOT NULL CHECK (account_kind IN ('site_cash','household_cash','organization_cash','public_cash','company_cash')),
    account_id bytea NOT NULL CHECK (octet_length(account_id) = 32),
    location_key text CHECK (length(location_key) > 0),
    catchment_key text CHECK (length(catchment_key) > 0),
    industry_key text CHECK (length(industry_key) > 0),
    industry_label text CHECK (length(industry_label) > 0),
    CHECK ((industry_key IS NULL) = (industry_label IS NULL)),
    PRIMARY KEY (campaign_id, account_key),
    UNIQUE (campaign_id, account_kind, account_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (campaign_id) REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id)
        DEFERRABLE INITIALLY DEFERRED
);
-- Keep one native account FK per distinct period principal. The directory never
-- changes an economic payer behind a reserve or manufactures a recipient.
CREATE TABLE babylon_state.money_movement_account_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL, account_key integer NOT NULL,
    PRIMARY KEY(campaign_id,resolve_tick,account_key),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.money_journal_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(campaign_id,account_key) REFERENCES babylon_state.economic_flow_account_v1
);
CREATE FUNCTION babylon_state.money_movement_accounts_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    PERFORM babylon_state.economic_reference_lock_v1(NEW.campaign_id);
    INSERT INTO babylon_state.money_movement_account_v1
    SELECT DISTINCT NEW.campaign_id,NEW.resolve_tick,k FROM unnest(NEW.payer_key||NEW.recipient_key) AS e(k)
    WHERE k IS NOT NULL ORDER BY k
    -- The conflict action locks the existing key until commit. Its false
    -- predicate keeps an immutable roster row intact. New keys use both
    -- native foreign keys. The campaign lock also rejects stale snapshots.
    ON CONFLICT (campaign_id,resolve_tick,account_key)
    DO UPDATE SET account_key=EXCLUDED.account_key WHERE false;
    RETURN NEW;
END $$;
CREATE TRIGGER money_movement_accounts_v1
BEFORE INSERT OR UPDATE OF campaign_id,resolve_tick,payer_key,recipient_key ON babylon_state.money_movement_block_v1
FOR EACH ROW EXECUTE FUNCTION babylon_state.money_movement_accounts_v1();
CREATE FUNCTION babylon_state.money_movement_reference_change_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF TG_OP='TRUNCATE' THEN
        RAISE foreign_key_violation USING MESSAGE='retire movement references with scoped DELETE';
    END IF;
    IF TG_OP='UPDATE' THEN
        RAISE foreign_key_violation USING MESSAGE='movement endpoint reference is immutable';
    END IF;
    PERFORM babylon_state.economic_reference_lock_v1(q.campaign_id)
    FROM (SELECT DISTINCT campaign_id FROM retired ORDER BY campaign_id) AS q;
    IF EXISTS (SELECT FROM retired o JOIN babylon_state.money_movement_block_v1 b USING(campaign_id,resolve_tick)
               WHERE o.account_key=ANY(b.payer_key) OR o.account_key=ANY(b.recipient_key)) THEN
        RAISE foreign_key_violation USING MESSAGE='retained movement still uses the endpoint';
    END IF;
    RETURN NULL;
END $$;
CREATE TRIGGER money_movement_reference_update_v1 BEFORE UPDATE ON babylon_state.money_movement_account_v1
FOR EACH ROW EXECUTE FUNCTION babylon_state.money_movement_reference_change_v1();
CREATE TRIGGER money_movement_reference_delete_v1 AFTER DELETE ON babylon_state.money_movement_account_v1
REFERENCING OLD TABLE AS retired FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.money_movement_reference_change_v1();
CREATE TRIGGER money_movement_reference_truncate_v1 BEFORE TRUNCATE ON babylon_state.money_movement_account_v1
FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.money_movement_reference_change_v1();
REVOKE ALL ON babylon_state.money_movement_account_v1 FROM PUBLIC;
REVOKE ALL ON FUNCTION babylon_state.money_movement_accounts_v1(), babylon_state.money_movement_reference_change_v1() FROM PUBLIC;
REVOKE ALL ON babylon_state.economic_flow_account_v1 FROM PUBLIC;

-- Compact per-site accounts and physical stock survive movement detail retention.
CREATE TABLE babylon_state.site_principal_v1 (
    campaign_id uuid NOT NULL REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id)
        DEFERRABLE INITIALLY DEFERRED,
    site_key integer NOT NULL CHECK (site_key BETWEEN 0 AND 16777214),
    foundation_sha256 bytea NOT NULL CHECK (octet_length(foundation_sha256)=32),
    site_id bytea NOT NULL CHECK (octet_length(site_id)=32),
    PRIMARY KEY (campaign_id,site_key),
    UNIQUE (campaign_id,site_id) DEFERRABLE INITIALLY DEFERRED
);
-- Opening ownership uses the signed physical site roster. Each beneficiary's original
-- carrying value is independent of the company allocation and stays explicit.
CREATE TABLE babylon_state.economic_company_member_key_v1 (
    campaign_id uuid NOT NULL, site_key integer NOT NULL,
    company_id bytea NOT NULL CHECK(octet_length(company_id)=32),
    county_geoid text NOT NULL CHECK(county_geoid ~ '^[0-9]{5}$'),
    opening_employed numeric(20,0) NOT NULL CHECK(opening_employed BETWEEN 0 AND 18446744073709551615),
    original_cash_micros numeric(39,0) NOT NULL CHECK(original_cash_micros BETWEEN 0 AND 170141183460469231731687303715884105727),
    cash_floor_micros numeric(39,0) NOT NULL CHECK(cash_floor_micros BETWEEN 0 AND 170141183460469231731687303715884105727),
    swept_micros numeric(39,0) NOT NULL CHECK(swept_micros BETWEEN 0 AND LEAST(original_cash_micros,original_capital_micros)),
    original_capital_micros numeric(39,0) NOT NULL CHECK(original_capital_micros BETWEEN 0 AND 170141183460469231731687303715884105727),
    CHECK(swept_micros=0 OR original_cash_micros-swept_micros>=cash_floor_micros),
    PRIMARY KEY(campaign_id,site_key),
    FOREIGN KEY(campaign_id,site_key) REFERENCES babylon_state.site_principal_v1 DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(campaign_id,company_id) REFERENCES babylon_state.economic_company_v1 ON DELETE CASCADE
);
CREATE INDEX economic_company_members_by_parent_v1 ON babylon_state.economic_company_member_key_v1(campaign_id,company_id,site_key);
CREATE TABLE babylon_state.economic_company_original_share_v1 (
    campaign_id uuid NOT NULL,site_key integer NOT NULL,
    beneficiary_kind text NOT NULL CHECK(beneficiary_kind IN ('site_cash','household_cash','public_cash','organization_cash')),
    beneficiary_id bytea NOT NULL CHECK(octet_length(beneficiary_id)=32),
    original_shares numeric(20,0) NOT NULL CHECK(original_shares BETWEEN 1 AND 18446744073709551615),
    original_carrying_micros numeric(39,0) NOT NULL CHECK(original_carrying_micros BETWEEN 0 AND 170141183460469231731687303715884105727),
    PRIMARY KEY(campaign_id,site_key,beneficiary_kind,beneficiary_id),
    FOREIGN KEY(campaign_id,site_key) REFERENCES babylon_state.economic_company_member_key_v1 ON DELETE CASCADE
);
CREATE INDEX economic_company_original_beneficiary_v1 ON babylon_state.economic_company_original_share_v1(campaign_id,beneficiary_kind,beneficiary_id);
CREATE VIEW babylon_state.economic_company_member_v1 AS
SELECT m.campaign_id,c.foundation_sha256,m.company_id,s.site_id,m.county_geoid,m.opening_employed,
       m.original_cash_micros,m.cash_floor_micros,m.swept_micros,
       (m.original_cash_micros-m.swept_micros)::numeric(39,0) AS remaining_cash_micros,
       m.original_capital_micros,(m.original_capital_micros-m.swept_micros)::numeric(39,0) AS remaining_capital_micros
FROM babylon_state.economic_company_member_key_v1 m
JOIN babylon_state.economic_company_v1 c USING(campaign_id,company_id)
JOIN babylon_state.site_principal_v1 s ON (s.campaign_id,s.site_key,s.foundation_sha256)=(m.campaign_id,m.site_key,c.foundation_sha256);
-- Raw numeric arithmetic has arbitrary precision. Enforce the admitted Rust integer
-- domains before exposing the original numeric column types to observers.
CREATE DOMAIN babylon_state.company_site_shares_v1 AS numeric NOT NULL
    CHECK(VALUE BETWEEN 1 AND 18446744073709551615);
CREATE DOMAIN babylon_state.company_claim_weight_v1 AS numeric NOT NULL
    CHECK(VALUE BETWEEN 0 AND 340282366920938463463374607431768211455);
CREATE VIEW babylon_state.economic_company_claim_source_v1 AS
SELECT m.campaign_id,c.foundation_sha256,m.company_id,s.site_id,h.beneficiary_kind,h.beneficiary_id,
       h.original_shares,h.site_total_shares,m.original_capital_micros AS capital_micros,h.original_carrying_micros
FROM babylon_state.economic_company_member_key_v1 m
JOIN babylon_state.economic_company_v1 c USING(campaign_id,company_id)
JOIN babylon_state.site_principal_v1 s ON (s.campaign_id,s.site_key,s.foundation_sha256)=(m.campaign_id,m.site_key,c.foundation_sha256)
CROSS JOIN LATERAL (
    SELECT o.beneficiary_kind,o.beneficiary_id,o.original_shares,o.original_carrying_micros,
           (sum(o.original_shares) OVER())::babylon_state.company_site_shares_v1::numeric(20,0) AS site_total_shares
    FROM babylon_state.economic_company_original_share_v1 o WHERE (o.campaign_id,o.site_key)=(m.campaign_id,m.site_key)
) h;
CREATE VIEW babylon_state.economic_company_claim_v1 AS
SELECT s.campaign_id,s.foundation_sha256,s.company_id,s.beneficiary_kind,s.beneficiary_id,
       sum(s.capital_micros * s.original_shares *
           (CASE WHEN mod(c.common_denominator,s.site_total_shares)=0 THEN div(c.common_denominator,s.site_total_shares) END)
               ::babylon_state.company_claim_weight_v1)::babylon_state.company_claim_weight_v1::numeric(39,0) AS weight
FROM babylon_state.economic_company_claim_source_v1 s JOIN babylon_state.economic_company_v1 c USING(campaign_id,foundation_sha256,company_id)
GROUP BY s.campaign_id,s.foundation_sha256,s.company_id,s.beneficiary_kind,s.beneficiary_id;
REVOKE ALL ON babylon_state.economic_company_member_key_v1,babylon_state.economic_company_original_share_v1,
    babylon_state.economic_company_member_v1,babylon_state.economic_company_claim_v1,babylon_state.economic_company_claim_source_v1 FROM PUBLIC;
-- A roster block commits every admitted site identity and foundation digest in key order.
CREATE VIEW babylon_state.site_roster_source_v1 AS
SELECT campaign_id,site_key/32 AS block_key,
    bit_or(set_bit(0::bit(32),site_key%32,1)) AS members,
    sha256(string_agg(int4send(site_key)||site_id||foundation_sha256,''::bytea ORDER BY site_key)) AS sha256
FROM babylon_state.site_principal_v1 GROUP BY campaign_id,site_key/32;
CREATE TABLE babylon_state.site_roster_block_v1 (
    campaign_id uuid NOT NULL REFERENCES babylon_state.material_campaign_foundation_v3 DEFERRABLE INITIALLY DEFERRED,
    block_key integer NOT NULL CHECK(block_key BETWEEN 0 AND 524287),
    members bit(32) NOT NULL CHECK(members<>0::bit(32)),
    sha256 bytea NOT NULL CHECK(octet_length(sha256)=32),
    PRIMARY KEY(campaign_id,block_key),
    UNIQUE(campaign_id,block_key,members,sha256)
);
-- One write per changed campaign serializes source and certificate edits at every isolation level.
CREATE TABLE babylon_state.site_roster_guard_v1 (
    campaign_id uuid PRIMARY KEY REFERENCES babylon_state.material_campaign_foundation_v3 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    last_change xid8 NOT NULL
);
CREATE FUNCTION babylon_state.touch_site_roster_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
DECLARE affected text;
BEGIN
    affected := CASE TG_OP WHEN 'INSERT' THEN 'SELECT campaign_id FROM fresh'
        WHEN 'DELETE' THEN 'SELECT campaign_id FROM prior'
        ELSE 'SELECT campaign_id FROM prior UNION SELECT campaign_id FROM fresh' END;
    EXECUTE 'INSERT INTO babylon_state.site_roster_guard_v1 SELECT DISTINCT campaign_id,pg_current_xact_id() FROM ('
        || affected || ') s ORDER BY campaign_id ON CONFLICT(campaign_id) DO UPDATE SET last_change=excluded.last_change';
    RETURN NULL;
END $$;
CREATE FUNCTION babylon_state.verify_site_roster_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
BEGIN
    IF EXISTS(WITH stored AS (SELECT * FROM babylon_state.site_roster_block_v1 WHERE campaign_id=NEW.campaign_id),
                   source AS (SELECT * FROM babylon_state.site_roster_source_v1 WHERE campaign_id=NEW.campaign_id)
        SELECT FROM ((TABLE stored EXCEPT TABLE source) UNION ALL (TABLE source EXCEPT TABLE stored)) AS different) THEN
        RAISE EXCEPTION 'site roster block differs from captured principals' USING ERRCODE='23503';
    END IF;
    RETURN NULL;
END $$;
CREATE FUNCTION babylon_state.prevent_site_roster_truncate_v1() RETURNS trigger LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
BEGIN
    RAISE EXCEPTION 'delete the scoped site roster instead of truncating its source' USING ERRCODE='23503';
END $$;
CREATE CONSTRAINT TRIGGER verify_site_roster_v1 AFTER INSERT OR UPDATE ON babylon_state.site_roster_guard_v1
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.verify_site_roster_v1();
CREATE TRIGGER site_roster_insert AFTER INSERT ON babylon_state.site_principal_v1 REFERENCING NEW TABLE AS fresh
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.touch_site_roster_v1();
CREATE TRIGGER site_roster_update AFTER UPDATE ON babylon_state.site_principal_v1 REFERENCING OLD TABLE AS prior NEW TABLE AS fresh
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.touch_site_roster_v1();
CREATE TRIGGER site_roster_delete AFTER DELETE ON babylon_state.site_principal_v1 REFERENCING OLD TABLE AS prior
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.touch_site_roster_v1();
CREATE TRIGGER protect_site_roster BEFORE TRUNCATE ON babylon_state.site_principal_v1
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.prevent_site_roster_truncate_v1();
CREATE TRIGGER site_roster_insert AFTER INSERT ON babylon_state.site_roster_block_v1 REFERENCING NEW TABLE AS fresh
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.touch_site_roster_v1();
CREATE TRIGGER site_roster_update AFTER UPDATE ON babylon_state.site_roster_block_v1 REFERENCING OLD TABLE AS prior NEW TABLE AS fresh
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.touch_site_roster_v1();
CREATE TRIGGER site_roster_delete AFTER DELETE ON babylon_state.site_roster_block_v1 REFERENCING OLD TABLE AS prior
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.touch_site_roster_v1();
CREATE TRIGGER protect_site_roster BEFORE TRUNCATE ON babylon_state.site_roster_block_v1
    FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.prevent_site_roster_truncate_v1();

-- A NULL exception vector means that every included source ordinal equals its foundation site key.
CREATE FUNCTION babylon_state.site_ordinals_valid_v1(block_key integer,present bit,ordinals integer[])
RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path TO pg_catalog AS $$
    SELECT ordinals IS NULL OR (array_ndims(ordinals)=1 AND array_lower(ordinals,1)=1 AND cardinality(ordinals)=32
        AND EXISTS(SELECT FROM unnest(ordinals) v WHERE v IS NOT NULL)
        AND NOT EXISTS(SELECT FROM unnest(ordinals) WITH ORDINALITY e(v,i) WHERE v IS NOT NULL AND
            (get_bit(present,(i-1)::integer)=0 OR v=block_key::bigint*32+i-1 OR v NOT BETWEEN 0 AND 16777214)))
$$;
-- Each contiguous slice has the same sixty fixed-point fields and equations as the native journal.
-- Internal NULL cells represent zero in monetary books. The books mask preserves physical-only sites.
CREATE FUNCTION babylon_state.site_postings_valid_v1(books bit,lines numeric[])
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path TO pg_catalog AS $$
    SELECT NOT EXISTS(SELECT FROM generate_series(0,31) AS s(slot)
        CROSS JOIN LATERAL (SELECT lines[slot*60+1:(slot+1)*60] AS line OFFSET 0) AS r
        WHERE CASE WHEN get_bit(books,slot)=0 THEN EXISTS(SELECT FROM unnest(r.line) v WHERE v IS NOT NULL)
            ELSE
                -- closing total assets
                coalesce(r.line[24],0) <> coalesce(r.line[26],0) + coalesce(r.line[30],0)
                -- opening total assets
                OR coalesce(r.line[9],0) <> coalesce(r.line[11],0) + coalesce(r.line[15],0)
                -- closing total equity
                OR coalesce(r.line[30],0) <> coalesce(r.line[60],0) + coalesce(r.line[15],0)
                -- net income
                OR coalesce(r.line[57],0) <> coalesce(r.line[60],0) + coalesce(r.line[59],0) - coalesce(r.line[58],0)
                -- closing cash
                OR coalesce(r.line[16],0) <> coalesce(r.line[1],0) + coalesce(r.line[53],0) + coalesce(r.line[54],0) + coalesce(r.line[55],0) + coalesce(r.line[56],0)
        END)
$$;
CREATE TABLE babylon_state.site_statement_block_v1 (
    campaign_id uuid NOT NULL,resolve_tick bigint NOT NULL,block_key integer NOT NULL,
    present bit(32) NOT NULL CHECK(present<>0::bit(32)),books bit(32) NOT NULL CHECK((present & books)=books),
    lines numeric(39,0)[] COMPRESSION lz4 NOT NULL CHECK(array_ndims(lines)=1 AND array_lower(lines,1)=1
        AND cardinality(lines)=1920 AND array_position(lines,0::numeric) IS NULL
        AND babylon_state.site_postings_valid_v1(books,lines)),
    roster_members bit(32) NOT NULL CHECK((present & roster_members)=present),
    roster_sha256 bytea NOT NULL,ordinal_exceptions integer[],
    CHECK(babylon_state.site_ordinals_valid_v1(block_key,present,ordinal_exceptions)),
    PRIMARY KEY(campaign_id,resolve_tick,block_key),
    UNIQUE(campaign_id,resolve_tick,block_key,present),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.money_journal_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(campaign_id,block_key,roster_members,roster_sha256)
        REFERENCES babylon_state.site_roster_block_v1(campaign_id,block_key,members,sha256) DEFERRABLE INITIALLY DEFERRED
);
CREATE VIEW babylon_state.site_statement_v1 AS
SELECT b.campaign_id,coalesce(b.ordinal_exceptions[k.site_key%32+1],k.site_key) AS site_ordinal,b.resolve_tick,k.site_key,
    (CASE WHEN r.monetary THEN coalesce(r.line[1],0) END)::numeric(39,0) AS opening_cash_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[2],0) END)::numeric(39,0) AS opening_purchase_reserves_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[3],0) END)::numeric(39,0) AS opening_payroll_reserves_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[4],0) END)::numeric(39,0) AS opening_wage_receivables_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[5],0) END)::numeric(39,0) AS opening_inventory_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[6],0) END)::numeric(39,0) AS opening_freight_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[7],0) END)::numeric(39,0) AS opening_equity_investments_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[8],0) END)::numeric(39,0) AS opening_equipment_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[9],0) END)::numeric(39,0) AS opening_total_assets_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[10],0) END)::numeric(39,0) AS opening_wage_payables_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[11],0) END)::numeric(39,0) AS opening_total_liabilities_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[12],0) END)::numeric(39,0) AS opening_opening_capital_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[13],0) END)::numeric(39,0) AS opening_contributed_capital_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[14],0) END)::numeric(39,0) AS opening_retained_earnings_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[15],0) END)::numeric(39,0) AS opening_total_equity_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[16],0) END)::numeric(39,0) AS closing_cash_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[17],0) END)::numeric(39,0) AS closing_purchase_reserves_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[18],0) END)::numeric(39,0) AS closing_payroll_reserves_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[19],0) END)::numeric(39,0) AS closing_wage_receivables_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[20],0) END)::numeric(39,0) AS closing_inventory_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[21],0) END)::numeric(39,0) AS closing_freight_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[22],0) END)::numeric(39,0) AS closing_equity_investments_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[23],0) END)::numeric(39,0) AS closing_equipment_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[24],0) END)::numeric(39,0) AS closing_total_assets_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[25],0) END)::numeric(39,0) AS closing_wage_payables_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[26],0) END)::numeric(39,0) AS closing_total_liabilities_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[27],0) END)::numeric(39,0) AS closing_opening_capital_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[28],0) END)::numeric(39,0) AS closing_contributed_capital_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[29],0) END)::numeric(39,0) AS closing_retained_earnings_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[30],0) END)::numeric(39,0) AS closing_total_equity_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[31],0) END)::numeric(39,0) AS income_sales_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[32],0) END)::numeric(39,0) AS income_wage_income_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[33],0) END)::numeric(39,0) AS income_cost_of_goods_sold_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[34],0) END)::numeric(39,0) AS income_productive_labor_capitalized_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[35],0) END)::numeric(39,0) AS income_installation_labor_capitalized_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[36],0) END)::numeric(39,0) AS income_equipment_wear_capitalized_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[37],0) END)::numeric(39,0) AS income_idle_labor_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[38],0) END)::numeric(39,0) AS income_handling_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[39],0) END)::numeric(39,0) AS income_maintenance_labor_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[40],0) END)::numeric(39,0) AS income_maintenance_material_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[41],0) END)::numeric(39,0) AS income_freight_loss_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[42],0) END)::numeric(39,0) AS income_consumption_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[43],0) END)::numeric(39,0) AS income_final_demand_outlay_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[44],0) END)::numeric(39,0) AS income_unused_service_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[45],0) END)::numeric(39,0) AS income_tax_income_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[46],0) END)::numeric(39,0) AS income_tax_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[47],0) END)::numeric(39,0) AS income_public_transfer_income_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[48],0) END)::numeric(39,0) AS income_public_transfer_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[49],0) END)::numeric(39,0) AS income_distribution_income_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[50],0) END)::numeric(39,0) AS income_gift_income_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[51],0) END)::numeric(39,0) AS income_gift_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[52],0) END)::numeric(39,0) AS income_agency_observation_labor_expense_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[53],0) END)::numeric(39,0) AS cash_flow_operating_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[54],0) END)::numeric(39,0) AS cash_flow_investing_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[55],0) END)::numeric(39,0) AS cash_flow_financing_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[56],0) END)::numeric(39,0) AS cash_flow_reserve_reclassification_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[57],0) END)::numeric(39,0) AS net_income_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[58],0) END)::numeric(39,0) AS contributions_received_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[59],0) END)::numeric(39,0) AS distributions_paid_micros,
    (CASE WHEN r.monetary THEN coalesce(r.line[60],0) END)::numeric(39,0) AS change_in_equity_micros
FROM babylon_state.site_principal_v1 k JOIN babylon_state.site_statement_block_v1 b
    ON b.campaign_id=k.campaign_id AND b.block_key=k.site_key/32 AND get_bit(b.present,k.site_key%32)=1
CROSS JOIN LATERAL (SELECT b.lines[(k.site_key%32)*60+1:(k.site_key%32+1)*60] AS line,
    get_bit(b.books,k.site_key%32)=1 AS monetary OFFSET 0) r;

-- Per-period commodity identities come from the actual opening/closing stock union.
CREATE TABLE babylon_state.site_stock_key_v1 (
    campaign_id uuid NOT NULL,
    resolve_tick bigint NOT NULL,
    commodity_ordinal integer NOT NULL CHECK (commodity_ordinal>=0),
    good_id bytea NOT NULL CHECK (octet_length(good_id)=32),
    unit_id bytea NOT NULL CHECK (octet_length(unit_id)=32),
    PRIMARY KEY (campaign_id,resolve_tick,commodity_ordinal),
    UNIQUE (campaign_id,resolve_tick,good_id,unit_id),
    FOREIGN KEY (campaign_id,resolve_tick) REFERENCES babylon_state.money_journal_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE FUNCTION babylon_state.site_stock_slots_valid_v1(slots bit,oq numeric[],cq numeric[],oc numeric[],cc numeric[])
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path TO pg_catalog AS $$
    SELECT NOT EXISTS(SELECT FROM unnest(oq,cq,oc,cc) WITH ORDINALITY v(o,c,op,cp,i)
        WHERE CASE WHEN get_bit(slots,(i-1)::integer)=1 THEN
            (o IS NULL AND c IS NULL) OR o NOT BETWEEN 0 AND 18446744073709551615
            OR c NOT BETWEEN 0 AND 18446744073709551615 OR op<0 OR cp<0
            OR (o IS NULL AND op IS NOT NULL) OR (c IS NULL AND cp IS NOT NULL)
        ELSE num_nonnulls(o,c,op,cp)>0 END)
$$;
CREATE TABLE babylon_state.site_stock_block_v1 (
    campaign_id uuid NOT NULL,resolve_tick bigint NOT NULL,block_key integer NOT NULL,commodity_ordinal integer NOT NULL,
    present bit(32) NOT NULL,stocks bit(32) NOT NULL CHECK(stocks<>0::bit(32) AND (present & stocks)=stocks),
    opening_quantities numeric(20,0)[] NOT NULL,closing_quantities numeric(20,0)[] NOT NULL,
    opening_costs numeric(39,0)[] NOT NULL,closing_costs numeric(39,0)[] NOT NULL,
    CHECK(array_dims(opening_quantities) IS NOT DISTINCT FROM '[1:32]' AND array_dims(closing_quantities) IS NOT DISTINCT FROM '[1:32]'
        AND array_dims(opening_costs) IS NOT DISTINCT FROM '[1:32]' AND array_dims(closing_costs) IS NOT DISTINCT FROM '[1:32]'),
    CHECK(babylon_state.site_stock_slots_valid_v1(stocks,opening_quantities,closing_quantities,opening_costs,closing_costs)),
    PRIMARY KEY(campaign_id,resolve_tick,block_key,commodity_ordinal),
    FOREIGN KEY(campaign_id,resolve_tick,commodity_ordinal) REFERENCES babylon_state.site_stock_key_v1 DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(campaign_id,resolve_tick,block_key,present) REFERENCES babylon_state.site_statement_block_v1(campaign_id,resolve_tick,block_key,present)
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE VIEW babylon_state.site_stock_balance_v1 AS
SELECT b.campaign_id,b.resolve_tick,k.site_key,b.commodity_ordinal,
    b.opening_quantities[k.site_key%32+1]::numeric(20,0) AS opening_quantity,
    b.closing_quantities[k.site_key%32+1]::numeric(20,0) AS closing_quantity,
    b.opening_costs[k.site_key%32+1]::numeric(39,0) AS opening_carrying_cost_micros,
    b.closing_costs[k.site_key%32+1]::numeric(39,0) AS closing_carrying_cost_micros
FROM babylon_state.site_principal_v1 k JOIN babylon_state.site_stock_block_v1 b
    ON b.campaign_id=k.campaign_id AND b.block_key=k.site_key/32 AND get_bit(b.stocks,k.site_key%32)=1;
REVOKE ALL ON babylon_state.site_principal_v1,babylon_state.site_roster_source_v1,babylon_state.site_roster_block_v1,
    babylon_state.site_roster_guard_v1,babylon_state.site_statement_block_v1,babylon_state.site_statement_v1,
    babylon_state.site_stock_key_v1,babylon_state.site_stock_block_v1,babylon_state.site_stock_balance_v1 FROM PUBLIC;

REVOKE ALL ON FUNCTION babylon_state.touch_site_roster_v1(),babylon_state.verify_site_roster_v1(),
    babylon_state.prevent_site_roster_truncate_v1(),babylon_state.site_ordinals_valid_v1(integer,bit,integer[]),
    babylon_state.site_postings_valid_v1(bit,numeric[]),babylon_state.site_stock_slots_valid_v1(bit,numeric[],numeric[],numeric[],numeric[])
    FROM PUBLIC;

-- Versioned, rebuildable recorded-labor coverage and physically indexed carrying checkpoints.
CREATE TABLE babylon_state.labor_period_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK (resolve_tick>0),
    fact_sha256 bytea NOT NULL CHECK (octet_length(fact_sha256)=32),
    checkpoint_sha256 bytea NOT NULL CHECK (octet_length(checkpoint_sha256)=32),
    result_world_hash bytea NOT NULL CHECK (octet_length(result_world_hash)=32),
    node_count bigint NOT NULL CHECK (node_count>=0),
    movement_count bigint NOT NULL CHECK (movement_count>=0),
    position_count bigint NOT NULL CHECK (position_count>=0),
    opening_micro_hours numeric NOT NULL, closing_micro_hours numeric NOT NULL,
    direct_micro_hours numeric NOT NULL, released_micro_hours numeric NOT NULL,
    CHECK (LEAST(opening_micro_hours,closing_micro_hours,direct_micro_hours,released_micro_hours)>=0
       AND GREATEST(opening_micro_hours,closing_micro_hours,direct_micro_hours,released_micro_hours)<=340282366920938463463374607431768211455
       AND GREATEST(scale(opening_micro_hours),scale(closing_micro_hours),scale(direct_micro_hours),scale(released_micro_hours))=0
       AND opening_micro_hours+direct_micro_hours=closing_micro_hours+released_micro_hours),
    PRIMARY KEY(campaign_id,resolve_tick),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.money_journal_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
ALTER TABLE babylon_state.money_journal_period_v1 ADD CONSTRAINT money_labor_coverage_v1
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.labor_period_v1 DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE babylon_state.labor_checkpoint_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL,
    sha256 bytea NOT NULL CHECK(octet_length(sha256)=32),
    checkpoint_bytes bytea NOT NULL CHECK(pg_catalog.sha256(checkpoint_bytes)=sha256),
    PRIMARY KEY(campaign_id,resolve_tick),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.labor_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
-- Period ordinal references share complete typed labor identities. A mutable
-- source directory cannot alter an identity already referenced by a period.
ALTER TABLE babylon_state.economic_flow_account_v1
    ADD COLUMN labor_scope_revision integer NOT NULL DEFAULT 1 CHECK(labor_scope_revision>0),
    ADD UNIQUE(campaign_id,account_key,labor_scope_revision);
ALTER TABLE babylon_state.economic_flow_location_v1
    ADD COLUMN labor_point_revision integer NOT NULL DEFAULT 1 CHECK(labor_point_revision>0),
    ADD UNIQUE(campaign_id,location_key,labor_point_revision);

CREATE FUNCTION babylon_state.revise_labor_account_scope_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
BEGIN
    NEW.labor_scope_revision := OLD.labor_scope_revision +
        ((NEW.account_kind,NEW.account_id,NEW.location_key,NEW.catchment_key,NEW.industry_key,NEW.industry_label)
         IS DISTINCT FROM
         (OLD.account_kind,OLD.account_id,OLD.location_key,OLD.catchment_key,OLD.industry_key,OLD.industry_label))::integer;
    RETURN NEW;
END $$;
CREATE TRIGGER revise_labor_scope BEFORE UPDATE ON babylon_state.economic_flow_account_v1
    FOR EACH ROW EXECUTE FUNCTION babylon_state.revise_labor_account_scope_v1();
CREATE FUNCTION babylon_state.revise_labor_point_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
BEGIN
    -- Numeric display scale participates in the original binary descriptor hash.
    NEW.labor_point_revision := OLD.labor_point_revision +
        (record_send(ROW(NEW.longitude,NEW.latitude)) <> record_send(ROW(OLD.longitude,OLD.latitude)))::integer;
    RETURN NEW;
END $$;
CREATE TRIGGER revise_labor_point BEFORE UPDATE ON babylon_state.economic_flow_location_v1
    FOR EACH ROW EXECUTE FUNCTION babylon_state.revise_labor_point_v1();
REVOKE ALL ON FUNCTION babylon_state.revise_labor_account_scope_v1(),babylon_state.revise_labor_point_v1() FROM PUBLIC;

CREATE TABLE babylon_state.labor_product_v1 (
    campaign_id uuid NOT NULL REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id),
    product_key integer NOT NULL CHECK(product_key>0),
    good_id bytea CHECK(octet_length(good_id)=32),
    unit_id bytea NOT NULL CHECK(octet_length(unit_id)=32),
    PRIMARY KEY(campaign_id,product_key),
    UNIQUE NULLS NOT DISTINCT(campaign_id,good_id,unit_id)
);
CREATE FUNCTION babylon_state.retain_labor_identity_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
BEGIN
    IF NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'labor identities are immutable' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER retain_labor_product BEFORE UPDATE ON babylon_state.labor_product_v1
    FOR EACH ROW EXECUTE FUNCTION babylon_state.retain_labor_identity_v1();
REVOKE ALL ON FUNCTION babylon_state.retain_labor_identity_v1() FROM PUBLIC;

-- Some physical sites have no monetary book. Preserve the scope supplied by
-- the captured economic catalog for those sites without creating a cash account.
CREATE TYPE babylon_state.labor_physical_scope_v1 AS (
    scope_kind text,scope_id bytea,location_key text,catchment_key text,
    industry_key text,industry_label text,longitude numeric,latitude numeric
);
REVOKE ALL ON TYPE babylon_state.labor_physical_scope_v1 FROM PUBLIC;

CREATE TABLE babylon_state.labor_node_identity_v1 (
    campaign_id uuid NOT NULL REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id),
    descriptor_key bigint NOT NULL CHECK(descriptor_key>0),
    descriptor_sha256 bytea NOT NULL CHECK(octet_length(descriptor_sha256)=32),
    kind text NOT NULL CHECK(kind IN ('site_stock','household_stock','work','household_work','maintenance','process','sink','commercial_freight','aid_freight','equipment','installation')),
    entity_id bytea CHECK(octet_length(entity_id)=32),
    product_key integer,
    purpose text CHECK(purpose IN ('agency_observation','aid_freight_loss','final_demand_outlay','freight_loss','household_consumption','household_service_use','maintenance_expiry','unallocated_service_expiry','unused_service_expiry','organizer_cash_collection')),
    scope_key integer,scope_revision integer,location_key text,point_revision integer,
    physical_scope babylon_state.labor_physical_scope_v1,
    process_id bytea CHECK(octet_length(process_id)=32),route_id bytea CHECK(octet_length(route_id)=32),
    origin_id bytea CHECK(octet_length(origin_id)=32),destination_id bytea CHECK(octet_length(destination_id)=32),
    CHECK((kind IN ('commercial_freight','aid_freight','equipment','installation'))=(entity_id IS NOT NULL)),
    CHECK((kind='sink')=(purpose IS NOT NULL)),
    CHECK((kind IN ('commercial_freight','aid_freight'))=(route_id IS NOT NULL)
        AND (route_id IS NULL)=(origin_id IS NULL) AND (route_id IS NULL)=(destination_id IS NULL)),
    CHECK((scope_key IS NULL)=(scope_revision IS NULL) AND
        (point_revision IS NULL OR (location_key IS NOT NULL AND scope_key IS NOT NULL))),
    CHECK((kind IN ('work','household_work','site_stock','household_stock','maintenance','process','equipment','installation'))::integer
        = num_nonnulls(scope_key,physical_scope)),
    CHECK(physical_scope IS NOT DISTINCT FROM NULL OR
        ((physical_scope).scope_kind IS NOT NULL AND (physical_scope).scope_kind IN ('site_cash','household_cash')
         AND (physical_scope).scope_id IS NOT NULL AND octet_length((physical_scope).scope_id)=32
         AND ((physical_scope).industry_key IS NULL)=((physical_scope).industry_label IS NULL)
         AND ((physical_scope).longitude IS NULL)=((physical_scope).latitude IS NULL)
         AND ((physical_scope).longitude IS NULL OR ((physical_scope).longitude BETWEEN -180 AND 180 AND (physical_scope).latitude BETWEEN -90 AND 90)))),
    CHECK((kind IN ('site_stock','household_stock','commercial_freight','aid_freight','equipment','installation','work','household_work'))=(product_key IS NOT NULL)),
    CHECK((kind IN ('maintenance','process','equipment','installation'))=(process_id IS NOT NULL)),
    PRIMARY KEY(campaign_id,descriptor_key), UNIQUE(campaign_id,descriptor_sha256),
    FOREIGN KEY(campaign_id,product_key) REFERENCES babylon_state.labor_product_v1 ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY(campaign_id,scope_key,scope_revision)
        REFERENCES babylon_state.economic_flow_account_v1(campaign_id,account_key,labor_scope_revision) ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY(campaign_id,location_key,point_revision)
        REFERENCES babylon_state.economic_flow_location_v1(campaign_id,location_key,labor_point_revision) ON UPDATE RESTRICT ON DELETE RESTRICT
);
CREATE INDEX labor_node_scope_v1 ON babylon_state.labor_node_identity_v1(campaign_id,location_key)
    WHERE location_key IS NOT NULL;
CREATE INDEX labor_node_account_v1 ON babylon_state.labor_node_identity_v1(campaign_id,scope_key)
    WHERE scope_key IS NOT NULL;

CREATE VIEW babylon_state.labor_node_descriptor_v1 AS
SELECT d.campaign_id,d.descriptor_key,d.descriptor_sha256,d.kind,
       CASE WHEN d.kind IN ('site_stock','household_stock','work','household_work') THEN coalesce(a.account_id,(d.physical_scope).scope_id)
            WHEN d.kind IN ('process','maintenance') THEN d.process_id ELSE d.entity_id END AS entity_id,
       g.good_id,g.unit_id,d.purpose,coalesce(a.account_kind,(d.physical_scope).scope_kind) AS scope_kind,
       coalesce(a.account_id,(d.physical_scope).scope_id) AS scope_id,d.process_id,d.route_id,d.origin_id,d.destination_id,
       d.location_key,
       coalesce(a.catchment_key,(d.physical_scope).catchment_key) AS catchment_key,
       coalesce(a.industry_key,(d.physical_scope).industry_key) AS industry_key,
       coalesce(a.industry_label,(d.physical_scope).industry_label) AS industry_label,
       coalesce(l.longitude,(d.physical_scope).longitude) AS longitude,coalesce(l.latitude,(d.physical_scope).latitude) AS latitude
FROM babylon_state.labor_node_identity_v1 d
LEFT JOIN babylon_state.economic_flow_account_v1 a ON (a.campaign_id,a.account_key)=(d.campaign_id,d.scope_key)
LEFT JOIN babylon_state.economic_flow_location_v1 l ON (l.campaign_id,l.location_key,l.labor_point_revision)=(d.campaign_id,d.location_key,d.point_revision)
LEFT JOIN babylon_state.labor_product_v1 g ON (g.campaign_id,g.product_key)=(d.campaign_id,d.product_key);
CREATE FUNCTION babylon_state.labor_node_fingerprint_v1(n babylon_state.labor_node_descriptor_v1)
RETURNS bytea LANGUAGE sql STABLE STRICT SET search_path TO pg_catalog AS $$
    SELECT sha256(record_send(ROW(
        ($1).kind, ($1).entity_id, ($1).good_id, ($1).unit_id, ($1).purpose, ($1).scope_kind, ($1).scope_id,
        ($1).process_id, ($1).route_id, ($1).origin_id, ($1).destination_id, ($1).location_key, ($1).catchment_key,
        ($1).industry_key, ($1).industry_label, ($1).longitude, ($1).latitude
    )))
$$;
CREATE FUNCTION babylon_state.check_labor_descriptors_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
BEGIN
    IF EXISTS (
        SELECT FROM staged s JOIN babylon_state.labor_node_descriptor_v1 d USING(campaign_id,descriptor_key)
        LEFT JOIN babylon_state.economic_flow_account_v1 a ON (a.campaign_id,a.account_key)=(s.campaign_id,s.scope_key)
        WHERE s.descriptor_sha256<>babylon_state.labor_node_fingerprint_v1(d)
           OR s.location_key IS DISTINCT FROM coalesce(a.location_key,(s.physical_scope).location_key)
           OR (d.scope_kind IS NOT NULL AND d.scope_kind NOT IN ('site_cash','household_cash'))
           OR ((d.kind IN ('site_stock','household_stock','commercial_freight','aid_freight','equipment','installation'))<>(d.good_id IS NOT NULL))
    ) THEN
        RAISE EXCEPTION 'labor descriptor differs from its complete typed content' USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END $$;
CREATE TRIGGER labor_descriptor_insert AFTER INSERT ON babylon_state.labor_node_identity_v1
    REFERENCING NEW TABLE AS staged FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.check_labor_descriptors_v1();
CREATE TRIGGER retain_labor_descriptor BEFORE UPDATE ON babylon_state.labor_node_identity_v1
    FOR EACH ROW EXECUTE FUNCTION babylon_state.retain_labor_identity_v1();
REVOKE ALL ON FUNCTION babylon_state.labor_node_fingerprint_v1(babylon_state.labor_node_descriptor_v1),babylon_state.check_labor_descriptors_v1() FROM PUBLIC;
REVOKE ALL ON babylon_state.labor_node_descriptor_v1,babylon_state.labor_product_v1 FROM PUBLIC;
-- Source ordinals start at zero and are local to one close. A missing side has
-- three NULL cells; recorded zero hours and unknown prehistory are independent.
CREATE FUNCTION babylon_state.labor_holding_block_valid_v1(quantities numeric[], hours numeric[], unknowns boolean[], width integer)
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT SET search_path TO pg_catalog AS $$
    SELECT array_ndims(quantities)=1 AND array_lower(quantities,1)=1 AND cardinality(quantities)=width
       AND array_ndims(hours)=1 AND array_lower(hours,1)=1 AND cardinality(hours)=width
       AND array_ndims(unknowns)=1 AND array_lower(unknowns,1)=1 AND cardinality(unknowns)=width
       AND NOT EXISTS (SELECT FROM unnest(quantities,hours,unknowns) s(q,h,u)
                       WHERE num_nonnulls(q,h,u) NOT IN (0,3)
                          OR scale(q)<>0 OR q NOT BETWEEN 1 AND 18446744073709551615
                          OR scale(h)<>0 OR h NOT BETWEEN 0 AND 340282366920938463463374607431768211455)
$$;
REVOKE ALL ON FUNCTION babylon_state.labor_holding_block_valid_v1(numeric[],numeric[],boolean[],integer) FROM PUBLIC;
CREATE TABLE babylon_state.labor_node_block_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL,
    block_ordinal bigint NOT NULL CHECK(block_ordinal BETWEEN 0 AND 36028797018963967),
    descriptor_keys bigint[] NOT NULL CHECK(array_ndims(descriptor_keys)=1 AND array_lower(descriptor_keys,1)=1
        AND cardinality(descriptor_keys) BETWEEN 1 AND 256 AND array_position(descriptor_keys,NULL) IS NULL
        AND 0<ALL(descriptor_keys)),
    last_ordinal bigint GENERATED ALWAYS AS (block_ordinal*256+(cardinality(descriptor_keys)-1)) STORED,
    opening_quantity numeric[] NOT NULL, opening_recorded_micro_hours numeric[] NOT NULL, opening_unknown_opening boolean[] NOT NULL,
    closing_quantity numeric[] NOT NULL, closing_recorded_micro_hours numeric[] NOT NULL, closing_unknown_opening boolean[] NOT NULL,
    CHECK(babylon_state.labor_holding_block_valid_v1(opening_quantity,opening_recorded_micro_hours,opening_unknown_opening,cardinality(descriptor_keys))),
    CHECK(babylon_state.labor_holding_block_valid_v1(closing_quantity,closing_recorded_micro_hours,closing_unknown_opening,cardinality(descriptor_keys))),
    PRIMARY KEY(campaign_id,resolve_tick,block_ordinal),
    UNIQUE(campaign_id,resolve_tick,block_ordinal,last_ordinal),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.labor_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX labor_node_block_descriptors_v1 ON babylon_state.labor_node_block_v1 USING gin(descriptor_keys) WITH (fastupdate=off);
CREATE VIEW babylon_state.labor_node_v1 AS
SELECT b.campaign_id,b.resolve_tick,b.block_ordinal*256+(s.ordinal-1) AS node_ordinal,
       s.descriptor_key,s.opening_quantity,s.opening_recorded_micro_hours,s.opening_unknown_opening,
       s.closing_quantity,s.closing_recorded_micro_hours,s.closing_unknown_opening
FROM babylon_state.labor_node_block_v1 b CROSS JOIN LATERAL unnest(
    b.descriptor_keys,b.opening_quantity,b.opening_recorded_micro_hours,b.opening_unknown_opening,
    b.closing_quantity,b.closing_recorded_micro_hours,b.closing_unknown_opening
) WITH ORDINALITY s(descriptor_key,opening_quantity,opening_recorded_micro_hours,opening_unknown_opening,
                    closing_quantity,closing_recorded_micro_hours,closing_unknown_opening,ordinal);
REVOKE ALL ON babylon_state.labor_node_block_v1,babylon_state.labor_node_v1 FROM PUBLIC;
-- Owner-side projection also supports exact verification while the marker is staged.
CREATE VIEW babylon_state.labor_node_fact_v1 AS
SELECT n.campaign_id,n.resolve_tick,n.node_ordinal,
       d.kind, d.entity_id, d.good_id, d.unit_id, d.purpose, d.scope_kind, d.scope_id,
       d.process_id, d.route_id, d.origin_id, d.destination_id, d.location_key, d.catchment_key,
       d.industry_key, d.industry_label, d.longitude, d.latitude,
       n.opening_quantity, n.opening_recorded_micro_hours, n.opening_unknown_opening,
       n.closing_quantity, n.closing_recorded_micro_hours, n.closing_unknown_opening
FROM babylon_state.labor_node_v1 n JOIN babylon_state.labor_node_descriptor_v1 d USING(campaign_id,descriptor_key);
REVOKE ALL ON babylon_state.labor_node_identity_v1,babylon_state.labor_node_fact_v1 FROM PUBLIC;
CREATE TABLE babylon_state.labor_movement_block_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL,
    block_ordinal bigint NOT NULL CHECK (block_ordinal BETWEEN 0 AND 72057594037927935),
    slots smallint[] NOT NULL CHECK (babylon_state.movement_slots_v1(slots)),
    source_node bigint[] NOT NULL,
    destination_node bigint[] NOT NULL,
    receipt_family text[] NOT NULL,
    receipt_ordinal bigint[] NOT NULL,
    quantity numeric[] NOT NULL,
    recorded_micro_hours numeric[] NOT NULL,
    unknown_opening boolean[] NOT NULL,
    CHECK (array_dims(source_node) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(destination_node) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(receipt_family) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(receipt_ordinal) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(quantity) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(recorded_micro_hours) IS NOT DISTINCT FROM array_dims(slots)
        AND array_dims(unknown_opening) IS NOT DISTINCT FROM array_dims(slots)),
    PRIMARY KEY(campaign_id,resolve_tick,block_ordinal),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.labor_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE FUNCTION babylon_state.labor_movement_values_v1(a_source_node bigint[], a_destination_node bigint[], a_receipt_family text[], a_receipt_ordinal bigint[], a_quantity numeric[], a_recorded_micro_hours numeric[], a_unknown_opening boolean[])
RETURNS boolean LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path = pg_catalog AS $$
    SELECT NOT EXISTS (
        SELECT FROM unnest(a_source_node, a_destination_node, a_receipt_family, a_receipt_ordinal, a_quantity, a_recorded_micro_hours, a_unknown_opening)
            AS r(source_node, destination_node, receipt_family, receipt_ordinal, quantity, recorded_micro_hours, unknown_opening)
        WHERE (r.source_node>=0 AND r.destination_node>=0 AND r.receipt_ordinal>=0
            AND r.receipt_family IN ('production','maintenance','installation','equipment_wear','handling',
                'aid','dispatches','arrivals','losses','local_fulfillments','local_transfers','service_outputs',
                'service_performance','household_consumption','household_services','household_time',
                'member_labor_use','agency_paid','collections')
            AND scale(r.quantity)=0 AND r.quantity BETWEEN 1 AND 18446744073709551615
            AND scale(r.recorded_micro_hours)=0
            AND r.recorded_micro_hours BETWEEN 0 AND 340282366920938463463374607431768211455
            AND r.unknown_opening IS NOT NULL) IS NOT TRUE
    )
$$;
ALTER TABLE babylon_state.labor_movement_block_v1 ADD CHECK (babylon_state.labor_movement_values_v1(source_node,destination_node,receipt_family,receipt_ordinal,quantity,recorded_micro_hours,unknown_opening));
CREATE VIEW babylon_state.labor_movement_v1 AS
SELECT b.campaign_id,b.resolve_tick,b.block_ordinal*128+r.slot AS ordinal,
       r.source_node,r.destination_node,r.receipt_family,r.receipt_ordinal,r.quantity,r.recorded_micro_hours,r.unknown_opening
FROM babylon_state.labor_movement_block_v1 b
CROSS JOIN LATERAL unnest(b.slots,b.source_node,b.destination_node,b.receipt_family,b.receipt_ordinal,b.quantity,b.recorded_micro_hours,b.unknown_opening)
    AS r(slot,source_node,destination_node,receipt_family,receipt_ordinal,quantity,recorded_micro_hours,unknown_opening);
REVOKE ALL ON babylon_state.labor_movement_block_v1,babylon_state.labor_movement_v1 FROM PUBLIC;
REVOKE ALL ON FUNCTION babylon_state.labor_movement_values_v1(bigint[],bigint[],text[],bigint[],numeric[],numeric[],boolean[]) FROM PUBLIC;
-- The only variable-width roster block is the last. Binding its actual end
-- also prevents a concurrent parent shrink from invalidating retained movements.
CREATE TABLE babylon_state.labor_movement_roster_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL, block_ordinal bigint NOT NULL, last_ordinal bigint NOT NULL,
    PRIMARY KEY(campaign_id,resolve_tick,block_ordinal),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.labor_period_v1
        ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(campaign_id,resolve_tick,block_ordinal,last_ordinal)
        REFERENCES babylon_state.labor_node_block_v1(campaign_id,resolve_tick,block_ordinal,last_ordinal)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE FUNCTION babylon_state.labor_movement_nodes_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE
    needed integer;
    admitted integer;
BEGIN
    PERFORM babylon_state.economic_reference_lock_v1(NEW.campaign_id);
    INSERT INTO babylon_state.labor_movement_roster_v1
    SELECT NEW.campaign_id,NEW.resolve_tick,n.block_ordinal,n.last_ordinal
    FROM (SELECT DISTINCT k/256 AS block_ordinal
          FROM unnest(NEW.source_node||NEW.destination_node) AS e(k)) AS required
    JOIN babylon_state.labor_node_block_v1 n USING(block_ordinal)
    WHERE n.campaign_id=NEW.campaign_id AND n.resolve_tick=NEW.resolve_tick
    ORDER BY n.block_ordinal ON CONFLICT DO NOTHING;
    WITH required AS MATERIALIZED (
        SELECT k/256 AS block_ordinal,min(k) AS first_used,max(k) AS last_used
        FROM unnest(NEW.source_node||NEW.destination_node) AS e(k) GROUP BY k/256
    ), locked AS MATERIALIZED (
        SELECT a.block_ordinal FROM required r JOIN babylon_state.labor_movement_roster_v1 a USING(block_ordinal)
        WHERE (a.campaign_id,a.resolve_tick)=(NEW.campaign_id,NEW.resolve_tick)
          AND r.first_used>=0 AND r.last_used<=a.last_ordinal
        ORDER BY a.block_ordinal FOR KEY SHARE OF a
    )
    SELECT (SELECT count(*) FROM required),(SELECT count(*) FROM locked) INTO needed,admitted;
    IF needed<>admitted THEN
        RAISE foreign_key_violation USING MESSAGE='unresolved labor movement node';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER labor_movement_nodes_v1
BEFORE INSERT OR UPDATE OF campaign_id,resolve_tick,source_node,destination_node ON babylon_state.labor_movement_block_v1
FOR EACH ROW EXECUTE FUNCTION babylon_state.labor_movement_nodes_v1();
CREATE FUNCTION babylon_state.labor_movement_reference_change_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF TG_OP='TRUNCATE' THEN
        RAISE foreign_key_violation USING MESSAGE='retire movement references with scoped DELETE';
    END IF;
    IF TG_OP='UPDATE' THEN
        RAISE foreign_key_violation USING MESSAGE='movement endpoint reference is immutable';
    END IF;
    PERFORM babylon_state.economic_reference_lock_v1(q.campaign_id)
    FROM (SELECT DISTINCT campaign_id FROM retired ORDER BY campaign_id) AS q;
    IF EXISTS (SELECT FROM retired o JOIN babylon_state.labor_movement_block_v1 b USING(campaign_id,resolve_tick)
               WHERE EXISTS (SELECT FROM unnest(b.source_node||b.destination_node) AS e(k) WHERE k/256=o.block_ordinal)) THEN
        RAISE foreign_key_violation USING MESSAGE='retained movement still uses the endpoint';
    END IF;
    RETURN NULL;
END $$;
CREATE TRIGGER labor_movement_reference_update_v1 BEFORE UPDATE ON babylon_state.labor_movement_roster_v1
FOR EACH ROW EXECUTE FUNCTION babylon_state.labor_movement_reference_change_v1();
CREATE TRIGGER labor_movement_reference_delete_v1 AFTER DELETE ON babylon_state.labor_movement_roster_v1
REFERENCING OLD TABLE AS retired FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_movement_reference_change_v1();
CREATE TRIGGER labor_movement_reference_truncate_v1 BEFORE TRUNCATE ON babylon_state.labor_movement_roster_v1
FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_movement_reference_change_v1();
REVOKE ALL ON babylon_state.labor_movement_roster_v1 FROM PUBLIC;
REVOKE ALL ON FUNCTION babylon_state.labor_movement_nodes_v1(), babylon_state.labor_movement_reference_change_v1() FROM PUBLIC;
REVOKE ALL ON babylon_state.labor_period_v1,babylon_state.labor_checkpoint_v1,babylon_state.labor_node_v1,babylon_state.labor_movement_v1 FROM PUBLIC;

-- The logical references in arrays have no scalar FK operator. All mutations
-- affecting membership serialize on a real write per campaign and transaction.
-- This also makes a concurrent stale REPEATABLE READ writer fail serialization.
-- Several block statements normally produce just one deferred period check.
CREATE TABLE babylon_state.economic_reference_guard_v1 (
    campaign_id uuid PRIMARY KEY REFERENCES babylon_state.material_campaign_foundation_v3(campaign_id),
    transaction_id xid8 NOT NULL,
    check_periods bigint[] NOT NULL,
    check_all_descriptors boolean NOT NULL
);
REVOKE ALL ON babylon_state.economic_reference_guard_v1 FROM PUBLIC;

-- A custom forward/reverse membership check must use this on both sides.
-- A row lock alone does not invalidate an already established transaction snapshot.
CREATE FUNCTION babylon_state.economic_reference_lock_v1(c uuid) RETURNS void
LANGUAGE sql VOLATILE STRICT SET search_path TO pg_catalog AS $$
    INSERT INTO babylon_state.economic_reference_guard_v1 AS g
        VALUES(c,pg_current_xact_id(),ARRAY[]::bigint[],false)
    ON CONFLICT(campaign_id) DO UPDATE SET transaction_id=EXCLUDED.transaction_id,
        check_periods=EXCLUDED.check_periods,check_all_descriptors=false
    WHERE g.transaction_id<>EXCLUDED.transaction_id
$$;
REVOKE ALL ON FUNCTION babylon_state.economic_reference_lock_v1(uuid) FROM PUBLIC;

CREATE FUNCTION babylon_state.labor_node_changed_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
DECLARE sources text;
BEGIN
    -- Each event receives actual PostgreSQL transition relations. An UPDATE
    -- includes both old and new scopes so moving a block never hides the donor.
    sources := CASE TG_OP WHEN 'INSERT' THEN 'SELECT * FROM inserted'
                          WHEN 'DELETE' THEN 'SELECT * FROM removed'
                          ELSE 'SELECT * FROM removed UNION ALL SELECT * FROM inserted' END;
    IF TG_TABLE_NAME='labor_node_identity_v1' THEN
        -- Inserting a descriptor cannot orphan a reference. A delete or key
        -- replacement checks the retained dictionary once for this campaign.
        sources := 'SELECT DISTINCT campaign_id,NULL::bigint AS tick,true AS check_all FROM ('||sources||') s';
    ELSE
        sources := 'SELECT DISTINCT campaign_id,resolve_tick AS tick,false AS check_all FROM ('||sources||') s';
    END IF;
    EXECUTE 'INSERT INTO babylon_state.economic_reference_guard_v1 AS g
        SELECT campaign_id,pg_current_xact_id(),
               coalesce(array_agg(tick ORDER BY tick) FILTER(WHERE tick IS NOT NULL),ARRAY[]::bigint[]),
               bool_or(check_all)
        FROM ('||sources||') s GROUP BY campaign_id ORDER BY campaign_id
        ON CONFLICT(campaign_id) DO UPDATE SET
           transaction_id=EXCLUDED.transaction_id,
           check_periods=CASE WHEN g.transaction_id=EXCLUDED.transaction_id THEN
               ARRAY(SELECT DISTINCT unnest(g.check_periods||EXCLUDED.check_periods) ORDER BY 1)
               ELSE EXCLUDED.check_periods END,
           check_all_descriptors=EXCLUDED.check_all_descriptors OR
               (g.transaction_id=EXCLUDED.transaction_id AND g.check_all_descriptors)
        WHERE g.transaction_id<>EXCLUDED.transaction_id OR NOT EXCLUDED.check_periods <@ g.check_periods OR
              (EXCLUDED.check_all_descriptors AND NOT g.check_all_descriptors)';
    RETURN NULL;
END $$;

CREATE FUNCTION babylon_state.labor_node_validate_v1() RETURNS trigger
LANGUAGE plpgsql SET search_path TO pg_catalog AS $$
BEGIN
    IF cardinality(NEW.check_periods)=0 AND NOT NEW.check_all_descriptors THEN RETURN NULL; END IF;
    -- Earlier events were superseded by a larger set of scopes in this transaction.
    IF EXISTS (SELECT FROM babylon_state.economic_reference_guard_v1 g
               WHERE g.campaign_id=NEW.campaign_id AND (g.check_periods,g.check_all_descriptors)
                    IS DISTINCT FROM (NEW.check_periods,NEW.check_all_descriptors)) THEN
        RETURN NULL;
    END IF;
    IF EXISTS (
        SELECT FROM babylon_state.labor_period_v1 l
        JOIN babylon_state.money_journal_period_v1 m USING(campaign_id,resolve_tick)
        CROSS JOIN LATERAL (
            SELECT coalesce(sum(cardinality(b.descriptor_keys)),0) AS n,max(b.last_ordinal) AS last_ordinal
            FROM babylon_state.labor_node_block_v1 b
            WHERE (b.campaign_id,b.resolve_tick)=(l.campaign_id,l.resolve_tick)
        ) a
        WHERE l.campaign_id=NEW.campaign_id AND l.resolve_tick=ANY(NEW.check_periods)
          AND (a.n<>CASE WHEN m.detail_retained THEN l.node_count ELSE 0 END
               OR a.last_ordinal>=a.n)
    ) THEN RAISE EXCEPTION 'incomplete retained labor node ordinals' USING ERRCODE='23503'; END IF;
    IF EXISTS (
        SELECT unnest(b.descriptor_keys) FROM babylon_state.labor_node_block_v1 b
        WHERE b.campaign_id=NEW.campaign_id AND (NEW.check_all_descriptors OR b.resolve_tick=ANY(NEW.check_periods))
        EXCEPT SELECT d.descriptor_key FROM babylon_state.labor_node_identity_v1 d WHERE d.campaign_id=NEW.campaign_id
    ) THEN RAISE EXCEPTION 'unknown labor descriptor in scoped node block' USING ERRCODE='23503'; END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER labor_node_validate_v1 AFTER INSERT OR UPDATE ON babylon_state.economic_reference_guard_v1
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION babylon_state.labor_node_validate_v1();

CREATE FUNCTION babylon_state.labor_node_no_truncate_v1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'remove scoped labor facts through the period owner' USING ERRCODE='23503'; END $$;
REVOKE ALL ON FUNCTION babylon_state.labor_node_changed_v1(),babylon_state.labor_node_validate_v1(),
    babylon_state.labor_node_no_truncate_v1() FROM PUBLIC;
CREATE TRIGGER labor_node_block_v1_insert_refs AFTER INSERT ON babylon_state.labor_node_block_v1
REFERENCING NEW TABLE AS inserted FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER labor_node_block_v1_update_refs AFTER UPDATE ON babylon_state.labor_node_block_v1
REFERENCING OLD TABLE AS removed NEW TABLE AS inserted FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER labor_node_block_v1_delete_refs AFTER DELETE ON babylon_state.labor_node_block_v1
REFERENCING OLD TABLE AS removed FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER labor_node_identity_v1_update_refs AFTER UPDATE ON babylon_state.labor_node_identity_v1
REFERENCING OLD TABLE AS removed NEW TABLE AS inserted FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER labor_node_identity_v1_delete_refs AFTER DELETE ON babylon_state.labor_node_identity_v1
REFERENCING OLD TABLE AS removed FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER labor_period_v1_insert_refs AFTER INSERT ON babylon_state.labor_period_v1
REFERENCING NEW TABLE AS inserted FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER labor_period_v1_update_refs AFTER UPDATE ON babylon_state.labor_period_v1
REFERENCING OLD TABLE AS removed NEW TABLE AS inserted FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER money_journal_period_v1_update_refs AFTER UPDATE ON babylon_state.money_journal_period_v1
REFERENCING OLD TABLE AS removed NEW TABLE AS inserted FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER money_journal_period_v1_insert_refs AFTER INSERT ON babylon_state.money_journal_period_v1
REFERENCING NEW TABLE AS inserted FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_changed_v1();
CREATE TRIGGER labor_node_block_v1_no_truncate BEFORE TRUNCATE ON babylon_state.labor_node_block_v1
FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_no_truncate_v1();
CREATE TRIGGER labor_node_identity_v1_no_truncate BEFORE TRUNCATE ON babylon_state.labor_node_identity_v1
FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_no_truncate_v1();
CREATE TRIGGER economic_reference_guard_v1_no_truncate BEFORE TRUNCATE ON babylon_state.economic_reference_guard_v1
FOR EACH STATEMENT EXECUTE FUNCTION babylon_state.labor_node_no_truncate_v1();

CREATE FUNCTION babylon_state.labor_node_guard_private_v1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='DELETE' OR pg_catalog.pg_trigger_depth()<2 THEN
        RAISE EXCEPTION 'labor node validation scope is internally maintained' USING ERRCODE='23503';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER labor_node_guard_private_v1 BEFORE INSERT OR UPDATE OR DELETE ON babylon_state.economic_reference_guard_v1
FOR EACH ROW EXECUTE FUNCTION babylon_state.labor_node_guard_private_v1();
REVOKE ALL ON FUNCTION babylon_state.labor_node_guard_private_v1() FROM PUBLIC;

-- Retained company legal and consolidated books, authenticated by the completed journal marker.
CREATE TABLE babylon_state.company_accounting_period_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>0),
    fact_sha256 bytea NOT NULL CHECK(octet_length(fact_sha256)=32),
    checkpoint_sha256 bytea NOT NULL CHECK(octet_length(checkpoint_sha256)=32),
    result_world_hash bytea NOT NULL CHECK(octet_length(result_world_hash)=32),
    company_count bigint NOT NULL CHECK(company_count>0),
    entry_count bigint NOT NULL CHECK(entry_count>=0),
    PRIMARY KEY(campaign_id,resolve_tick),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.money_journal_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.company_accounting_checkpoint_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>0),
    checkpoint_bytes bytea NOT NULL,
    PRIMARY KEY(campaign_id,resolve_tick),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.company_accounting_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.company_statement_balance_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>0),
    company_id bytea NOT NULL CHECK(octet_length(company_id)=32),
    scope text NOT NULL CHECK(scope IN ('parent','subsidiaries','consolidated')),
    boundary text NOT NULL CHECK(boundary IN ('opening','closing')),
    cash_micros numeric(39,0) NOT NULL,
    reserves_micros numeric(39,0) NOT NULL,
    receivables_micros numeric(39,0) NOT NULL,
    inventory_micros numeric(39,0) NOT NULL,
    freight_micros numeric(39,0) NOT NULL,
    equipment_micros numeric(39,0) NOT NULL,
    investments_micros numeric(39,0) NOT NULL,
    assets_micros numeric(39,0) NOT NULL,
    liabilities_micros numeric(39,0) NOT NULL,
    equity_micros numeric(39,0) NOT NULL,
    retained_earnings_micros numeric(39,0) NOT NULL,
    CHECK(assets_micros=liabilities_micros+equity_micros),
    PRIMARY KEY(campaign_id,resolve_tick,company_id,scope,boundary),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.company_accounting_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.company_statement_income_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>0),
    company_id bytea NOT NULL CHECK(octet_length(company_id)=32),
    scope text NOT NULL CHECK(scope IN ('parent','subsidiaries','consolidated')),
    sales_micros numeric(39,0) NOT NULL,
    cost_of_goods_sold_micros numeric(39,0) NOT NULL,
    operating_expenses_micros numeric(39,0) NOT NULL,
    taxes_micros numeric(39,0) NOT NULL,
    other_income_micros numeric(39,0) NOT NULL,
    other_expenses_micros numeric(39,0) NOT NULL,
    profit_micros numeric(39,0) NOT NULL,
    distributions_micros numeric(39,0) NOT NULL,
    contributions_micros numeric(39,0) NOT NULL,
    CHECK(profit_micros=sales_micros-cost_of_goods_sold_micros-operating_expenses_micros-taxes_micros+other_income_micros-other_expenses_micros),
    PRIMARY KEY(campaign_id,resolve_tick,company_id,scope),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.company_accounting_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.company_statement_cash_flow_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>0),
    company_id bytea NOT NULL CHECK(octet_length(company_id)=32),
    scope text NOT NULL CHECK(scope IN ('parent','subsidiaries','consolidated')),
    operating_micros numeric(39,0) NOT NULL,
    investing_micros numeric(39,0) NOT NULL,
    financing_micros numeric(39,0) NOT NULL,
    reserve_reclassification_micros numeric(39,0) NOT NULL,
    PRIMARY KEY(campaign_id,resolve_tick,company_id,scope),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.company_accounting_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.company_elimination_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>0),
    company_id bytea NOT NULL CHECK(octet_length(company_id)=32),
    opening_investments_micros numeric(39,0) NOT NULL,
    closing_investments_micros numeric(39,0) NOT NULL,
    opening_intercompany_claims_micros numeric(39,0) NOT NULL,
    closing_intercompany_claims_micros numeric(39,0) NOT NULL,
    distributions_micros numeric(39,0) NOT NULL,
    contributions_micros numeric(39,0) NOT NULL,
    sales_micros numeric(39,0) NOT NULL,
    seller_cost_micros numeric(39,0) NOT NULL,
    margin_created_micros numeric(39,0) NOT NULL,
    margin_realized_micros numeric(39,0) NOT NULL,
    opening_unrealized_margin_micros numeric(39,0) NOT NULL,
    closing_unrealized_margin_micros numeric(39,0) NOT NULL,
    CHECK(closing_unrealized_margin_micros=opening_unrealized_margin_micros+margin_created_micros-margin_realized_micros),
    CHECK(closing_investments_micros=opening_investments_micros+contributions_micros),
    PRIMARY KEY(campaign_id,resolve_tick,company_id),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.company_accounting_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE babylon_state.company_realization_entry_v1 (
    campaign_id uuid NOT NULL, resolve_tick bigint NOT NULL CHECK(resolve_tick>0),
    company_id bytea NOT NULL CHECK(octet_length(company_id)=32),
    family smallint NOT NULL CHECK(family IN(26,27,38,39)), ordinal bigint NOT NULL CHECK(ordinal>=0),
    kind text NOT NULL CHECK(kind IN ('internal_sale','external_sale','expense','contribution','dividend')),
    from_kind text NOT NULL, from_id bytea NOT NULL CHECK(octet_length(from_id)=32),
    to_kind text, to_id bytea CHECK(octet_length(to_id)=32),
    CHECK((to_kind IS NULL)=(to_id IS NULL)),
    amount_micros numeric(39,0) NOT NULL,
    legal_cost_micros numeric(39,0) NOT NULL,
    group_cost_micros numeric(39,0) NOT NULL,
    margin_created_micros numeric(39,0) NOT NULL,
    margin_realized_micros numeric(39,0) NOT NULL,
    PRIMARY KEY(campaign_id,resolve_tick,company_id,family,ordinal),
    FOREIGN KEY(campaign_id,resolve_tick) REFERENCES babylon_state.company_accounting_period_v1 ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);
REVOKE ALL ON babylon_state.company_accounting_period_v1,
    babylon_state.company_accounting_checkpoint_v1,
    babylon_state.company_statement_balance_v1,
    babylon_state.company_statement_income_v1,
    babylon_state.company_statement_cash_flow_v1,
    babylon_state.company_elimination_v1,
    babylon_state.company_realization_entry_v1 FROM PUBLIC;
