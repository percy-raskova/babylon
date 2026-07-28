//! Topology pane payloads + the 2D glyph-floor renderers (M4, contract
//! `docs/superpowers/specs/2026-07-27-m4-topology-contracts.md` §1/§4; plan
//! Task 31).
//!
//! **Scope of this file today (a declared zipper point — mirrors
//! `test_egotree_directive.py`/`test_matrix_directive.py`'s own "keep each
//! WO's directive tests in its own file" rationale, applied to a Rust
//! module instead of a test file):** this pass adds ONLY the 2D half — the
//! four §1 envelope payload structs ([`PaohPayload`], [`EgotreePayload`],
//! [`IncidencePayload`], [`AdjacencyPayload`], plus the self-dispatching
//! [`TopologyPayload`] enum) and their byte-faithful glyph-floor render
//! functions. The chrome-owned `TopologyView` struct (kind/focus/camera
//! state, key routing per §6) and the 3D scene builders (§5, Tasks 32-34)
//! land in this SAME file as a later addition, not a duplicate module — a
//! deliberate zipper point, not an accident of two lanes racing on one path.
//!
//! Every payload struct here deserializes directly from the JSON string
//! `crate::host::Host::topology_json` returns (§1) — never from
//! fence-directive text: `babylon.tui.directives` /
//! `babylon.tui.topology.{egotree,matrix}` parse the OTHER (baked-page)
//! representation of the same four shapes and stay entirely Python-side (a
//! baked `{paoh}`/`{egotree}`/`{matrix}` fence is III.13's "materialized
//! view", not this live seam). `verified_tick` and (for `paoh`) `layout`
//! are carried through for a later consumer (a tick banner; the Task 33
//! hypergraph 3D builder's node positions) — the 2D renderers below read
//! neither field.
//!
//! **Color mapping (§4's "byte-faithful ports... colors mapped through the
//! parity-guarded tokens" ruling), shared by every renderer in this
//! module:**
//!
//! | Python role   | Rust color                     |
//! |----------------|--------------------------------|
//! | `$foreground`  | [`BONE`]                        |
//! | `$text-muted`  | [`DIM`]                         |
//! | `b $accent`    | bold [`GOLD`]                   |
//! | `$primary`     | [`CRIMSON`]                     |
//! | `$panel`       | the module-local [`PANEL`]      |

use std::collections::BTreeMap;

use ratatui::crossterm::event::KeyCode;
use ratatui::layout::Rect;
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;
use serde::Deserialize;

use crate::theme::{BONE, CRIMSON, DIM, GOLD};

/// The panel-muted glyph tone (`babylon/tui/theme.py:76`: `PANEL: Final =
/// "#200404"`, "Plate background, one step up from the field... NOT a §9b
/// role token" — see that module's own docstring). Declared HERE rather
/// than in `theme.rs`, mirroring `chronicle::AMBER`'s own precedent: the
/// cross-language parity guard (`tests/unit/render/test_rust_theme_parity.py`)
/// parses every `Color::Rgb` literal in `theme.rs` against the Python §9b
/// palette and would fail on a constant with no §9b counterpart — this
/// module keeps its own copy instead of adding a non-§9b `theme.rs` const.
pub const PANEL: Color = Color::Rgb(32, 4, 4);

/// One `{paoh}` hyperedge column: a community's roster at projection time,
/// per §1's `paoh` envelope (`edges[]`).
#[derive(Debug, Clone, Deserialize)]
pub struct PaohEdgePayload {
    /// The `CommunityType` value this hyperedge represents. Unread by
    /// [`render_paoh`] (column POSITION is the identity the glyph grid
    /// shows; `community_id` is only `paoh_ordering`'s tie-break key) —
    /// carried through for a later consumer without a second host round
    /// trip.
    pub community_id: String,
    /// The tick this hyperedge formed, or `None`. `paoh.py`'s own module
    /// docstring: **every edge today carries `None`** — no producer for
    /// `CommunityView.formation_tick` exists yet. See [`render_paoh`]'s
    /// docs for how a `None` tick renders.
    pub formation_tick: Option<u64>,
    /// The community's roster at projection time (serializes SORTED per
    /// §1: "`members` serializes SORTED").
    pub members: Vec<String>,
}

/// The `paoh` kind envelope (§1).
#[derive(Debug, Clone, Deserialize)]
pub struct PaohPayload {
    pub verified_tick: u64,
    /// Row labels, in `paoh_ordering`'s lexicographic order.
    pub nodes: Vec<String>,
    /// Columns, already in `paoh_ordering`'s tick-then-`community_id`
    /// order — NOT re-sorted here; [`render_paoh`] trusts the host's own
    /// ordering (§1: "`edges` keep `paoh_ordering`'s order").
    pub edges: Vec<PaohEdgePayload>,
    /// Closed-form bipartite-shell coordinates (member outer circle,
    /// community inner circle; §1's layout ruling) — the Task 33
    /// hypergraph 3D builder's input. [`render_paoh`] never reads this
    /// field: the glyph floor is text-grid, not spatial (§1's own ruling).
    pub layout: BTreeMap<String, [f64; 2]>,
}

