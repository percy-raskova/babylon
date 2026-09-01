//! Fog-safe semantic Archive page and knowledge contracts.

use std::collections::BTreeSet;

use babylon_kernel::sha256_of;
use minijinja::{context, Environment, UndefinedBehavior};
use postgres::types::FromSqlOwned;
use postgres::{Config, GenericClient, IsolationLevel, NoTls, Row};
use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};

use crate::identity::CampaignId;
use crate::migration_manifest::SCHEMA_ADVISORY_LOCK_KEY;

/// Exact additive schema used by the semantic Archive worker.
pub const SEMANTIC_ARCHIVE_SCHEMA_V1_SQL: &str =
    include_str!("../migrations/semantic_archive_v1.sql");
const ARCHIVE_PAGE_TEMPLATE_V1: &str = include_str!("archive_page_v1.md.j2");
const MAX_ID_BYTES: usize = 128;
const MAX_TEXT_BYTES: usize = 4_096;
const MAX_SIGNALS: usize = 256;
const MAX_LINKS: usize = 256;
const MAX_KNOWLEDGE_GRANTS: usize = 65_535;
const MAX_PAGE_BYTES: usize = 1_048_576;
const MAX_SEARCH_HITS: u32 = 100;
const ARCHIVE_SCHEMA_CONTRACT_ID: &str = "babylon.semantic-archive-schema.v1";
const ARCHIVE_WORKER_DOMAIN_V1: &[u8] = b"babylon.semantic-archive-worker.v1\0";
const ARCHIVE_DIRTY_BATCH_DOMAIN_V1: &[u8] = b"babylon.semantic-archive-dirty-batch.v1\0";
const ARCHIVE_SCHEMA_MARKERS_SQL_V1: &str = "SELECT \
    pg_catalog.to_regclass('babylon_meta.semantic_archive_schema_v1') IS NOT NULL, \
    pg_catalog.to_regclass('babylon_meta.archive_knowledge_grant_v1') IS NOT NULL, \
    pg_catalog.to_regclass('babylon_meta.archive_receipt_consumption_v1') IS NOT NULL, \
    pg_catalog.to_regclass('babylon_meta.archive_page_v1') IS NOT NULL";
const ARCHIVE_RECEIPT_SQL_V1: &str = "SELECT dirty.tick_content_hash \
    FROM babylon_state.archive_dirty_receipt_v1 AS dirty \
    JOIN babylon_state.tick_commit AS marker \
      ON marker.campaign_id = dirty.campaign_id \
     AND marker.resolve_tick = dirty.resolve_tick \
    WHERE dirty.campaign_id = $1::uuid AND dirty.resolve_tick = $2 \
    FOR SHARE OF dirty, marker";
/// SQL-only knowledge boundary used before any template receives values.
pub const ARCHIVE_KNOWLEDGE_SQL_V1: &str = "SELECT subject_kind, subject_id, grant_key \
    FROM babylon_meta.archive_knowledge_grant_v1 \
    WHERE campaign_id = $1::uuid AND granted_tick <= $2 \
    ORDER BY subject_kind, subject_id, grant_key LIMIT $3";
/// Known-page search with no join to material or raw event ledgers.
pub const ARCHIVE_SEARCH_SQL_V1: &str = "SELECT page.subject_kind, page.subject_id, page.title, \
    page.verified_tick, page.markdown, page.content_sha256, page.provenance_json \
    FROM babylon_meta.archive_page_v1 AS page \
    JOIN babylon_meta.archive_knowledge_grant_v1 AS knowledge \
      ON knowledge.campaign_id = page.campaign_id \
     AND knowledge.subject_kind = page.subject_kind \
     AND knowledge.subject_id = page.subject_id \
     AND knowledge.grant_key = 'subject' \
     AND knowledge.granted_tick <= page.verified_tick \
    WHERE page.campaign_id = $1::uuid \
      AND pg_catalog.strpos(pg_catalog.lower(page.search_text), pg_catalog.lower($2)) > 0 \
    ORDER BY page.subject_kind, page.subject_id LIMIT $3";

/// SHA-256 of the pinned strict `MiniJinja` page template.
pub const ARCHIVE_PAGE_TEMPLATE_SHA256_V1: [u8; 32] = [
    0xf5, 0x56, 0x15, 0x34, 0xe5, 0x39, 0x24, 0xac, 0x4f, 0x79, 0x70, 0xd9, 0xab, 0xfb, 0x19, 0xd0,
    0x32, 0xcf, 0x49, 0x1e, 0x6d, 0x04, 0xdc, 0x24, 0x63, 0xd3, 0xb3, 0xbf, 0x25, 0xc4, 0xb5, 0x39,
];

/// Closed semantic page kinds in the first Archive slice.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize)]
pub enum ArchiveSubjectKindV1 {
    /// United States county identified by five-digit Census FIPS.
    County,
    /// Census-designated place identified by seven-digit place GEOID.
    Place,
}

impl ArchiveSubjectKindV1 {
    /// Stable storage and page-path spelling.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::County => "county",
            Self::Place => "place",
        }
    }
}

/// Stable semantic Archive page identity.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize)]
pub struct ArchivePageRefV1 {
    kind: ArchiveSubjectKindV1,
    id: String,
}

impl ArchivePageRefV1 {
    /// Construct one exact county or place identity.
    ///
    /// # Errors
    /// Refuses the wrong digit width or an unbounded identity.
    pub fn try_new(kind: ArchiveSubjectKindV1, id: String) -> Result<Self, SemanticArchiveErrorV1> {
        let expected = match kind {
            ArchiveSubjectKindV1::County => 5,
            ArchiveSubjectKindV1::Place => 7,
        };
        if id.len() != expected
            || id.len() > MAX_ID_BYTES
            || !id.bytes().all(|byte| byte.is_ascii_digit())
        {
            return Err(SemanticArchiveErrorV1::InvalidIdentity);
        }
        Ok(Self { kind, id })
    }

