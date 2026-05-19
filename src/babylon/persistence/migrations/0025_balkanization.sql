-- 0025_balkanization.sql
-- Spec-070 Sovereign Topology + Faction Influence + Balkanization.
-- Owner subsystem: balkanization (per Constitution II.11).
-- Only the FactionInfluenceSystem, SovereigntySystem, and
-- CollapseTransitionSystem may write to these tables; cross-subsystem
-- reads MUST go through GraphProtocol (never direct SQL).
--
-- Tables introduced:
--   1. runtime_political_factions          - BalkanizationFaction nodes
--   2. runtime_sovereigns                   - Sovereign nodes
--   3. runtime_claims_edges                 - Sovereign → Territory CLAIMS
--   4. runtime_influences_edges             - Faction → Territory INFLUENCES
--   5. runtime_administers_edges            - Sovereign → Sovereign hierarchy
--   6. balkanization_claims_audit           - FR-046 append-only audit log
--   7. balkanization_influences_audit       - FR-046 append-only audit log
--
-- Note: per FR-045, this is the spec-070 BalkanizationFaction (renamed
-- from spec.md's "PoliticalFaction" to disambiguate from spec-031's
-- existing PoliticalFaction Organization subclass). The table name
-- retains "political_factions" plural for legibility on the SQL side
-- — the Python entity is BalkanizationFaction.

CREATE TABLE IF NOT EXISTS runtime_political_factions (
    session_id        UUID NOT NULL,
    faction_id        TEXT NOT NULL CHECK (faction_id ~ '^FAC_[A-Z][A-Z0-9_]*$'),
    name              TEXT NOT NULL,
    ideology          TEXT NOT NULL,
    colonial_stance   TEXT NOT NULL CHECK (colonial_stance IN (
                          'uphold', 'ignore', 'abolish'
                      )),
    is_settler_formation  BOOLEAN NOT NULL,
    extraction_modifier   DOUBLE PRECISION NOT NULL CHECK (extraction_modifier >= 0),
    violence_modifier     DOUBLE PRECISION NOT NULL CHECK (violence_modifier >= 0),
    class_reduction       DOUBLE PRECISION NOT NULL CHECK (class_reduction BETWEEN 0 AND 1),
    metabolic_reduction   DOUBLE PRECISION NOT NULL CHECK (metabolic_reduction BETWEEN -1 AND 1),
    color_hex             TEXT NOT NULL CHECK (color_hex ~ '^#[0-9A-Fa-f]{6}$'),
    founded_tick          INTEGER NOT NULL CHECK (founded_tick >= 0),
    dissolved_tick        INTEGER CHECK (dissolved_tick IS NULL OR dissolved_tick >= founded_tick),

    PRIMARY KEY (session_id, faction_id)
);

COMMENT ON TABLE runtime_political_factions IS
    'spec-070 FR-005--FR-008 BalkanizationFaction nodes. Owner: '
    'balkanization subsystem (II.11). Disambiguated from spec-031 '
    'PoliticalFaction Organization subclass per FR-045.';

CREATE TABLE IF NOT EXISTS runtime_sovereigns (
    session_id        UUID NOT NULL,
    sovereign_id      TEXT NOT NULL CHECK (sovereign_id ~ '^SOV_[A-Z][A-Z0-9_]*$'),
    name              TEXT NOT NULL,
    sovereignty_type  TEXT NOT NULL CHECK (sovereignty_type IN (
                          'recognized_state', 'provisional', 'insurgent',
                          'occupation', 'secessionist', 'emergency'
                      )),
    legitimacy        DOUBLE PRECISION NOT NULL CHECK (legitimacy BETWEEN 0 AND 1),
    color_hex         TEXT NOT NULL CHECK (color_hex ~ '^#[0-9A-Fa-f]{6}$'),
    capital_territory_id  TEXT,
    -- ruling_faction_id may be NULL ONLY for SOV_EXTERIOR_NULL (FR-040b).
    ruling_faction_id     TEXT CHECK (ruling_faction_id IS NULL OR
                              ruling_faction_id ~ '^FAC_[A-Z][A-Z0-9_]*$'),
    extraction_policy     TEXT NOT NULL CHECK (extraction_policy IN (
                              'intensify', 'continue', 'cease'
                          )),
    founded_tick          INTEGER NOT NULL CHECK (founded_tick >= 0),
    dissolved_tick        INTEGER CHECK (dissolved_tick IS NULL OR dissolved_tick >= founded_tick),

    -- FR-040b SOV_EXTERIOR_NULL invariant: NULL ruling_faction implies
    -- extraction_policy=CONTINUE.
    CONSTRAINT chk_null_ruling_implies_continue
        CHECK (
            ruling_faction_id IS NOT NULL
            OR extraction_policy = 'continue'
        ),

    PRIMARY KEY (session_id, sovereign_id)
);

COMMENT ON TABLE runtime_sovereigns IS
    'spec-070 FR-001--FR-004 Sovereign nodes. Owner: balkanization '
    'subsystem (II.11). FR-040b: SOV_EXTERIOR_NULL has '
    'ruling_faction_id=NULL paired with extraction_policy=CONTINUE.';

CREATE TABLE IF NOT EXISTS runtime_claims_edges (
    session_id        UUID NOT NULL,
    sovereign_id      TEXT NOT NULL,
    territory_id      TEXT NOT NULL,
    control_level     DOUBLE PRECISION NOT NULL CHECK (control_level BETWEEN 0 AND 1),
    fiscal_status     TEXT NOT NULL CHECK (fiscal_status IN (
                          'taxed', 'revolt', 'blockade', 'liberated', 'occupied'
                      )),
    legal_status      TEXT NOT NULL CHECK (legal_status IN (
                          'de_jure', 'de_facto', 'disputed', 'occupied', 'ceded'
                      )),
    recognition_level DOUBLE PRECISION NOT NULL DEFAULT 1.0
                          CHECK (recognition_level BETWEEN 0 AND 1),
    claimed_since_tick INTEGER NOT NULL CHECK (claimed_since_tick >= 0),

    -- FR-013: no self-claim.
    CONSTRAINT chk_no_self_claim CHECK (sovereign_id != territory_id),

    PRIMARY KEY (session_id, sovereign_id, territory_id)
);