/// One `{egotree}` depth-1 child, with its own depth-2 fan-out, per §1's
/// `egotree` envelope (`children[]`).
#[derive(Debug, Clone, Deserialize)]
pub struct EgotreeChildPayload {
    pub node_id: String,
    pub neighbors: Vec<String>,
}

/// The `egotree` kind envelope (§1). `focus` is REQUIRED for this kind
/// (§1's own ruling) — an absent/unknown root already resolved to the
/// honest-absence `null` payload before a struct of this shape is ever
/// built, so [`render_egotree`] never has to handle that case itself.
#[derive(Debug, Clone, Deserialize)]
pub struct EgotreePayload {
    pub verified_tick: u64,
    pub root_id: String,
    /// `"member"` or `"community"` — which Levi node class the root sits
    /// on. Kept as a plain `String` rather than a closed Rust enum: the
    /// display-only `(side)` suffix in [`render_egotree`] only prints the
    /// value, it never branches on it.
    pub root_side: String,
    /// Depth-1 children, in the host's own order (`LeviEgoTree.children`
    /// is already sorted by `node_id` server-side).
    pub children: Vec<EgotreeChildPayload>,
}

/// The `incidence` kind envelope (§1): a node × hyperedge membership grid.
#[derive(Debug, Clone, Deserialize)]
pub struct IncidencePayload {
    pub verified_tick: u64,
    pub nodes: Vec<String>,
    pub hyperedges: Vec<String>,
    /// Row-major membership grid; `cells[r][c]` is `true` iff `nodes[r]`
    /// belongs to `hyperedges[c]`.
    pub cells: Vec<Vec<bool>>,
}

/// The `adjacency` kind envelope (§1): a node × node co-membership grid.
#[derive(Debug, Clone, Deserialize)]
pub struct AdjacencyPayload {
    pub verified_tick: u64,
    pub nodes: Vec<String>,
    /// Row-major, symmetric grid with a `false` diagonal (self-adjacency
    /// is not a meaningful quantity — see [`render_adjacency`]).
    pub cells: Vec<Vec<bool>>,
}

/// The self-dispatching union of §1's four envelopes, tagged on the
/// wire's own `"kind"` field — deserialize the raw `topology_json` string
/// (once it's confirmed non-`"null"`) straight into this to route without
/// a caller-side `match` on a separately-parsed kind string.
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum TopologyPayload {
    Paoh(PaohPayload),
    Egotree(EgotreePayload),
    Incidence(IncidencePayload),
    Adjacency(AdjacencyPayload),
}

impl TopologyPayload {
    /// Render this payload with its own kind's glyph-floor renderer.
    #[must_use]
    pub fn render(&self) -> Vec<Line<'static>> {
        match self {
            Self::Paoh(payload) => render_paoh(payload),
            Self::Egotree(payload) => render_egotree(payload),
            Self::Incidence(payload) => render_incidence(payload),
            Self::Adjacency(payload) => render_adjacency(payload),
        }
    }
}

/// Render a `paoh` payload as PAOH cell-art: nodes as rows, hyperedges as
/// tick-ordered columns — a byte-faithful port of
/// `babylon.tui.directives.render_paoh` (`directives.py:122-149`) over the
/// §1 envelope shape instead of a parsed fence body. 4-char cells
/// (glyph + 3 spaces), 10-char row labels (+1 literal space) [`BONE`].
///
/// Glyphs: `●` bold [`GOLD`] where the row's node is a member of that
/// column's hyperedge; `│` [`CRIMSON`] where the node sits strictly
/// between two member rows (a span connector, never itself a member);
/// [`PANEL`] `·` otherwise.
///
/// **`formation_tick: null` ruling (contract §1/§4 silence on this exact
/// point — recorded as a deviation in the M4 port's own tracking):**
/// `directives.py::render_paoh` never receives a `None` tick in practice —
/// `parse_paoh_body`'s fence grammar requires an integer per edge line,
/// and `format_paoh_fence_body` (`paoh.py`) honestly *omits* any edge with
/// no formation tick before it ever reaches a baked fence body. The §1
/// envelope carries no such filter (`_community_views`' aggregation
/// attributes every roster-bearing community), so a `None` tick is
/// actually the LIVE case today: every `CommunityView.formation_tick` is
/// `None` until a producer lands (`paoh.py`'s own module docstring).
/// Rendering nothing would silently drop a real hyperedge column
/// (Constitution III.11); fabricating a tick number would be worse. This
/// renderer prints the honest, same-width placeholder `"t?  "` instead of
/// either.
#[must_use]
pub fn render_paoh(payload: &PaohPayload) -> Vec<Line<'static>> {
    // Verify-panel finding: the empty case is the ONLY live case today
    // (no membership producer) — say so, matching the incidence/adjacency
    // siblings' convention, never a blank line.
    if payload.nodes.is_empty() {
        return vec![Line::from(Span::styled(
            "no paoh data",
            Style::new().fg(DIM),
        ))];
    }
    let row_of: BTreeMap<&str, usize> = payload
        .nodes
        .iter()
        .enumerate()
        .map(|(row, node)| (node.as_str(), row))
        .collect();
    let spans: Vec<(usize, usize)> = payload
        .edges
        .iter()
        .map(|edge| {
            let mut rows: Vec<usize> = edge
                .members
                .iter()
                .filter_map(|member| row_of.get(member.as_str()).copied())
                .collect();
            rows.sort_unstable();
            let lo = rows.first().copied().unwrap_or(0);
            let hi = rows.last().copied().unwrap_or(0);
            (lo, hi)
        })
        .collect();

    let mut header: Vec<Span<'static>> = vec![Span::raw(" ".repeat(11))];
    for (index, edge) in payload.edges.iter().enumerate() {
        if index > 0 {
            header.push(Span::raw(" "));
        }
        let label = match edge.formation_tick {
            Some(tick) => format!("t{:<3}", tick),
            None => format!("t{:<3}", "?"),
        };
        header.push(Span::styled(label, Style::new().fg(BONE)));
    }
    let mut lines = vec![Line::from(header)];

    for (row, node) in payload.nodes.iter().enumerate() {
        let mut cells: Vec<Span<'static>> = vec![Span::styled(
            format!("{:<10} ", node),
            Style::new().fg(BONE),
        )];
        for (edge, (lo, hi)) in payload.edges.iter().zip(spans.iter()) {
            let is_member = edge.members.iter().any(|member| member == node);
            let (glyph, style) = if is_member {
                ("●   ", Style::new().fg(GOLD).add_modifier(Modifier::BOLD))
            } else if *lo < row && row < *hi {
                ("│   ", Style::new().fg(CRIMSON))
            } else {
                ("·   ", Style::new().fg(PANEL))
            };
            cells.push(Span::styled(glyph, style));
        }
        lines.push(Line::from(cells));
    }
    lines
}