    /// Return the closed subject kind.
    #[must_use]
    pub const fn kind(&self) -> ArchiveSubjectKindV1 {
        self.kind
    }

    /// Borrow the exact external identity.
    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }

    fn page_key(&self) -> String {
        format!("{}/{}", self.kind.as_str(), self.id)
    }
}

/// Known page identity and safe player-facing title.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveSubjectV1 {
    page_ref: ArchivePageRefV1,
    title: String,
}

impl ArchiveSubjectV1 {
    /// Construct one page subject.
    ///
    /// # Errors
    /// Refuses an invalid identity or unsafe title.
    pub fn try_new(
        kind: ArchiveSubjectKindV1,
        id: String,
        title: String,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        validate_text(&title)?;
        Ok(Self {
            page_ref: ArchivePageRefV1::try_new(kind, id)?,
            title,
        })
    }

    /// Borrow the stable page reference.
    #[must_use]
    pub const fn page_ref(&self) -> &ArchivePageRefV1 {
        &self.page_ref
    }

    /// Borrow the safe known title.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }
}

/// One player-visible source locator.
#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
pub struct ArchiveCitationV1 {
    source_id: String,
    locator: String,
}

impl ArchiveCitationV1 {
    /// Construct a bounded source citation.
    ///
    /// # Errors
    /// Refuses an empty, NUL-containing, or unbounded component.
    pub fn try_new(source_id: String, locator: String) -> Result<Self, SemanticArchiveErrorV1> {
        validate_text(&source_id)?;
        validate_text(&locator)?;
        Ok(Self { source_id, locator })
    }

    /// Borrow the stable source identity.
    #[must_use]
    pub fn source_id(&self) -> &str {
        &self.source_id
    }

    /// Borrow the precise source locator.
    #[must_use]
    pub fn locator(&self) -> &str {
        &self.locator
    }
}

/// One knowledge-grant-addressable semantic signal.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveSignalV1 {
    grant_key: String,
    label: String,
    value: String,
    citation: ArchiveCitationV1,
}

impl ArchiveSignalV1 {
    /// Construct one bounded signal.
    ///
    /// # Errors
    /// Refuses an unsafe grant key, label, or value.
    pub fn try_new(
        grant_key: String,
        label: String,
        value: String,
        citation: ArchiveCitationV1,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        validate_key(&grant_key)?;
        validate_text(&label)?;
        validate_text(&value)?;
        Ok(Self {
            grant_key,
            label,
            value,
            citation,
        })
    }
}

/// One outbound semantic page link.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveLinkV1 {
    target: ArchivePageRefV1,
    known_label: String,
}

impl ArchiveLinkV1 {
    /// Construct one outbound link whose label may be shown only when known.
    ///
    /// # Errors
    /// Refuses an unsafe label.
    pub fn try_new(
        target: ArchivePageRefV1,
        known_label: String,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        validate_text(&known_label)?;
        Ok(Self {
            target,
            known_label,
        })
    }
}

/// One receipt-bound page refresh requested by the semantic worker.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchivePageInputV1 {
    subject: ArchiveSubjectV1,
    verified_tick: u64,
    tick_content_hash: [u8; 32],
    decision_question: String,
    signals: Vec<ArchiveSignalV1>,
    links: Vec<ArchiveLinkV1>,
}

impl ArchivePageInputV1 {
    /// Construct one bounded dirty-subject work item.
    ///
    /// # Errors
    /// Refuses synthetic tick zero, duplicate keys, or unbounded collections.
    pub fn try_new(
        subject: ArchiveSubjectV1,
        verified_tick: u64,
        tick_content_hash: [u8; 32],
        decision_question: String,
        signals: Vec<ArchiveSignalV1>,
        links: Vec<ArchiveLinkV1>,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        if verified_tick == 0 || verified_tick > i64::MAX as u64 {
            return Err(SemanticArchiveErrorV1::InvalidVerifiedTick);
        }
        validate_text(&decision_question)?;
        if signals.len() > MAX_SIGNALS || links.len() > MAX_LINKS {
            return Err(SemanticArchiveErrorV1::CollectionBound);
        }
        let signal_keys = signals
            .iter()
            .map(|signal| signal.grant_key.as_str())
            .collect::<BTreeSet<_>>();
        let link_targets = links
            .iter()
            .map(|link| &link.target)
            .collect::<BTreeSet<_>>();
        if signal_keys.len() != signals.len() || link_targets.len() != links.len() {
            return Err(SemanticArchiveErrorV1::DuplicateKey);
        }
        Ok(Self {
            subject,
            verified_tick,
            tick_content_hash,
            decision_question,
            signals,
            links,
        })
    }
}

/// Exact SQL-derived knowledge grants supplied to the pure renderer.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveKnowledgeV1 {
    subjects: BTreeSet<ArchivePageRefV1>,
    fields: BTreeSet<(ArchivePageRefV1, String)>,
}