CREATE INDEX IF NOT EXISTS ix_claims_session_territory
    ON runtime_claims_edges (session_id, territory_id, control_level DESC);

COMMENT ON TABLE runtime_claims_edges IS
    'spec-070 FR-009 Sovereign → Territory CLAIMS edges. Soft-cap sum '
    'of control_level per territory at 1.0; violations emit '
    'DUAL_POWER_ACTIVE rather than fail the tick (FR-035).';

CREATE TABLE IF NOT EXISTS runtime_influences_edges (
    session_id        UUID NOT NULL,
    faction_id        TEXT NOT NULL,
    territory_id      TEXT NOT NULL,
    influence_level   DOUBLE PRECISION NOT NULL CHECK (influence_level BETWEEN 0 AND 1),
    support_type      TEXT NOT NULL CHECK (support_type IN (
                          'material', 'ideological', 'military',
                          'electoral', 'labor'
                      )),
    cadre_count       INTEGER NOT NULL DEFAULT 0 CHECK (cadre_count >= 0),
    sympathizer_count BIGINT NOT NULL DEFAULT 0 CHECK (sympathizer_count >= 0),
    established_tick  INTEGER NOT NULL CHECK (established_tick >= 0),

    -- FR-017: no self-influence.
    CONSTRAINT chk_no_self_influence CHECK (faction_id != territory_id),

    PRIMARY KEY (session_id, faction_id, territory_id)
);

CREATE INDEX IF NOT EXISTS ix_influences_session_territory
    ON runtime_influences_edges (session_id, territory_id, influence_level DESC);

COMMENT ON TABLE runtime_influences_edges IS
    'spec-070 FR-014 Faction → Territory INFLUENCES edges. FR-016: '
    'sum of influence_level per territory is NOT capped at 1.0 '
    '(distinct from CLAIMS).';

CREATE TABLE IF NOT EXISTS runtime_administers_edges (
    session_id        UUID NOT NULL,
    upper_sovereign_id TEXT NOT NULL,
    lower_sovereign_id TEXT NOT NULL,
    delegation_scope  TEXT NOT NULL,
    granted_tick      INTEGER NOT NULL CHECK (granted_tick >= 0),

    CONSTRAINT chk_no_self_admin CHECK (upper_sovereign_id != lower_sovereign_id),

    PRIMARY KEY (session_id, upper_sovereign_id, lower_sovereign_id)
);

COMMENT ON TABLE runtime_administers_edges IS
    'spec-070 FR-018 Sovereign → Sovereign hierarchical edges. MUST '
    'form an acyclic DAG (application-layer constraint; not enforced '
    'in the database).';

-- ─────────────────────────────────────────────────────────────────────
-- Audit tables (FR-046 + R-005). Append-only.
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS balkanization_claims_audit (
    audit_id          BIGSERIAL PRIMARY KEY,
    session_id        UUID NOT NULL,
    tick              INTEGER NOT NULL CHECK (tick >= 0),
    sovereign_id      TEXT NOT NULL,
    territory_id      TEXT NOT NULL,
    operation         TEXT NOT NULL CHECK (operation IN ('CREATE', 'UPDATE', 'DELETE')),
    control_level     DOUBLE PRECISION NOT NULL CHECK (control_level BETWEEN 0 AND 1),
    fiscal_status     TEXT NOT NULL,
    legal_status      TEXT NOT NULL,
    recognition_level DOUBLE PRECISION NOT NULL DEFAULT 1.0
                          CHECK (recognition_level BETWEEN 0 AND 1),
    observer_mutation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_claims_audit_session_tick
    ON balkanization_claims_audit (session_id, tick);

REVOKE UPDATE, DELETE ON balkanization_claims_audit FROM PUBLIC;

COMMENT ON TABLE balkanization_claims_audit IS
    'spec-070 FR-046 CLAIMS-mutation audit log. Append-only. '
    'observer_mutation flag distinguishes OBSERVER-mode '
    'player verbs (FR-049) from in-simulation mutations.';

CREATE TABLE IF NOT EXISTS balkanization_influences_audit (
    audit_id          BIGSERIAL PRIMARY KEY,
    session_id        UUID NOT NULL,
    tick              INTEGER NOT NULL CHECK (tick >= 0),
    faction_id        TEXT NOT NULL,
    territory_id      TEXT NOT NULL,
    operation         TEXT NOT NULL CHECK (operation IN ('CREATE', 'UPDATE', 'DELETE')),
    influence_level   DOUBLE PRECISION NOT NULL CHECK (influence_level BETWEEN 0 AND 1),
    support_type      TEXT NOT NULL,
    cadre_count       INTEGER NOT NULL DEFAULT 0 CHECK (cadre_count >= 0),
    sympathizer_count BIGINT NOT NULL DEFAULT 0 CHECK (sympathizer_count >= 0),
    observer_mutation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_influences_audit_session_tick
    ON balkanization_influences_audit (session_id, tick);

REVOKE UPDATE, DELETE ON balkanization_influences_audit FROM PUBLIC;

COMMENT ON TABLE balkanization_influences_audit IS
    'spec-070 FR-046 INFLUENCES-mutation audit log. Append-only.';