/// Render an `egotree` payload as a depth-2 bipartite ego-tree — a
/// byte-faithful port of `babylon.tui.topology.egotree::render_egotree`
/// (`topology/egotree.py:84-109`) over the §1 envelope shape.
///
/// Glyphs: root bold [`GOLD`] + `(side)` [`DIM`]; depth-1 branch glyphs
/// (`├── `/`└── `) [`CRIMSON`], depth-1 node ids [`BONE`]; depth-2
/// prefix+branch glyphs (`│   `/`    ` + `├── `/`└── `, painted as ONE
/// span) [`PANEL`], depth-2 neighbor ids [`DIM`]. Depth is hard-capped at
/// 2 by the payload's own bipartite shape (Power-of-10 rule 2) — both
/// loops below bound on a real `Vec::len`, never a counter that could be
/// raised.
#[must_use]
pub fn render_egotree(payload: &EgotreePayload) -> Vec<Line<'static>> {
    let mut lines = vec![Line::from(vec![
        Span::styled(
            payload.root_id.clone(),
            Style::new().fg(GOLD).add_modifier(Modifier::BOLD),
        ),
        Span::raw(" "),
        Span::styled(format!("({})", payload.root_side), Style::new().fg(DIM)),
    ])];

    let total_children = payload.children.len();
    for (index, child) in payload.children.iter().enumerate() {
        let is_last_child = index + 1 == total_children;
        let branch = if is_last_child {
            "└── "
        } else {
            "├── "
        };
        lines.push(Line::from(vec![
            Span::styled(branch, Style::new().fg(CRIMSON)),
            Span::styled(child.node_id.clone(), Style::new().fg(BONE)),
        ]));

        let prefix = if is_last_child { "    " } else { "│   " };
        let total_neighbors = child.neighbors.len();
        for (n_index, neighbor) in child.neighbors.iter().enumerate() {
            let is_last_neighbor = n_index + 1 == total_neighbors;
            let sub_branch = if is_last_neighbor {
                "└── "
            } else {
                "├── "
            };
            lines.push(Line::from(vec![
                Span::styled(format!("{prefix}{sub_branch}"), Style::new().fg(PANEL)),
                Span::styled(neighbor.clone(), Style::new().fg(DIM)),
            ]));
        }
    }
    lines
}

/// The fixed cell width every column shares in an incidence/adjacency
/// grid: the longest label, +1 gap (`matrix.py::_column_width`). `1` for
/// an empty label set — a matrix with zero columns still needs a defined,
/// if unused, width.
fn column_width(labels: &[String]) -> usize {
    labels
        .iter()
        .map(|label| label.chars().count())
        .max()
        .map_or(1, |max| max + 1)
}

/// The row-label column's width: the longest node id, or `1` when there
/// are no nodes (`matrix.py`'s own `default=1`).
fn row_label_width(nodes: &[String]) -> usize {
    nodes
        .iter()
        .map(|node| node.chars().count())
        .max()
        .unwrap_or(1)
}

/// The shared column-header line (`matrix.py::_header_row`):
/// `row_label_width + 1` leading spaces, then every label [`BONE`],
/// left-padded to `col_width`. Shared by [`render_incidence`] (hyperedge
/// labels) and [`render_adjacency`] (node labels), mirroring
/// `matrix.py`'s own one-function-two-callers split.
fn header_row(row_label_width: usize, col_labels: &[String], col_width: usize) -> Line<'static> {
    let mut spans = vec![Span::raw(" ".repeat(row_label_width + 1))];
    for label in col_labels {
        spans.push(Span::styled(
            format!("{:<w$}", label, w = col_width),
            Style::new().fg(BONE),
        ));
    }
    Line::from(spans)
}