impl ArchiveKnowledgeV1 {
    /// Validate an exact SQL grant result.
    ///
    /// # Errors
    /// Refuses duplicate subjects, fields, or invalid field keys.
    pub fn try_new(
        subjects: Vec<ArchivePageRefV1>,
        fields: Vec<(ArchivePageRefV1, String)>,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        for (_, field) in &fields {
            validate_key(field)?;
        }
        let subject_count = subjects.len();
        let field_count = fields.len();
        let subjects = subjects.into_iter().collect::<BTreeSet<_>>();
        let fields = fields.into_iter().collect::<BTreeSet<_>>();
        if subjects.len() != subject_count || fields.len() != field_count {
            return Err(SemanticArchiveErrorV1::DuplicateGrant);
        }
        Ok(Self { subjects, fields })
    }

    fn knows_subject(&self, page_ref: &ArchivePageRefV1) -> bool {
        self.subjects.contains(page_ref)
    }

    fn knows_field(&self, page_ref: &ArchivePageRefV1, grant_key: &str) -> bool {
        self.fields
            .contains(&(page_ref.clone(), grant_key.to_owned()))
    }
}

/// One rendered, searchable, citation-bearing page artifact.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RenderedArchivePageV1 {
    markdown: String,
    search_text: String,
    sha256: [u8; 32],
}

impl RenderedArchivePageV1 {
    /// Borrow exact UTF-8 Markdown bytes.
    #[must_use]
    pub fn markdown(&self) -> &str {
        &self.markdown
    }

    /// Borrow the known-only search materialization.
    #[must_use]
    pub fn search_text(&self) -> &str {
        &self.search_text
    }

    /// Return SHA-256 of exact Markdown bytes.
    #[must_use]
    pub const fn sha256(&self) -> [u8; 32] {
        self.sha256
    }
}

/// Pinned strict `MiniJinja` rendering authority.
pub struct FogSafeArchiveRendererV1 {
    environment: Environment<'static>,
}

impl FogSafeArchiveRendererV1 {
    /// Compile the one embedded template with strict undefined behavior.
    ///
    /// # Errors
    /// Returns [`SemanticArchiveErrorV1::Template`] for checked-in syntax drift.
    pub fn new() -> Result<Self, SemanticArchiveErrorV1> {
        let mut environment = Environment::empty();
        environment.set_undefined_behavior(UndefinedBehavior::Strict);
        environment
            .add_template("archive-page-v1", ARCHIVE_PAGE_TEMPLATE_V1)
            .map_err(|_| SemanticArchiveErrorV1::Template)?;
        Ok(Self { environment })
    }

    /// Render one known subject with SQL-derived field and link grants.
    ///
    /// # Errors
    /// Refuses an unknown subject or any strict template failure.
    pub fn render(
        &self,
        input: &ArchivePageInputV1,
        knowledge: &ArchiveKnowledgeV1,
    ) -> Result<RenderedArchivePageV1, SemanticArchiveErrorV1> {
        if !knowledge.knows_subject(input.subject.page_ref()) {
            return Err(SemanticArchiveErrorV1::UnknownSubject);
        }
        let signals = input
            .signals
            .iter()
            .filter(|signal| knowledge.knows_field(input.subject.page_ref(), &signal.grant_key))
            .map(TemplateSignalV1::from)
            .collect::<Vec<_>>();
        let links = input
            .links
            .iter()
            .map(|link| TemplateLinkV1 {
                page_key: link.target.page_key(),
                known_label: knowledge
                    .knows_subject(&link.target)
                    .then_some(link.known_label.as_str()),
            })
            .collect::<Vec<_>>();
        let tick_content_hash = hex_digest(&input.tick_content_hash);
        let template = self
            .environment
            .get_template("archive-page-v1")
            .map_err(|_| SemanticArchiveErrorV1::Template)?;
        let markdown = template
            .render(context! {
                subject_key => input.subject.page_ref().page_key(),
                title => input.subject.title(),
                verified_tick => input.verified_tick,
                tick_content_hash => tick_content_hash,
                decision_question => input.decision_question.as_str(),
                signals => signals,
                links => links,
            })
            .map_err(|_| SemanticArchiveErrorV1::Template)?;
        let search_text = known_search_text(input, knowledge);
        if markdown.len() > MAX_PAGE_BYTES || search_text.len() > MAX_PAGE_BYTES {
            return Err(SemanticArchiveErrorV1::CollectionBound);
        }
        let sha256 = sha256_of(markdown.as_bytes());
        Ok(RenderedArchivePageV1 {
            markdown,
            search_text,
            sha256,
        })
    }

    /// Return the checked-in template identity.
    #[must_use]
    pub const fn template_sha256(&self) -> [u8; 32] {
        ARCHIVE_PAGE_TEMPLATE_SHA256_V1
    }
}

/// One bounded batch bound to a single committed dirty receipt.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveDirtyBatchV1 {
    resolve_tick: u64,
    tick_content_hash: [u8; 32],
    pages: Vec<ArchivePageInputV1>,
}

impl ArchiveDirtyBatchV1 {
    /// Validate an ordered dirty-subject batch.
    ///
    /// # Errors
    /// Refuses tick mismatch, duplicate subjects, or more than 256 pages.
    pub fn try_new(
        resolve_tick: u64,
        tick_content_hash: [u8; 32],
        pages: Vec<ArchivePageInputV1>,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        if resolve_tick == 0 || resolve_tick > i64::MAX as u64 {
            return Err(SemanticArchiveErrorV1::InvalidVerifiedTick);
        }
        if pages.len() > MAX_LINKS {
            return Err(SemanticArchiveErrorV1::CollectionBound);
        }
        let subjects = pages
            .iter()
            .map(|page| page.subject.page_ref())
            .collect::<BTreeSet<_>>();
        if subjects.len() != pages.len() {
            return Err(SemanticArchiveErrorV1::DuplicateKey);
        }
        if pages.iter().any(|page| {
            page.verified_tick != resolve_tick || page.tick_content_hash != tick_content_hash
        }) {
            return Err(SemanticArchiveErrorV1::ReceiptMismatch);
        }
        Ok(Self {
            resolve_tick,
            tick_content_hash,
            pages,
        })
    }