/// Render an `incidence` payload as a node × hyperedge cell-art grid — a
/// byte-faithful port of `render_incidence_matrix`
/// (`topology/matrix.py:57-87`) over the §1 envelope shape.
///
/// Glyphs: header/row labels [`BONE`]; present cell `●` bold [`GOLD`];
/// absent cell `·` [`PANEL`]. An empty grid (`nodes` empty) renders the
/// header line alone plus the exact `"no incidence data"` [`DIM`] line
/// (`matrix.py`'s own honest-absence wording) rather than a blank grid.
#[must_use]
pub fn render_incidence(payload: &IncidencePayload) -> Vec<Line<'static>> {
    let col_width = column_width(&payload.hyperedges);
    let row_width = row_label_width(&payload.nodes);
    let mut lines = vec![header_row(row_width, &payload.hyperedges, col_width)];
    if payload.nodes.is_empty() {
        lines.push(Line::from(Span::styled(
            "no incidence data",
            Style::new().fg(DIM),
        )));
        return lines;
    }
    // Python's `zip(..., strict=True)` semantics preserved through the
    // port (verify-panel finding): a shape mismatch renders LOUD, never
    // a silently truncated grid.
    if payload.cells.len() != payload.nodes.len()
        || payload
            .cells
            .iter()
            .any(|row| row.len() != payload.hyperedges.len())
    {
        return vec![Line::from(Span::styled(
            "▌ topology UNREADABLE — incidence grid shape mismatch",
            Style::new().fg(CRIMSON),
        ))];
    }
    for (node, row) in payload.nodes.iter().zip(payload.cells.iter()) {
        let mut spans = vec![Span::styled(
            format!("{:<w$} ", node, w = row_width),
            Style::new().fg(BONE),
        )];
        for present in row {
            let (glyph, style) = if *present {
                ("●", Style::new().fg(GOLD).add_modifier(Modifier::BOLD))
            } else {
                ("·", Style::new().fg(PANEL))
            };
            spans.push(Span::styled(format!("{:<w$}", glyph, w = col_width), style));
        }
        lines.push(Line::from(spans));
    }
    lines
}

/// Render an `adjacency` payload as a node × node cell-art grid — a
/// byte-faithful port of `render_adjacency_matrix`
/// (`topology/matrix.py:90-121`) over the §1 envelope shape.
///
/// Glyphs: header/row labels [`BONE`]; adjacent cell `●` bold [`GOLD`];
/// non-adjacent cell `·` [`PANEL`]; the diagonal `—` [`DIM`] (self-
/// adjacency is not a meaningful quantity, distinct from "not adjacent" —
/// never a false `·`). An empty grid renders the header line alone plus
/// the exact `"no adjacency data"` [`DIM`] line.
#[must_use]
pub fn render_adjacency(payload: &AdjacencyPayload) -> Vec<Line<'static>> {
    let col_width = column_width(&payload.nodes);
    let row_width = row_label_width(&payload.nodes);
    let mut lines = vec![header_row(row_width, &payload.nodes, col_width)];
    if payload.nodes.is_empty() {
        lines.push(Line::from(Span::styled(
            "no adjacency data",
            Style::new().fg(DIM),
        )));
        return lines;
    }
    // `strict=True` parity (verify-panel finding), as in render_incidence.
    if payload.cells.len() != payload.nodes.len()
        || payload
            .cells
            .iter()
            .any(|row| row.len() != payload.nodes.len())
    {
        return vec![Line::from(Span::styled(
            "▌ topology UNREADABLE — adjacency grid shape mismatch",
            Style::new().fg(CRIMSON),
        ))];
    }
    for (row_index, (node, row)) in payload.nodes.iter().zip(payload.cells.iter()).enumerate() {
        let mut spans = vec![Span::styled(
            format!("{:<w$} ", node, w = row_width),
            Style::new().fg(BONE),
        )];
        for (col_index, adjacent) in row.iter().enumerate() {
            let (glyph, style) = if row_index == col_index {
                ("—", Style::new().fg(DIM))
            } else if *adjacent {
                ("●", Style::new().fg(GOLD).add_modifier(Modifier::BOLD))
            } else {
                ("·", Style::new().fg(PANEL))
            };
            spans.push(Span::styled(format!("{:<w$}", glyph, w = col_width), style));
        }
        lines.push(Line::from(spans));
    }
    lines
}

// ── The chrome-owned view (contract §3/§6) — the integration layer over ──
// Lane B's payload/render surface and Lane C's scene3d/camera surface.

/// Which topology payload kind the glyph floor is showing (contract §1's
/// four-kind vocabulary; cycle order = the `g` key's rotation).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TopologyGlyphKind {
    Paoh,
    Egotree,
    Incidence,
    Adjacency,
}

impl TopologyGlyphKind {
    /// The wire value for `topology_json`'s `kind` argument.
    pub fn wire(self) -> &'static str {
        match self {
            Self::Paoh => "paoh",
            Self::Egotree => "egotree",
            Self::Incidence => "incidence",
            Self::Adjacency => "adjacency",
        }
    }

    /// The `g` key's cycle (contract §9 deviation: kind cycling was not
    /// ruled in §6; `g` is the recorded addition).
    pub fn next(self) -> Self {
        match self {
            Self::Paoh => Self::Egotree,
            Self::Egotree => Self::Incidence,
            Self::Incidence => Self::Adjacency,
            Self::Adjacency => Self::Paoh,
        }
    }
}

/// The pane's display mode. The 3D lane (BD-4's release-blocking half)
/// is the default where the `raster` feature is compiled in — the glyph
/// floor stays one `g` away (ADR097: Tier 0 carries full parity).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TopologyMode {
    /// 3D hypergraph (members + community hulls).
    Hyper3d,
    /// 3D contradiction-field surface.
    Surface3d,
    /// The 2D glyph floor (the four §1 kinds).
    Glyph2d,
}

/// What the app shell must do after a topology keypress.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TopologyAction {
    /// Nothing further — the view mutated its own state only.
    Handled,
    /// The kind/mode changed such that the host must be re-queried
    /// (`topology_json`/`field_state_json`) before the next frame.
    NeedsRefresh,
    /// Not a topology key — fall through to the next handler.
    NotHandled,
}

/// The chrome-owned topology pane state (contract §3: pane switching is
/// chrome-internal, so this lives on `PlayChrome`, never the view stack).
#[derive(Debug, Default)]
pub struct TopologyView {
    /// The glyph floor's current payload kind.
    pub kind: Option<TopologyGlyphKind>,
    /// The last `topology_json` payload, parsed; `None` = honest absence
    /// (unbound session, egotree with no focus, or never fetched).
    pub payload: Option<TopologyPayload>,
    /// The last fetch returned unparseable non-null JSON — render LOUD.
    pub payload_failed: bool,
    /// The last `field_state_json` payload, parsed (surface mode's feed).
    pub field_state: Option<serde_json::Value>,
    /// The last `field_state_json` reply was unparseable — render LOUD
    /// (III.11: an error is never indistinguishable from honest absence).
    pub field_state_failed: bool,
    /// Display mode; `None` = pick the default on first entry.
    pub mode: Option<TopologyMode>,
    /// The `f` key's field-cycle index (surface mode).
    pub field_idx: usize,
    /// Glyph-floor vertical scroll (Up/Down in `Glyph2d`; reset on `g`).
    pub scroll: u16,
    #[cfg(feature = "raster")]
    /// Camera state (contract §6: discrete, deterministic, client-only).
    pub camera: crate::scene3d::CameraState,
}

impl TopologyView {
    /// The mode the pane opens in: 3D hypergraph where the raster lane is
    /// compiled, the glyph floor otherwise.
    fn default_mode() -> TopologyMode {
        #[cfg(feature = "raster")]
        {
            TopologyMode::Hyper3d
        }
        #[cfg(not(feature = "raster"))]
        {
            TopologyMode::Glyph2d
        }
    }

    /// Current mode, materializing the default on first read.
    pub fn mode(&mut self) -> TopologyMode {
        *self.mode.get_or_insert_with(Self::default_mode)
    }

    /// Current glyph kind, defaulting to `paoh` (the hypergraph's own
    /// data source, so 3D and the default floor share one payload).
    pub fn glyph_kind(&mut self) -> TopologyGlyphKind {
        *self.kind.get_or_insert(TopologyGlyphKind::Paoh)
    }

    /// The `topology_json` args for the current fetch. `focus` is the
    /// wiki's current subject — egotree's root (§1: REQUIRED for
    /// egotree, ignored for the rest), NAMESPACE-STRIPPED at this seam
    /// (the wiki hands vault paths like `social_class/C001`; the levi
    /// root wants the bare `C001` — verify-panel finding).
    ///
    /// 3D hypergraph mode ALWAYS fetches `paoh` (its only render source)
    /// regardless of where the glyph cursor sits — otherwise `g,g,s`
    /// left the pane permanently, falsely absent (verify-panel finding).
    pub fn args_json(&mut self, focus: Option<&str>) -> String {
        let kind = if self.mode() == TopologyMode::Hyper3d {
            TopologyGlyphKind::Paoh
        } else {
            self.glyph_kind()
        };
        let bare = focus.map(|f| f.rsplit('/').next().unwrap_or(f));
        serde_json::json!({"kind": kind.wire(), "focus": bare}).to_string()
    }

    /// Ingest a `topology_json` reply (`"null"` = honest absence).
    pub fn ingest_topology(&mut self, raw: &str) {
        self.payload_failed = false;
        match serde_json::from_str::<Option<TopologyPayload>>(raw) {
            Ok(parsed) => self.payload = parsed,
            Err(_) => {
                self.payload = None;
                self.payload_failed = true;
            }
        }
    }

    /// Ingest a `field_state_json` reply (`"null"` = honest absence; a
    /// PARSE FAILURE is recorded loudly, never collapsed into absence —
    /// III.11, verify-panel finding).
    pub fn ingest_field_state(&mut self, raw: &str) {
        self.field_state_failed = false;
        match serde_json::from_str::<Option<serde_json::Value>>(raw) {
            Ok(parsed) => self.field_state = parsed,
            Err(_) => {
                self.field_state = None;
                self.field_state_failed = true;
            }
        }
    }