    /// Hash every exact ordered input byte used to materialize this receipt.
    #[must_use]
    pub fn sha256(&self) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(ARCHIVE_DIRTY_BATCH_DOMAIN_V1);
        hasher.update(self.resolve_tick.to_be_bytes());
        hasher.update(self.tick_content_hash);
        hash_len(&mut hasher, self.pages.len());
        for page in &self.pages {
            hash_page_input(&mut hasher, page);
        }
        hasher.finalize().into()
    }
}

/// One append-only SQL knowledge grant.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveKnowledgeGrantV1 {
    page_ref: ArchivePageRefV1,
    grant_key: String,
    granted_tick: u64,
    citation: ArchiveCitationV1,
}

impl ArchiveKnowledgeGrantV1 {
    /// Construct one subject (`subject`) or field grant.
    ///
    /// # Errors
    /// Refuses an unsafe key or a tick outside `PostgreSQL` `BIGINT`.
    pub fn try_new(
        page_ref: ArchivePageRefV1,
        grant_key: String,
        granted_tick: u64,
        citation: ArchiveCitationV1,
    ) -> Result<Self, SemanticArchiveErrorV1> {
        validate_key(&grant_key)?;
        if granted_tick > i64::MAX as u64 {
            return Err(SemanticArchiveErrorV1::InvalidVerifiedTick);
        }
        Ok(Self {
            page_ref,
            grant_key,
            granted_tick,
            citation,
        })
    }
}

/// Idempotent schema-install result.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ArchiveSchemaDispositionV1 {
    /// The exact additive schema committed now.
    Installed,
    /// The exact contract marker and all relations already existed.
    AlreadyCurrent,
}

/// Idempotent receipt-consumption result.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ArchiveMaterializeDispositionV1 {
    /// This invocation consumed and rendered the receipt.
    Applied,
    /// The exact worker contract had already consumed the receipt.
    AlreadyConsumed,
}

/// One persisted page result from an applied batch.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MaterializedArchivePageV1 {
    page_ref: ArchivePageRefV1,
    page: RenderedArchivePageV1,
    persisted: bool,
}

impl MaterializedArchivePageV1 {
    /// Borrow the stable page identity.
    #[must_use]
    pub const fn page_ref(&self) -> &ArchivePageRefV1 {
        &self.page_ref
    }

    /// Borrow the rendered artifact.
    #[must_use]
    pub const fn page(&self) -> &RenderedArchivePageV1 {
        &self.page
    }

    /// Whether this page replaced the current materialization.
    #[must_use]
    pub const fn persisted(&self) -> bool {
        self.persisted
    }
}

/// Receipt-level worker report.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveMaterializeReportV1 {
    disposition: ArchiveMaterializeDispositionV1,
    pages: Vec<MaterializedArchivePageV1>,
}

impl ArchiveMaterializeReportV1 {
    /// Return whether this invocation applied or observed an exact retry.
    #[must_use]
    pub const fn disposition(&self) -> ArchiveMaterializeDispositionV1 {
        self.disposition
    }

    /// Borrow rendered page results in caller-supplied order.
    #[must_use]
    pub fn pages(&self) -> &[MaterializedArchivePageV1] {
        &self.pages
    }
}

/// One fog-safe search result with page, tick, hash, and provenance citations.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArchiveSearchHitV1 {
    page_ref: ArchivePageRefV1,
    title: String,
    verified_tick: u64,
    markdown: String,
    content_sha256: [u8; 32],
    citations: Vec<ArchiveCitationV1>,
}

impl ArchiveSearchHitV1 {
    /// Borrow the known page identity.
    #[must_use]
    pub const fn page_ref(&self) -> &ArchivePageRefV1 {
        &self.page_ref
    }

    /// Borrow the known title.
    #[must_use]
    pub fn title(&self) -> &str {
        &self.title
    }

    /// Return the page's honest committed source tick.
    #[must_use]
    pub const fn verified_tick(&self) -> u64 {
        self.verified_tick
    }

    /// Borrow exact rendered Markdown.
    #[must_use]
    pub fn markdown(&self) -> &str {
        &self.markdown
    }

    /// Return SHA-256 of exact rendered Markdown.
    #[must_use]
    pub const fn content_sha256(&self) -> [u8; 32] {
        self.content_sha256
    }

    /// Borrow the player-visible provenance citations.
    #[must_use]
    pub fn citations(&self) -> &[ArchiveCitationV1] {
        &self.citations
    }
}

/// `PostgreSQL` adapter for the client-owned epistemic Archive tier.
#[derive(Clone)]
pub struct SemanticArchiveStoreV1 {
    config: Config,
}

impl SemanticArchiveStoreV1 {
    /// Bind the worker to one Rust-authoritative `PostgreSQL` target.
    #[must_use]
    pub fn new(config: &Config) -> Self {
        Self {
            config: config.clone(),
        }
    }