    /// Handle a topology-pane keypress (contract §6 + the `g` cycle).
    /// Chrome-global keys (Tab, digits, Esc) never reach here — the app
    /// shell's own arms win first.
    pub fn handle_key(&mut self, code: KeyCode) -> TopologyAction {
        let in_3d = self.mode() != TopologyMode::Glyph2d;
        match code {
            KeyCode::Char('s') => {
                let next = match self.mode() {
                    TopologyMode::Hyper3d => TopologyMode::Surface3d,
                    TopologyMode::Surface3d => TopologyMode::Hyper3d,
                    TopologyMode::Glyph2d => TopologyMode::Hyper3d,
                };
                self.mode = Some(next);
                TopologyAction::NeedsRefresh
            }
            KeyCode::Char('g') => {
                if self.mode() == TopologyMode::Glyph2d {
                    self.kind = Some(self.glyph_kind().next());
                } else {
                    self.mode = Some(TopologyMode::Glyph2d);
                }
                self.scroll = 0;
                TopologyAction::NeedsRefresh
            }
            KeyCode::Char('f') if in_3d => {
                self.field_idx = self.field_idx.wrapping_add(1);
                TopologyAction::Handled
            }
            // Glyph floor: Up/Down scroll a grid taller than the pane
            // (verify-panel finding — without this, tall PAOH grids were
            // unreachable and the camera keys mutated invisible state).
            KeyCode::Up if !in_3d => {
                self.scroll = self.scroll.saturating_sub(1);
                TopologyAction::Handled
            }
            KeyCode::Down if !in_3d => {
                self.scroll = self.scroll.saturating_add(1);
                TopologyAction::Handled
            }
            #[cfg(feature = "raster")]
            KeyCode::Left if in_3d => {
                self.camera.step_ry(-1.0);
                TopologyAction::Handled
            }
            #[cfg(feature = "raster")]
            KeyCode::Right if in_3d => {
                self.camera.step_ry(1.0);
                TopologyAction::Handled
            }
            #[cfg(feature = "raster")]
            KeyCode::Up if in_3d => {
                self.camera.step_rx(-1.0);
                TopologyAction::Handled
            }
            #[cfg(feature = "raster")]
            KeyCode::Down if in_3d => {
                self.camera.step_rx(1.0);
                TopologyAction::Handled
            }
            #[cfg(feature = "raster")]
            KeyCode::Char('+') | KeyCode::Char('=') if in_3d => {
                self.camera.step_dist(-1.0);
                TopologyAction::Handled
            }
            #[cfg(feature = "raster")]
            KeyCode::Char('-') if in_3d => {
                self.camera.step_dist(1.0);
                TopologyAction::Handled
            }
            #[cfg(feature = "raster")]
            KeyCode::Char('0') if in_3d => {
                self.camera.reset();
                TopologyAction::Handled
            }
            _ => TopologyAction::NotHandled,
        }
    }

    /// Render the pane into `area`.
    pub fn render(&mut self, frame: &mut Frame<'_>, area: Rect) {
        // III.11 (verify-panel finding): a malformed host reply renders
        // the CRIMSON UNREADABLE line in EVERY mode — hoisted here so no
        // mode can launder a parse failure into honest absence.
        let unreadable = match self.mode() {
            TopologyMode::Surface3d => self.field_state_failed,
            _ => self.payload_failed,
        };
        if unreadable {
            let block = Block::bordered().title("topology");
            let inner = block.inner(area);
            frame.render_widget(block, area);
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    "▌ topology UNREADABLE — malformed host data",
                    Style::new().fg(CRIMSON),
                ))),
                inner,
            );
            return;
        }
        match self.mode() {
            TopologyMode::Glyph2d => self.render_glyph(frame, area),
            TopologyMode::Hyper3d => self.render_hyper(frame, area),
            TopologyMode::Surface3d => self.render_surface(frame, area),
        }
    }

    fn render_glyph(&mut self, frame: &mut Frame<'_>, area: Rect) {
        let kind = self.glyph_kind();
        let title = format!("topology — {} (g cycles, s for 3D)", kind.wire());
        let block = Block::bordered().title(title);
        let inner = block.inner(area);
        frame.render_widget(block, area);
        let lines = if self.payload_failed {
            vec![Line::from(Span::styled(
                "▌ topology UNREADABLE — malformed host data",
                Style::new().fg(CRIMSON),
            ))]
        } else {
            match &self.payload {
                Some(payload) => payload.render(),
                None => vec![Line::from(Span::styled(
                    "▌ no topology recorded — for egotree, open a subject in the wiki first",
                    Style::new().fg(DIM),
                ))],
            }
        };
        frame.render_widget(Paragraph::new(lines).scroll((self.scroll, 0)), inner);
    }

    #[cfg(not(feature = "raster"))]
    fn render_hyper(&mut self, frame: &mut Frame<'_>, area: Rect) {
        self.render_no_raster(frame, area);
    }

    #[cfg(not(feature = "raster"))]
    fn render_surface(&mut self, frame: &mut Frame<'_>, area: Rect) {
        self.render_no_raster(frame, area);
    }

    #[cfg(not(feature = "raster"))]
    fn render_no_raster(&mut self, frame: &mut Frame<'_>, area: Rect) {
        // The honest-absence fence for a build without the 3D lane
        // (never shipped: the wheel forwards `raster` unconditionally).
        let block = Block::bordered().title("topology");
        let inner = block.inner(area);
        frame.render_widget(block, area);
        frame.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "▌ 3D lane not compiled (raster feature) — press 'g' for the glyph floor",
                Style::new().fg(CRIMSON),
            ))),
            inner,
        );
    }

    #[cfg(feature = "raster")]
    fn render_hyper(&mut self, frame: &mut Frame<'_>, area: Rect) {
        // Verify-panel BLOCKER: an EMPTY-but-present paoh payload must
        // render honest absence naming the real cause, never a blank
        // raster — today the engine has NO community_memberships
        // producer (seam registry: STRUCTURALLY_IMPOSSIBLE), so empty is
        // the live steady state until that producer lands.
        if let Some(TopologyPayload::Paoh(paoh)) = &self.payload {
            if paoh.edges.is_empty() || paoh.layout.is_empty() {
                let block =
                    Block::bordered().title("topology — hypergraph 3D (s: surface, g: glyphs)");
                let inner = block.inner(area);
                frame.render_widget(block, area);
                frame.render_widget(
                    Paragraph::new(Line::from(Span::styled(
                        "▌ no community hyperedges attributed — the membership producer has not landed",
                        Style::new().fg(DIM),
                    ))),
                    inner,
                );
                return;
            }
        }
        let Some(TopologyPayload::Paoh(paoh)) = &self.payload else {
            // 3D renders off the paoh payload; anything else is absence.
            let block = Block::bordered().title("topology — hypergraph 3D (s: surface, g: glyphs)");
            let inner = block.inner(area);
            frame.render_widget(block, area);
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    "▌ no hypergraph recorded yet — advance a tick",
                    Style::new().fg(DIM),
                ))),
                inner,
            );
            return;
        };
        let mut nodes: Vec<(String, [f64; 2], f64, hypergraph_rs::raster::Rgb)> = Vec::new();
        let member_ids: std::collections::BTreeSet<&str> = paoh
            .edges
            .iter()
            .flat_map(|e| e.members.iter().map(String::as_str))
            .collect();
        let mut layout: Vec<(&String, &[f64; 2])> = paoh.layout.iter().collect();
        layout.sort_by(|a, b| a.0.cmp(b.0));
        for (id, xy) in layout {
            let is_member = member_ids.contains(id.as_str());
            let (radius, color) = if is_member {
                (0.045, rgb_of(BONE))
            } else {
                (0.075, rgb_of(GOLD))
            };
            nodes.push((id.clone(), *xy, radius, color));
        }
        let hulls: Vec<(Vec<String>, hypergraph_rs::raster::Rgb)> = paoh
            .edges
            .iter()
            .map(|e| (e.members.clone(), rgb_of(CRIMSON)))
            .collect();
        let struts: Vec<(String, String)> = paoh
            .edges
            .iter()
            .flat_map(|e| {
                e.members
                    .iter()
                    .map(|m| (m.clone(), e.community_id.clone()))
            })
            .collect();
        let scene = crate::scene3d::hypergraph_scene(&nodes, &hulls, &struts);
        self.blit_scene(
            frame,
            area,
            &scene,
            "topology — hypergraph 3D (arrows rotate, +/- zoom, s: surface, g: glyphs)",
        );
    }

    #[cfg(feature = "raster")]
    fn render_surface(&mut self, frame: &mut Frame<'_>, area: Rect) {
        let title = "topology — contradiction field (arrows rotate, f: field, s: hypergraph)";
        let Some(field) = &self.field_state else {
            let block = Block::bordered().title(title);
            let inner = block.inner(area);
            frame.render_widget(block, area);
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    "▌ no field state recorded yet — advance a tick",
                    Style::new().fg(DIM),
                ))),
                inner,
            );
            return;
        };
        // §2's client-side join: unit circle over the sorted node_ids,
        // scalar = the cycled field name (default: the principal field).
        let nodes = field
            .get("nodes")
            .and_then(|n| n.as_array())
            .cloned()
            .unwrap_or_default();
        let mut ids: Vec<(String, &serde_json::Value)> = Vec::new();
        for node in &nodes {
            if let Some(id) = node.get("node_id").and_then(|v| v.as_str()) {
                ids.push((id.to_string(), node));
            }
        }
        ids.sort_by(|a, b| a.0.cmp(&b.0));
        let mut field_names: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        for (_, node) in &ids {
            if let Some(fields) = node.get("fields").and_then(|f| f.as_object()) {
                field_names.extend(fields.keys().cloned());
            }
        }
        let names: Vec<String> = field_names.into_iter().collect();
        let selected = if names.is_empty() {
            None
        } else {
            let principal = field
                .get("principal_field")
                .and_then(|p| p.get("field_name"))
                .and_then(|v| v.as_str());
            let base = principal
                .and_then(|p| names.iter().position(|n| n == p))
                .unwrap_or(0);
            Some(names[(base + self.field_idx) % names.len()].clone())
        };
        let mut samples: Vec<(f64, f64, f64)> = Vec::new();
        let mut skipped = 0usize;
        if let Some(name) = &selected {
            let count = ids.len().max(1) as f64;
            for (i, (_, node)) in ids.iter().enumerate() {
                let angle = (i as f64) / count * std::f64::consts::TAU;
                // A node contributes only fields it actually carries —
                // never a fabricated zero (FieldStateNodeView's own
                // contract; verify-panel finding).
                let Some(scalar) = node
                    .get("fields")
                    .and_then(|f| f.get(name))
                    .and_then(|v| v.as_f64())
                else {
                    skipped += 1;
                    continue;
                };
                samples.push((angle.cos(), angle.sin(), scalar));
            }
        }
        if samples.is_empty() {
            // Verify-panel BLOCKER class: zero surviving samples must be
            // honest absence, never a blank raster.
            let block = Block::bordered().title(title);
            let inner = block.inner(area);
            frame.render_widget(block, area);
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    "▌ no field values recorded for any class yet — advance a tick",
                    Style::new().fg(DIM),
                ))),
                inner,
            );
            return;
        }
        let scene = crate::scene3d::field_surface(&samples, (32, 24));
        // Name honesty (verify-panel): at early ticks principal_field is
        // None and the cycle degrades to the alphabetically-first field —
        // say so instead of implying a principal ruling.
        let principal_known = field
            .get("principal_field")
            .and_then(|p| p.get("field_name"))
            .and_then(|v| v.as_str())
            .is_some();
        let full_title = match &selected {
            Some(name) if principal_known && skipped == 0 => format!("{title} [{name}]"),
            Some(name) if principal_known => format!("{title} [{name} — {skipped} classes absent]"),
            Some(name) => format!("{title} [{name} — no principal field yet]"),
            None => title.to_string(),
        };
        self.blit_scene(frame, area, &scene, &full_title);
    }

    #[cfg(feature = "raster")]
    fn blit_scene(
        &mut self,
        frame: &mut Frame<'_>,
        area: Rect,
        scene: &hypergraph_rs::raster::SceneGraph3D,
        title: &str,
    ) {
        let block = Block::bordered().title(title.to_string());
        let inner = block.inner(area);
        frame.render_widget(block, area);
        if inner.width == 0 || inner.height == 0 {
            return;
        }
        let grid = hypergraph_rs::raster::rasterize(
            scene,
            &self.camera.camera(),
            inner.width,
            inner.height,
        );
        crate::raster_bridge::blit_rect(&grid, frame.buffer_mut(), inner);
    }
}