    /// Install the additive Archive schema under the shared schema lock.
    ///
    /// # Errors
    /// Refuses partial markers, a wrong contract row, or database failure.
    pub fn install_schema(&self) -> Result<ArchiveSchemaDispositionV1, SemanticArchiveErrorV1> {
        let mut client = self.connect("connect Archive schema installer")?;
        client
            .query_one(
                "SELECT pg_catalog.pg_advisory_lock($1)",
                &[&SCHEMA_ADVISORY_LOCK_KEY],
            )
            .map_err(|_| database("lock Archive schema installer"))?;
        let result = (|| {
            let row = client
                .query_one(ARCHIVE_SCHEMA_MARKERS_SQL_V1, &[])
                .map_err(|_| database("inspect Archive schema markers"))?;
            let markers = [
                decode::<bool>(&row, 0)?,
                decode::<bool>(&row, 1)?,
                decode::<bool>(&row, 2)?,
                decode::<bool>(&row, 3)?,
            ];
            if markers == [false; 4] {
                let mut transaction = client
                    .build_transaction()
                    .isolation_level(IsolationLevel::Serializable)
                    .start()
                    .map_err(|_| database("begin Archive schema install"))?;
                transaction
                    .batch_execute(
                        "SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on",
                    )
                    .map_err(|_| database("set Archive schema install settings"))?;
                transaction
                    .batch_execute(SEMANTIC_ARCHIVE_SCHEMA_V1_SQL)
                    .map_err(|_| database("install Archive schema"))?;
                transaction
                    .commit()
                    .map_err(|_| database("commit Archive schema"))?;
                Ok(ArchiveSchemaDispositionV1::Installed)
            } else if markers == [true; 4] {
                let row = client
                    .query_one(
                        "SELECT contract_id FROM babylon_meta.semantic_archive_schema_v1",
                        &[],
                    )
                    .map_err(|_| database("read Archive schema contract"))?;
                let contract_id: String = decode(&row, 0)?;
                if contract_id != ARCHIVE_SCHEMA_CONTRACT_ID {
                    return Err(SemanticArchiveErrorV1::SchemaMismatch);
                }
                Ok(ArchiveSchemaDispositionV1::AlreadyCurrent)
            } else {
                Err(SemanticArchiveErrorV1::PartialSchema)
            }
        })();
        let unlock = client
            .query_one(
                "SELECT pg_catalog.pg_advisory_unlock($1)",
                &[&SCHEMA_ADVISORY_LOCK_KEY],
            )
            .and_then(|row| row.try_get::<_, bool>(0))
            .map_err(|_| database("unlock Archive schema installer"));
        match (result, unlock) {
            (Err(error), _) | (Ok(_), Err(error)) => Err(error),
            (Ok(disposition), Ok(true)) => Ok(disposition),
            (Ok(_), Ok(false)) => Err(SemanticArchiveErrorV1::SchemaMismatch),
        }
    }

    /// Insert one immutable subject or field knowledge grant.
    ///
    /// # Errors
    /// Exact retry succeeds; conflicting provenance or tick refuses.
    pub fn grant_knowledge(
        &self,
        campaign_id: CampaignId,
        grant: &ArchiveKnowledgeGrantV1,
    ) -> Result<(), SemanticArchiveErrorV1> {
        let mut client = self.connect("connect Archive knowledge writer")?;
        let granted_tick = i64::try_from(grant.granted_tick)
            .map_err(|_| SemanticArchiveErrorV1::InvalidVerifiedTick)?;
        let affected = client
            .execute(
                "INSERT INTO babylon_meta.archive_knowledge_grant_v1 \
                 (campaign_id, subject_kind, subject_id, grant_key, granted_tick, \
                  provenance_source_id, provenance_locator) \
                 VALUES ($1::uuid, $2, $3, $4, $5, $6, $7) \
                 ON CONFLICT (campaign_id, subject_kind, subject_id, grant_key) DO NOTHING",
                &[
                    campaign_id.as_uuid(),
                    &grant.page_ref.kind.as_str(),
                    &grant.page_ref.id,
                    &grant.grant_key,
                    &granted_tick,
                    &grant.citation.source_id,
                    &grant.citation.locator,
                ],
            )
            .map_err(|_| database("insert Archive knowledge grant"))?;
        if affected == 1 {
            return Ok(());
        }
        let row = client
            .query_one(
                "SELECT granted_tick, provenance_source_id, provenance_locator \
                 FROM babylon_meta.archive_knowledge_grant_v1 \
                 WHERE campaign_id = $1::uuid AND subject_kind = $2 \
                   AND subject_id = $3 AND grant_key = $4",
                &[
                    campaign_id.as_uuid(),
                    &grant.page_ref.kind.as_str(),
                    &grant.page_ref.id,
                    &grant.grant_key,
                ],
            )
            .map_err(|_| database("reconcile Archive knowledge grant"))?;
        let exact = decode::<i64>(&row, 0)? == granted_tick
            && decode::<String>(&row, 1)? == grant.citation.source_id
            && decode::<String>(&row, 2)? == grant.citation.locator;
        if exact {
            Ok(())
        } else {
            Err(SemanticArchiveErrorV1::GrantConflict)
        }
    }