/// Extract the `(r, g, b)` of a `theme.rs` constant for the raster lane.
#[cfg(feature = "raster")]
fn rgb_of(color: ratatui::style::Color) -> hypergraph_rs::raster::Rgb {
    match color {
        ratatui::style::Color::Rgb(r, g, b) => hypergraph_rs::raster::Rgb(r, g, b),
        // Theme constants are always Rgb literals (the parity guard's
        // regex contract); anything else is a programmer error.
        _ => hypergraph_rs::raster::Rgb(232, 232, 232),
    }
}

#[cfg(test)]
mod view_state_tests {
    use super::*;

    /// Verify-panel MAJOR: `4, g, g, s` used to leave the 3D pane
    /// permanently absent — 3D mode must ALWAYS fetch `paoh`.
    #[test]
    fn returning_to_3d_after_glyph_cycling_fetches_paoh() {
        let mut view = TopologyView::default();
        let _ = view.mode(); // pane entry materializes the default mode
        assert_eq!(
            view.handle_key(KeyCode::Char('g')),
            TopologyAction::NeedsRefresh
        );
        assert_eq!(
            view.handle_key(KeyCode::Char('g')),
            TopologyAction::NeedsRefresh
        );
        assert_eq!(
            view.handle_key(KeyCode::Char('s')),
            TopologyAction::NeedsRefresh
        );
        let args = view.args_json(None);
        assert!(
            args.contains("\"kind\":\"paoh\""),
            "3D mode must fetch paoh regardless of the glyph cursor: {args}"
        );
    }

    /// Verify-panel MAJOR: the wiki hands NAMESPACED vault subjects; the
    /// levi root wants the bare id.
    #[test]
    fn egotree_focus_is_namespace_stripped() {
        let mut view = TopologyView {
            mode: Some(TopologyMode::Glyph2d),
            kind: Some(TopologyGlyphKind::Egotree),
            ..TopologyView::default()
        };
        let args = view.args_json(Some("social_class/C001"));
        assert!(
            args.contains("\"focus\":\"C001\""),
            "namespaced focus must strip to the bare id: {args}"
        );
    }

    /// Verify-panel MAJOR (III.11): a malformed field-state reply is
    /// recorded loudly, never collapsed into honest absence.
    #[test]
    fn malformed_field_state_sets_the_loud_flag() {
        let mut view = TopologyView::default();
        view.ingest_field_state("not json");
        assert!(view.field_state_failed);
        assert!(view.field_state.is_none());
        view.ingest_field_state("null");
        assert!(!view.field_state_failed, "honest null clears the flag");
    }

    /// Glyph-floor scroll keys are mode-local (verify-panel NIT): in 3D
    /// they rotate the camera; in Glyph2d they scroll.
    #[test]
    fn glyph_mode_arrows_scroll_not_rotate() {
        let mut view = TopologyView {
            mode: Some(TopologyMode::Glyph2d),
            ..TopologyView::default()
        };
        assert_eq!(view.handle_key(KeyCode::Down), TopologyAction::Handled);
        assert_eq!(view.scroll, 1);
        assert_eq!(view.handle_key(KeyCode::Up), TopologyAction::Handled);
        assert_eq!(view.scroll, 0);
    }
}