    /// Consume one committed receipt and materialize its dirty page batch atomically.
    ///
    /// # Errors
    /// Refuses an absent/mismatched receipt, unknown page subject, template failure,
    /// conflicting prior consumption, or database failure.
    pub fn materialize_receipt(
        &self,
        campaign_id: CampaignId,
        batch: &ArchiveDirtyBatchV1,
    ) -> Result<ArchiveMaterializeReportV1, SemanticArchiveErrorV1> {
        let renderer = FogSafeArchiveRendererV1::new()?;
        let resolve_tick = i64::try_from(batch.resolve_tick)
            .map_err(|_| SemanticArchiveErrorV1::InvalidVerifiedTick)?;
        let batch_sha256 = batch.sha256();
        let worker_contract = archive_worker_contract_sha256_v1();
        let mut client = self.connect("connect semantic Archive worker")?;
        let mut transaction = client
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .start()
            .map_err(|_| database("begin semantic Archive receipt"))?;
        let receipt = transaction
            .query_opt(
                ARCHIVE_RECEIPT_SQL_V1,
                &[campaign_id.as_uuid(), &resolve_tick],
            )
            .map_err(|_| database("read committed Archive receipt"))?
            .ok_or(SemanticArchiveErrorV1::MissingCommittedReceipt)?;
        let receipt_hash = decode_digest(&receipt, 0)?;
        if receipt_hash != batch.tick_content_hash {
            return Err(SemanticArchiveErrorV1::ReceiptMismatch);
        }
        let claimed = transaction
            .execute(
                "INSERT INTO babylon_meta.archive_receipt_consumption_v1 \
                 (campaign_id, resolve_tick, tick_content_hash, batch_sha256, \
                  worker_contract_sha256) \
                 VALUES ($1::uuid, $2, $3, $4, $5) \
                 ON CONFLICT (campaign_id, resolve_tick) DO NOTHING",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    &&batch.tick_content_hash[..],
                    &&batch_sha256[..],
                    &&worker_contract[..],
                ],
            )
            .map_err(|_| database("claim Archive receipt"))?;
        if claimed == 0 {
            let row = transaction
                .query_one(
                    "SELECT tick_content_hash, batch_sha256, worker_contract_sha256 \
                     FROM babylon_meta.archive_receipt_consumption_v1 \
                     WHERE campaign_id = $1::uuid AND resolve_tick = $2",
                    &[campaign_id.as_uuid(), &resolve_tick],
                )
                .map_err(|_| database("reconcile Archive receipt"))?;
            if decode_digest(&row, 0)? != batch.tick_content_hash
                || decode_digest(&row, 1)? != batch_sha256
                || decode_digest(&row, 2)? != worker_contract
            {
                return Err(SemanticArchiveErrorV1::ReceiptConflict);
            }
            transaction
                .commit()
                .map_err(|_| database("commit exact Archive retry"))?;
            return Ok(ArchiveMaterializeReportV1 {
                disposition: ArchiveMaterializeDispositionV1::AlreadyConsumed,
                pages: Vec::new(),
            });
        }
        let knowledge = read_knowledge(&mut transaction, campaign_id, resolve_tick)?;
        let mut materialized = Vec::with_capacity(batch.pages.len());
        for input in &batch.pages {
            let page = renderer.render(input, &knowledge)?;
            let citations = known_citations(input, &knowledge);
            let provenance_json = serde_json::to_string(&citations)
                .map_err(|_| SemanticArchiveErrorV1::InvalidText)?;
            let persisted = persist_page(
                &mut transaction,
                campaign_id,
                resolve_tick,
                &batch.tick_content_hash,
                input,
                &page,
                &provenance_json,
            )?;
            materialized.push(MaterializedArchivePageV1 {
                page_ref: input.subject.page_ref.clone(),
                page,
                persisted,
            });
        }
        transaction
            .commit()
            .map_err(|_| database("commit semantic Archive receipt"))?;
        Ok(ArchiveMaterializeReportV1 {
            disposition: ArchiveMaterializeDispositionV1::Applied,
            pages: materialized,
        })
    }

    /// Search only SQL-known materialized pages.
    ///
    /// # Errors
    /// Refuses a limit above 100, malformed stored rows, or database failure.
    pub fn search_known(
        &self,
        campaign_id: CampaignId,
        query: &str,
        limit: u32,
    ) -> Result<Vec<ArchiveSearchHitV1>, SemanticArchiveErrorV1> {
        if query.trim().is_empty() {
            return Ok(Vec::new());
        }
        if limit == 0 || limit > MAX_SEARCH_HITS {
            return Err(SemanticArchiveErrorV1::CollectionBound);
        }
        validate_text(query)?;
        let limit = i64::from(limit);
        let mut client = self.connect("connect known Archive search")?;
        client
            .query(
                ARCHIVE_SEARCH_SQL_V1,
                &[campaign_id.as_uuid(), &query, &limit],
            )
            .map_err(|_| database("search known Archive pages"))?
            .iter()
            .map(decode_search_hit)
            .collect()
    }

    fn connect(&self, operation: &'static str) -> Result<postgres::Client, SemanticArchiveErrorV1> {
        self.config.connect(NoTls).map_err(|_| database(operation))
    }
}

/// Hash the exact schema and template inputs used by the idempotent worker.
#[must_use]
pub fn archive_worker_contract_sha256_v1() -> [u8; 32] {
    let mut bytes = Vec::with_capacity(
        ARCHIVE_WORKER_DOMAIN_V1.len()
            + SEMANTIC_ARCHIVE_SCHEMA_V1_SQL.len()
            + ARCHIVE_PAGE_TEMPLATE_SHA256_V1.len(),
    );
    bytes.extend_from_slice(ARCHIVE_WORKER_DOMAIN_V1);
    bytes.extend_from_slice(SEMANTIC_ARCHIVE_SCHEMA_V1_SQL.as_bytes());
    bytes.extend_from_slice(&ARCHIVE_PAGE_TEMPLATE_SHA256_V1);
    sha256_of(&bytes)
}

fn read_knowledge(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
) -> Result<ArchiveKnowledgeV1, SemanticArchiveErrorV1> {
    let rows = client
        .query(
            ARCHIVE_KNOWLEDGE_SQL_V1,
            &[
                campaign_id.as_uuid(),
                &resolve_tick,
                &i64::try_from(MAX_KNOWLEDGE_GRANTS + 1)
                    .map_err(|_| SemanticArchiveErrorV1::CollectionBound)?,
            ],
        )
        .map_err(|_| database("read Archive knowledge grants"))?;
    if rows.len() > MAX_KNOWLEDGE_GRANTS {
        return Err(SemanticArchiveErrorV1::CollectionBound);
    }
    let mut subjects = Vec::with_capacity(rows.len());
    let mut fields = Vec::with_capacity(rows.len());
    for row in rows {
        let kind = decode_subject_kind(&decode::<String>(&row, 0)?)?;
        let page_ref = ArchivePageRefV1::try_new(kind, decode(&row, 1)?)?;
        let grant_key: String = decode(&row, 2)?;
        if grant_key == "subject" {
            subjects.push(page_ref);
        } else {
            fields.push((page_ref, grant_key));
        }
    }
    ArchiveKnowledgeV1::try_new(subjects, fields)
}

fn known_citations(
    input: &ArchivePageInputV1,
    knowledge: &ArchiveKnowledgeV1,
) -> Vec<ArchiveCitationV1> {
    input
        .signals
        .iter()
        .filter(|signal| knowledge.knows_field(input.subject.page_ref(), &signal.grant_key))
        .map(|signal| signal.citation.clone())
        .collect()
}

fn persist_page(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    tick_content_hash: &[u8; 32],
    input: &ArchivePageInputV1,
    page: &RenderedArchivePageV1,
    provenance_json: &str,
) -> Result<bool, SemanticArchiveErrorV1> {
    client
        .execute(
            "INSERT INTO babylon_meta.archive_page_v1 \
             (campaign_id, subject_kind, subject_id, title, verified_tick, \
              source_resolve_tick, source_tick_content_hash, template_sha256, \
              content_sha256, markdown, search_text, provenance_json) \
             VALUES ($1::uuid, $2, $3, $4, $5, $5, $6, $7, $8, $9, $10, $11) \
             ON CONFLICT (campaign_id, subject_kind, subject_id) DO UPDATE SET \
               title = EXCLUDED.title, verified_tick = EXCLUDED.verified_tick, \
               source_resolve_tick = EXCLUDED.source_resolve_tick, \
               source_tick_content_hash = EXCLUDED.source_tick_content_hash, \
               template_sha256 = EXCLUDED.template_sha256, \
               content_sha256 = EXCLUDED.content_sha256, markdown = EXCLUDED.markdown, \
               search_text = EXCLUDED.search_text, provenance_json = EXCLUDED.provenance_json \
             WHERE babylon_meta.archive_page_v1.source_resolve_tick <= \
                   EXCLUDED.source_resolve_tick",
            &[
                campaign_id.as_uuid(),
                &input.subject.page_ref.kind.as_str(),
                &input.subject.page_ref.id,
                &input.subject.title,
                &resolve_tick,
                &&tick_content_hash[..],
                &&ARCHIVE_PAGE_TEMPLATE_SHA256_V1[..],
                &&page.sha256[..],
                &page.markdown,
                &page.search_text,
                &provenance_json,
            ],
        )
        .map(|affected| affected == 1)
        .map_err(|_| database("upsert semantic Archive page"))
}

fn decode_search_hit(row: &Row) -> Result<ArchiveSearchHitV1, SemanticArchiveErrorV1> {
    let kind = decode_subject_kind(&decode::<String>(row, 0)?)?;
    let page_ref = ArchivePageRefV1::try_new(kind, decode(row, 1)?)?;
    let title: String = decode(row, 2)?;
    validate_text(&title)?;
    let verified_tick = decode::<i64>(row, 3)?;
    let verified_tick = u64::try_from(verified_tick)
        .ok()
        .filter(|tick| *tick > 0)
        .ok_or(SemanticArchiveErrorV1::StoredPageMismatch)?;
    let markdown: String = decode(row, 4)?;
    let content_sha256 = decode_digest(row, 5)?;
    if sha256_of(markdown.as_bytes()) != content_sha256 {
        return Err(SemanticArchiveErrorV1::StoredPageMismatch);
    }
    let provenance_json: String = decode(row, 6)?;
    let citations: Vec<ArchiveCitationV1> = serde_json::from_str(&provenance_json)
        .map_err(|_| SemanticArchiveErrorV1::StoredPageMismatch)?;
    for citation in &citations {
        validate_text(&citation.source_id)?;
        validate_text(&citation.locator)?;
    }
    Ok(ArchiveSearchHitV1 {
        page_ref,
        title,
        verified_tick,
        markdown,
        content_sha256,
        citations,
    })
}

fn decode_subject_kind(value: &str) -> Result<ArchiveSubjectKindV1, SemanticArchiveErrorV1> {
    match value {
        "county" => Ok(ArchiveSubjectKindV1::County),
        "place" => Ok(ArchiveSubjectKindV1::Place),
        _ => Err(SemanticArchiveErrorV1::StoredPageMismatch),
    }
}

fn decode<T: FromSqlOwned>(row: &Row, index: usize) -> Result<T, SemanticArchiveErrorV1> {
    row.try_get(index)
        .map_err(|_| database("decode semantic Archive row"))
}

fn decode_digest(row: &Row, index: usize) -> Result<[u8; 32], SemanticArchiveErrorV1> {
    let bytes: Vec<u8> = decode(row, index)?;
    bytes
        .try_into()
        .map_err(|_| SemanticArchiveErrorV1::StoredPageMismatch)
}

const fn database(operation: &'static str) -> SemanticArchiveErrorV1 {
    SemanticArchiveErrorV1::Database { operation }
}

#[derive(Serialize)]
struct TemplateSignalV1<'a> {
    label: &'a str,
    value: &'a str,
    citation: &'a ArchiveCitationV1,
}

impl<'a> From<&'a ArchiveSignalV1> for TemplateSignalV1<'a> {
    fn from(signal: &'a ArchiveSignalV1) -> Self {
        Self {
            label: &signal.label,
            value: &signal.value,
            citation: &signal.citation,
        }
    }
}

#[derive(Serialize)]
struct TemplateLinkV1<'a> {
    page_key: String,
    known_label: Option<&'a str>,
}

/// Stable closed refusal taxonomy for semantic Archive inputs and rendering.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SemanticArchiveErrorV1 {
    /// County or place identity was malformed.
    InvalidIdentity,
    /// Human-readable or grant-key text was unsafe or unbounded.
    InvalidText,
    /// Tick zero or a value outside `PostgreSQL` `BIGINT` was supplied.
    InvalidVerifiedTick,
    /// A fixed collection ceiling was exceeded.
    CollectionBound,
    /// One work item repeated a signal or link identity.
    DuplicateKey,
    /// One SQL grant row was repeated.
    DuplicateGrant,
    /// SQL did not grant knowledge of the page subject.
    UnknownSubject,
    /// A page or batch did not match its committed dirty receipt.
    ReceiptMismatch,
    /// No marker-backed dirty receipt exists for the requested tick.
    MissingCommittedReceipt,
    /// A different worker contract previously consumed the receipt.
    ReceiptConflict,
    /// An existing knowledge grant differs from the immutable retry.
    GrantConflict,
    /// Only part of the additive Archive schema exists.
    PartialSchema,
    /// The Archive schema marker or unlock result was not exact.
    SchemaMismatch,
    /// A stored page, digest, kind, tick, or provenance row was malformed.
    StoredPageMismatch,
    /// The pinned strict template failed to compile or render.
    Template,
    /// One database operation failed without retaining driver text.
    Database {
        /// Stable operation identity.
        operation: &'static str,
    },
}

impl std::fmt::Display for SemanticArchiveErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "semantic Archive refusal: {self:?}")
    }
}

impl std::error::Error for SemanticArchiveErrorV1 {}

fn validate_text(value: &str) -> Result<(), SemanticArchiveErrorV1> {
    if value.is_empty() || value.len() > MAX_TEXT_BYTES || value.as_bytes().contains(&0) {
        return Err(SemanticArchiveErrorV1::InvalidText);
    }
    Ok(())
}

fn validate_key(value: &str) -> Result<(), SemanticArchiveErrorV1> {
    if value.is_empty()
        || value.len() > MAX_ID_BYTES
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
    {
        return Err(SemanticArchiveErrorV1::InvalidText);
    }
    Ok(())
}

fn hash_page_input(hasher: &mut Sha256, input: &ArchivePageInputV1) {
    hash_page_ref(hasher, input.subject.page_ref());
    hash_bytes(hasher, input.subject.title.as_bytes());
    hasher.update(input.verified_tick.to_be_bytes());
    hasher.update(input.tick_content_hash);
    hash_bytes(hasher, input.decision_question.as_bytes());
    hash_len(hasher, input.signals.len());
    for signal in &input.signals {
        hash_bytes(hasher, signal.grant_key.as_bytes());
        hash_bytes(hasher, signal.label.as_bytes());
        hash_bytes(hasher, signal.value.as_bytes());
        hash_citation(hasher, &signal.citation);
    }
    hash_len(hasher, input.links.len());
    for link in &input.links {
        hash_page_ref(hasher, &link.target);
        hash_bytes(hasher, link.known_label.as_bytes());
    }
}

fn hash_page_ref(hasher: &mut Sha256, page_ref: &ArchivePageRefV1) {
    hasher.update([match page_ref.kind {
        ArchiveSubjectKindV1::County => 1,
        ArchiveSubjectKindV1::Place => 2,
    }]);
    hash_bytes(hasher, page_ref.id.as_bytes());
}

fn hash_citation(hasher: &mut Sha256, citation: &ArchiveCitationV1) {
    hash_bytes(hasher, citation.source_id.as_bytes());
    hash_bytes(hasher, citation.locator.as_bytes());
}

fn hash_len(hasher: &mut Sha256, len: usize) {
    hasher.update(u64::try_from(len).unwrap_or(u64::MAX).to_be_bytes());
}

fn hash_bytes(hasher: &mut Sha256, bytes: &[u8]) {
    hash_len(hasher, bytes.len());
    hasher.update(bytes);
}

fn known_search_text(input: &ArchivePageInputV1, knowledge: &ArchiveKnowledgeV1) -> String {
    let mut parts = vec![
        input.subject.page_ref().page_key(),
        input.subject.title().to_owned(),
    ];
    for signal in &input.signals {
        if knowledge.knows_field(input.subject.page_ref(), &signal.grant_key) {
            parts.push(signal.label.clone());
            parts.push(signal.value.clone());
        }
    }
    for link in &input.links {
        if knowledge.knows_subject(&link.target) {
            parts.push(link.target.page_key());
            parts.push(link.known_label.clone());
        }
    }
    parts.join(" ")
}

fn hex_digest(digest: &[u8; 32]) -> String {
    use std::fmt::Write as _;
    let mut output = String::with_capacity(64);
    for byte in digest {
        write!(&mut output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strict_mode_refuses_missing_template_names() {
        let mut environment = Environment::empty();
        environment.set_undefined_behavior(UndefinedBehavior::Strict);
        environment
            .add_template("missing", "{{ absent }}")
            .expect("test template compiles");
        assert!(environment
            .get_template("missing")
            .expect("test template exists")
            .render(context! {})
            .is_err());
    }
}
