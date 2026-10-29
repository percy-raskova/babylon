//! AST sentinel for the Google Rust Style Guide rules that no formatter or
//! Clippy lint can express: module layout, import shape, inline qualified
//! types, shared pointers, exception markers, hex literal casing, macro-body
//! import uses, and report-only bool-parameter payloads.
//!
//! `docs/agents/rust-style.md` is the governed specification. The check joins
//! the default `all` set; `bsl-lint google-rust-style <path>` also runs it by
//! name over one path.
//!
//! Three deliberate scopes keep the rules honest: the default filesystem walk
//! skips `fixtures` directories (they hold intentionally non-conforming test
//! data), a top-level `fn main` is not an API definition because Cargo
//! requires it in the crate root, and a bool-parameter or bool-payload finding
//! is `Warn` (printed, never gating) until its enum conversion lands. Explicit
//! paths are still checked exactly.

use crate::finding::{Finding, Severity};
use crate::repo::Repo;
use proc_macro2::{Delimiter, Group, TokenStream, TokenTree};
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{
    Arm, Attribute, Block, Expr, ExprClosure, ExprForLoop, ExprIf, ExprLet, ExprPath, ExprWhile,
    Field, Fields, FnArg, GenericArgument, ImplItemFn, Item, ItemEnum, ItemFn, ItemMod, ItemStruct,
    ItemUse, LitInt, Local, Macro, Meta, Pat, PatIdent, Path as SynPath, PathArguments, Signature,
    TraitItemFn, Type, TypePath, UseGlob, UseTree, Visibility,
};

/// The CLI name of this check.
pub const CHECK: &str = "google-rust-style";

const EXC_04: &str = "STYLE-EXCEPTION(EXC-04";
const EXC_05: &str = "STYLE-EXCEPTION(EXC-05";
const MARKER_LOOKBACK: usize = 2;
const MAX_WALK_DEPTH: usize = 32;

/// The EXC-04 register's file paths, relative to the repository root.
/// `docs/agents/rust-style.md` owns the table; this list mirrors it, and a new
/// retained shared pointer needs both entries in one commit.
const EXC_04_REGISTERED_FILES: &[&str] = &[
    "rust/crates/babylon-kernel/src/geography/roster.rs",
    "rust/crates/babylon-tick/src/material_world/register.rs",
    "rust/crates/babylon-persistence/src/economic_content.rs",
    "rust/crates/babylon-persistence/src/state_storage/register.rs",
    "rust/crates/babylon-persistence/src/observer_material/snapshot.rs",
    "rust/crates/babylon-persistence/src/economic_catalog/sources.rs",
    "rust/crates/babylon-persistence/src/archive_worker.rs",
    "rust/crates/babylon-client/src/logging.rs",
    "rust/crates/babylon-persistence/examples/michigan_experiment/artifacts.rs",
    "rust/crates/babylon-persistence/src/runtime_session/coordinator/tests/support.rs",
    "rust/crates/babylon-persistence/tests/observer_material_live/runtime_process.rs",
];

/// The EXC-05 register's file paths: only these two byte tables may skip
/// `rustfmt`. `docs/agents/rust-style.md` owns the matching table.
const EXC_05_REGISTERED_FILES: &[&str] = &[
    "rust/crates/babylon-graph/src/state_hash.rs",
    "rust/crates/babylon-tick/src/world_hash.rs",
];

/// The bool-parameter sites Task 9 deferred to the follow-up enum
/// conversions. Each entry is `(owner, parameter)`; `"0"` names the single
/// unnamed field of an enum variant. Removing an entry is part of converting
/// that site, never a separate style change.
const DEFERRED_BOOL_PARAMETERS: &[(&str, &str)] = &[
    ("CycleGood", "0"),
    ("step_selection", "backwards"),
    ("adjacent", "forward"),
    ("evidence_neighbor", "next"),
    ("move_evidence", "next"),
    ("paint_layout", "primary"),
];

/// Enum variants that carry a bool payload and already name their own type at
/// every construction site, so the guide's call-site-obviousness concern does
/// not apply. `Bool` is the BSL value model's canonical boolean constant.
const SELF_DESCRIBING_BOOL_PAYLOADS: &[&str] = &["Bool"];

/// The explicit Task 11 grandfather register for direct free-function imports
/// whose every use sits inside a macro token stream (the AST visitor cannot
/// see those uses). Format: `file|module|name[,name]`; `#` starts a comment.
/// The register may only SHRINK — fixing a site removes its line in the same
/// commit, and a new macro-only direct import is a gating finding.
const RESIDUAL_MACRO_IMPORTS: &str = include_str!("../data/google_rust_style_macro_residual.txt");

/// Pinned data-line count of [`RESIDUAL_MACRO_IMPORTS`]; changing the register
/// requires changing this number, which keeps every edit reviewed.
const RESIDUAL_MACRO_IMPORT_LINES: usize = 136;

/// A lowercase leaf imported from a module, pending confirmation that the file
/// calls it as a free function.
#[derive(Clone)]
struct ImportCandidate {
    name: String,
    line: usize,
    rendered: String,
    path: Vec<String>,
    scope: Vec<String>,
    lexical: Vec<usize>,
}

/// An inline `module::Type` reference that should normally be imported instead.
struct QualifiedSite {
    prefix: String,
    suffix: String,
    line: usize,
    rendered: String,
}

/// The source lines a comment marker search reads.
struct SourceLines<'a> {
    lines: Vec<&'a str>,
}

impl<'a> SourceLines<'a> {
    fn new(source: &'a str) -> Self {
        Self {
            lines: source.lines().collect(),
        }
    }

    /// Whether `marker` appears on `line`, `line - 1`, or `line - 2`.
    fn has_marker(&self, line: usize, marker: &str, lookback: usize) -> bool {
        for offset in 0..=lookback {
            let Some(index) = line
                .checked_sub(offset)
                .and_then(|value| value.checked_sub(1))
            else {
                continue;
            };
            if let Some(text) = self.lines.get(index) {
                if text.contains(marker) {
                    return true;
                }
            }
        }
        false
    }
}

/// The AST visitor accumulates findings plus the two facts that need a whole
/// file before they can be judged: which lowercase imports are actually called,
/// and whether a qualified type name has more than one owner.
struct StyleVisitor<'a> {
    file: String,
    non_leaf: bool,
    in_client_crate: bool,
    module_stack: Vec<bool>,
    scope: Vec<String>,
    lexical: Vec<usize>,
    next_scope: usize,
    local_fns: BTreeMap<Vec<String>, BTreeSet<String>>,
    fn_depth: usize,
    item_depth: usize,
    lines: SourceLines<'a>,
    findings: Vec<Finding>,
    imports: Vec<ImportCandidate>,
    used_names: BTreeSet<(Vec<String>, Vec<usize>, String)>,
    macro_used_names: BTreeSet<(Vec<String>, Vec<usize>, String)>,
    bindings: Vec<BTreeSet<String>>,
    owner: Option<String>,
    method: Option<String>,
    byte_table: bool,
    field_index: usize,
    field_name: Option<String>,
    seen_arc_sites: BTreeSet<String>,
    imported_types: BTreeSet<String>,
    qualified: BTreeMap<(String, String), QualifiedSite>,
}

impl<'a> StyleVisitor<'a> {
    fn new(file: String, non_leaf: bool, in_client_crate: bool, source: &'a str) -> Self {
        Self {
            file,
            non_leaf,
            in_client_crate,
            module_stack: Vec::new(),
            scope: Vec::new(),
            lexical: Vec::new(),
            next_scope: 0,
            local_fns: BTreeMap::new(),
            fn_depth: 0,
            item_depth: 0,
            lines: SourceLines::new(source),
            findings: Vec::new(),
            imports: Vec::new(),
            used_names: BTreeSet::new(),
            macro_used_names: BTreeSet::new(),
            bindings: Vec::new(),
            owner: None,
            method: None,
            byte_table: false,
            field_index: 0,
            field_name: None,
            seen_arc_sites: BTreeSet::new(),
            imported_types: BTreeSet::new(),
            qualified: BTreeMap::new(),
        }
    }

    fn push(&mut self, line: usize, what: impl Into<String>, evidence: impl Into<String>) {
        self.findings.push(Finding {
            check: CHECK,
            file: self.file.clone(),
            line,
            what: what.into(),
            evidence: evidence.into(),
            severity: Severity::Fail,
        });
    }

    /// Report-only finding: printed by the shared output contract, never
    /// flips the check's exit code.
    fn push_warn(&mut self, line: usize, what: impl Into<String>, evidence: impl Into<String>) {
        self.findings.push(Finding {
            check: CHECK,
            file: self.file.clone(),
            line,
            what: what.into(),
            evidence: evidence.into(),
            severity: Severity::Warn,
        });
    }

    fn finish(mut self) -> Vec<Finding> {
        self.finish_imports();
        self.finish_qualified_types();
        sort_findings(&mut self.findings);
        dedup_findings(&mut self.findings);
        self.findings
    }

    fn finish_imports(&mut self) {
        let imports = std::mem::take(&mut self.imports);
        for candidate in &imports {
            if self.name_is_a_local_fn(candidate) {
                // An enclosing module defines the imported local function.
                continue;
            }
            if self.used_names.iter().any(|(scope, lexical, name)| {
                scope.starts_with(&candidate.scope)
                    && lexical.starts_with(&candidate.lexical)
                    && name == &candidate.name
                    && !imports.iter().any(|other| {
                        other.name == *name
                            && scope.starts_with(&other.scope)
                            && lexical.starts_with(&other.lexical)
                            && (other.scope.len(), other.lexical.len())
                                > (candidate.scope.len(), candidate.lexical.len())
                    })
            }) {
                self.push(
                    candidate.line,
                    "free function is imported directly instead of its module",
                    format!(
                        "{} — import the module and call `{}` qualified",
                        candidate.rendered, candidate.name
                    ),
                );
            } else if self.macro_used_names.iter().any(|(scope, lexical, name)| {
                scope.starts_with(&candidate.scope)
                    && lexical.starts_with(&candidate.lexical)
                    && name == &candidate.name
                    && !imports.iter().any(|other| {
                        other.name == *name
                            && scope.starts_with(&other.scope)
                            && lexical.starts_with(&other.lexical)
                            && (other.scope.len(), other.lexical.len())
                                > (candidate.scope.len(), candidate.lexical.len())
                    })
            }) && !residual_macro_import(
                &self.file,
                &candidate.path.join("::"),
                &candidate.name,
            ) {
                self.push(
                    candidate.line,
                    "free function is imported directly and used inside macro bodies",
                    format!(
                        "{} — import the module and qualify each macro call site",
                        candidate.rendered
                    ),
                );
            }
        }
    }

    /// Whether `fn <name>` exists in the import's own module or an enclosing
    /// one. `use super::helper;` inside an inline test module imports a
    /// file-local helper, so it is not a direct third-party import.
    fn name_is_a_local_fn(&self, candidate: &ImportCandidate) -> bool {
        let local_in_ancestors = candidate
            .path
            .first()
            .is_some_and(|first| is_use_keyword(first))
            && (0..=candidate.scope.len()).any(|length| {
                self.local_fns
                    .get(&candidate.scope[..length])
                    .is_some_and(|names| names.contains(&candidate.name))
            });
        let local_in_scope = self
            .local_fns
            .get(&candidate.scope)
            .is_some_and(|names| names.contains(&candidate.name));
        local_in_scope || local_in_ancestors
    }

    fn finish_qualified_types(&mut self) {
        let sites = std::mem::take(&mut self.qualified);
        let mut owners_by_type: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for site in sites.values() {
            owners_by_type
                .entry(site.suffix.clone())
                .or_default()
                .insert(site.prefix.clone());
        }
        for site in sites.into_values() {
            if self.imported_types.contains(&site.suffix) {
                continue;
            }
            let disambiguating = owners_by_type
                .get(&site.suffix)
                .is_some_and(|owners| owners.len() > 1);
            if disambiguating {
                continue;
            }
            self.push(
                site.line,
                "module-qualified type is used inline instead of imported",
                format!(
                    "{} — import `{}` and use the bare type name",
                    site.rendered, site.suffix
                ),
            );
        }
    }

    fn check_top_level_item(&mut self, item: &Item) {
        if !self.non_leaf {
            return;
        }
        let (ident, kind) = match item {
            Item::Fn(item_fn) if item_fn.sig.ident == "main" => {
                // Cargo requires the process entry point in the crate root;
                // it is not an API that can move into a leaf module.
                return;
            }
            Item::Fn(item_fn) => (&item_fn.sig.ident, "a function"),
            Item::Struct(item_struct) => (&item_struct.ident, "a struct"),
            Item::Enum(item_enum) => (&item_enum.ident, "an enum"),
            Item::Trait(item_trait) => (&item_trait.ident, "a trait"),
            Item::Const(item_const) => (&item_const.ident, "a constant"),
            Item::Static(item_static) => (&item_static.ident, "a static"),
            Item::Type(item_type) => (&item_type.ident, "a type alias"),
            Item::Impl(item_impl) => {
                self.push(
                    item_impl.impl_token.span.start().line,
                    "non-leaf module defines an impl block",
                    "move the impl into the leaf module that defines the type",
                );
                return;
            }
            _ => return,
        };
        self.push(
            ident.span().start().line,
            format!("non-leaf module defines {kind}"),
            format!("`{ident}` — move it into a leaf module and re-export it"),
        );
    }

    fn inspect_use_tree(
        &mut self,
        tree: &UseTree,
        prefix: &mut Vec<String>,
        in_group: bool,
        public: bool,
    ) {
        match tree {
            UseTree::Path(path) => {
                let name = path.ident.to_string();
                if in_group {
                    self.push(
                        path.ident.span().start().line,
                        "use path nests `::` inside a brace group",
                        format!(
                            "{} — split it so each brace entry is one module",
                            render_path(
                                prefix,
                                &format!("{name}::{}", render_use_tree(&path.tree))
                            )
                        ),
                    );
                }
                prefix.push(name);
                self.inspect_use_tree(&path.tree, prefix, in_group, public);
                prefix.pop();
            }
            UseTree::Group(group) => {
                for item in &group.items {
                    self.inspect_use_tree(item, prefix, true, public);
                }
            }
            UseTree::Glob(glob) => self.inspect_glob(prefix, glob, public),
            UseTree::Name(name) => {
                let line = name.ident.span().start().line;
                self.inspect_use_leaf(&name.ident.to_string(), None, prefix, line);
            }
            UseTree::Rename(rename) => {
                let alias = rename.rename.to_string();
                let original = rename.ident.to_string();
                let line = rename.rename.span().start().line;
                self.inspect_use_leaf(&alias, Some(&original), prefix, line);
            }
        }
    }

    fn inspect_glob(&mut self, prefix: &[String], glob: &UseGlob, public: bool) {
        if self.glob_allowed(prefix, public) {
            return;
        }
        let what = if public && self.non_leaf && prefix.len() > 1 {
            "public glob re-export is not a single-segment child module"
        } else {
            "glob import is outside the EXC-03 allowances"
        };
        self.push(
            glob.star_token.span().start().line,
            what,
            format!("{} — import the names explicitly", render_path(prefix, "*")),
        );
    }

    fn glob_allowed(&self, prefix: &[String], public: bool) -> bool {
        let bevy_prelude = self.in_client_crate
            && prefix.len() == 2
            && prefix.first().is_some_and(|name| name == "bevy")
            && prefix.get(1).is_some_and(|name| name == "prelude");
        let test_super = self.module_stack.iter().any(|is_test| *is_test)
            && prefix.len() == 1
            && prefix.first().is_some_and(|name| name == "super");
        let local_enum = self.fn_depth > 0
            && prefix.len() == 1
            && prefix.first().is_some_and(|name| is_upper_camel_case(name));
        // EXC-03 keeps `pub use submodule::*` for a non-leaf module, but only
        // for one child module: `crate::`/`self::` prefixes and nested
        // module paths defeat the local re-export audit the allowance needs.
        let public_reexport = public
            && self.non_leaf
            && prefix.len() == 1
            && prefix
                .first()
                .is_some_and(|name| is_module_segment(name) && !is_use_keyword(name));
        bevy_prelude || test_super || local_enum || public_reexport
    }

    fn inspect_use_leaf(
        &mut self,
        name: &str,
        original: Option<&str>,
        prefix: &[String],
        use_line: usize,
    ) {
        if is_upper_camel_case(name) {
            self.imported_types.insert(name.to_owned());
            return;
        }
        if !is_lowercase_identifier(name) || is_use_keyword(name) || prefix.is_empty() {
            return;
        }
        if name.trim_matches('_').is_empty() {
            // `use std::fmt::Write as _;` introduces a trait into scope; it
            // names no callable value.
            return;
        }
        let rendered = match original {
            Some(original) => {
                let imported = render_path(prefix, original);
                format!("{imported} as {name}")
            }
            None => render_path(prefix, name),
        };
        self.imports.push(ImportCandidate {
            name: name.to_owned(),
            line: use_line,
            rendered,
            path: prefix.to_vec(),
            scope: self.scope.clone(),
            lexical: self.lexical.clone(),
        });
    }

    fn inspect_type_path(&mut self, type_path: &TypePath) {
        if type_path.qself.is_some() {
            return;
        }
        let segments = path_segments(&type_path.path);
        if segments.len() < 2 {
            return;
        }
        let Some(last) = segments.last() else {
            return;
        };
        if !is_upper_camel_case(last) {
            return;
        }
        let modules = &segments[..segments.len() - 1];
        if !modules.iter().all(|name| is_module_segment(name)) {
            return;
        }
        let line = type_path.path.span().start().line;
        self.record_qualified(modules.join("::"), last.clone(), line, segments.join("::"));
    }

    fn inspect_expr_path(&mut self, expr_path: &ExprPath) {
        if expr_path.qself.is_some() {
            return;
        }
        self.check_shared_pointer(&expr_path.path);
        self.check_catch_unwind(&expr_path.path);
        let segments = path_segments(&expr_path.path);
        if segments.len() < 3 {
            return;
        }
        let type_index = segments.len() - 2;
        let Some(type_name) = segments.get(type_index) else {
            return;
        };
        if !is_upper_camel_case(type_name) {
            return;
        }
        let modules = &segments[..type_index];
        if modules.is_empty() || !modules.iter().all(|name| is_module_segment(name)) {
            return;
        }
        let line = expr_path.path.span().start().line;
        self.record_qualified(
            modules.join("::"),
            type_name.clone(),
            line,
            segments.join("::"),
        );
    }

    fn record_qualified(&mut self, prefix: String, suffix: String, line: usize, rendered: String) {
        self.qualified
            .entry((prefix.clone(), suffix.clone()))
            .or_insert(QualifiedSite {
                prefix,
                suffix,
                line,
                rendered,
            });
    }

    fn check_shared_pointer(&mut self, path: &SynPath) {
        let registered = is_registered_file(&self.file, EXC_04_REGISTERED_FILES);
        for segment in &path.segments {
            let line = segment.ident.span().start().line;
            if segment.ident == "Arc" {
                let exact_site = self.exact_arc_site(path);
                let marked = exact_site
                    && registered
                    && self.owner.as_deref().is_some_and(|owner| {
                        registered_owner(&self.file, owner)
                            && (self.method.is_none()
                                || registered_method(
                                    owner,
                                    self.method.as_deref().unwrap_or_default(),
                                ))
                    })
                    && self.scope.is_empty()
                    && self.lines.has_marker(line, EXC_04, MARKER_LOOKBACK);
                let adopted = self
                    .file
                    .ends_with("babylon-tick/src/material_world/register.rs")
                    && self.owner.as_deref() == Some("SharedCanonicalBytes")
                    && self.method.is_none();
                if arc_holds_vec(&segment.arguments) && !(marked && adopted) {
                    self.push(
                        line,
                        "Arc<Vec<_>> copies a heap buffer; use Arc<[_]>",
                        "only the registered EXC-04 adopted-allocation site may keep Arc<Vec<_>>",
                    );
                } else if !marked {
                    self.push(
                        line,
                        "shared pointer Arc is outside the EXC-04 register",
                        "only a file listed in docs/agents/rust-style.md EXC-04 may retain it",
                    );
                }
            } else if segment.ident == "Rc" {
                self.push(
                    line,
                    "Rc is a finding everywhere; use unique ownership",
                    "Rc<T> and Rc<RefCell<T>> cannot be retained by an EXC-04 marker",
                );
            }
        }
    }

    fn exact_arc_site(&mut self, path: &SynPath) -> bool {
        let Some(owner) = self.owner.as_deref() else {
            return false;
        };
        let operation = path
            .segments
            .last()
            .map(|segment| segment.ident.to_string())
            .unwrap_or_default();
        let valid = if let Some(method) = self.method.as_deref() {
            matches!(
                (owner, method, operation.as_str()),
                ("SharedCanonicalBytes", "from_vec", "new")
                    | (
                        "SharedCanonicalBytes" | "MaterialReceiptHandle",
                        "shares_allocation",
                        "ptr_eq"
                    )
                    | (
                        "MaterialReceiptHandle" | "EconomicContentHandle" | "PeriodRegister",
                        "new",
                        "new"
                    )
                    | ("EconomicContentHandle", "strong_count", "strong_count")
                    | ("EconomicContentHandle", "downgrade", "downgrade")
                    | ("OpeningRegister", "from_opening", "new")
                    | ("RotatingSink", "open", "new")
                    | ("Diagnostics", "writer", "clone")
            )
        } else {
            matches!(
                (owner, self.field_name.as_deref()),
                (
                    "NationalCountyRoster"
                        | "MaterialReceiptHandle"
                        | "SharedCanonicalBytes"
                        | "EconomicContentHandle"
                        | "PeriodRegister"
                        | "ArchiveWorkerCancellation"
                        | "ProgressHandle"
                        | "DriverStateHandle"
                        | "Diagnostics",
                    Some("#0")
                ) | ("EconomicAdmissionOwner", Some("candidate"))
                    | ("OpeningRegister", Some("sections" | "lookup"))
                    | ("SourceArtifact", Some("bytes"))
                    | ("RotatingSink", Some("inner"))
            )
        };
        let site = self.method.as_deref().map_or_else(
            || self.field_name.clone().unwrap_or_default(),
            |method| format!("{method}:{operation}"),
        );
        let key = format!("{}|{owner}|{site}", self.file);
        valid && self.seen_arc_sites.insert(key)
    }

    fn check_catch_unwind(&mut self, path: &SynPath) {
        let Some(last) = path.segments.last() else {
            return;
        };
        if last.ident != "catch_unwind" {
            return;
        }
        self.push(
            last.ident.span().start().line,
            "panic::catch_unwind is not permitted",
            "use #[should_panic] in tests; no exception marker permits this call",
        );
    }

    fn record_path_use(&mut self, path: &SynPath) {
        if path.segments.len() != 1 {
            return;
        }
        let Some(segment) = path.segments.first() else {
            return;
        };
        let name = segment.ident.to_string();
        if is_lowercase_identifier(&name)
            && !is_use_keyword(&name)
            && !self
                .bindings
                .iter()
                .rev()
                .any(|scope| scope.contains(&name))
        {
            self.used_names
                .insert((self.scope.clone(), self.lexical.clone(), name));
        }
    }

    fn check_bool_parameters(&mut self, signature: &Signature) {
        let owner = signature.ident.to_string();
        let mut reports = Vec::new();
        for input in &signature.inputs {
            let FnArg::Typed(pat_type) = input else {
                continue;
            };
            let Pat::Ident(pat_ident) = pat_type.pat.as_ref() else {
                continue;
            };
            if !is_bool_type(&pat_type.ty) {
                continue;
            }
            let parameter = pat_ident.ident.to_string();
            if is_deferred_bool_parameter(&owner, &parameter) {
                continue;
            }
            reports.push((
                pat_type.ty.span().start().line,
                format!("`{owner}({parameter}: bool)` — introduce a two-variant enum"),
            ));
        }
        for (line, evidence) in reports {
            self.push_warn(
                line,
                "bool parameter's meaning is not obvious at the call site",
                evidence,
            );
        }
    }

    fn scan_macro_tokens(&mut self, tokens: &TokenStream) {
        let wrap =
            |delimiter| TokenStream::from(TokenTree::Group(Group::new(delimiter, tokens.clone())));
        let block = syn::parse2::<Block>(wrap(Delimiter::Brace));
        let expression = syn::parse2::<Expr>(wrap(Delimiter::Parenthesis));
        if block.is_ok() || expression.is_ok() {
            let mut nested = StyleVisitor::new(self.file.clone(), false, self.in_client_crate, "");
            nested.scope.clone_from(&self.scope);
            nested.lexical.clone_from(&self.lexical);
            nested.next_scope = self.next_scope;
            nested.bindings.clone_from(&self.bindings);
            if let Ok(block) = block {
                nested.visit_block(&block);
            } else if let Ok(expression) = expression {
                nested.visit_expr(&expression);
            }
            self.next_scope = nested.next_scope;
            self.macro_used_names.extend(nested.used_names);
            self.macro_used_names.extend(nested.macro_used_names);
            return;
        }
        let trees: Vec<TokenTree> = tokens.clone().into_iter().collect();
        for (index, tree) in trees.iter().enumerate() {
            match tree {
                TokenTree::Ident(ident) => {
                    let name = ident.to_string();
                    if is_lowercase_identifier(&name)
                        && !is_use_keyword(&name)
                        && !self
                            .bindings
                            .iter()
                            .rev()
                            .any(|scope| scope.contains(&name))
                        && !macro_ident_is_path_component(&trees, index)
                    {
                        self.macro_used_names.insert((
                            self.scope.clone(),
                            self.lexical.clone(),
                            name,
                        ));
                    }
                }
                TokenTree::Group(group) => self.scan_macro_tokens(&group.stream()),
                TokenTree::Punct(_) | TokenTree::Literal(_) => {}
            }
        }
    }
}

impl<'ast> Visit<'ast> for StyleVisitor<'_> {
    fn visit_item(&mut self, item: &'ast Item) {
        if self.item_depth == 0 {
            self.check_top_level_item(item);
        }
        self.item_depth += 1;
        let previous_owner = self.owner.take();
        self.owner = match item {
            Item::Struct(value) => Some(value.ident.to_string()),
            Item::Enum(value) => Some(value.ident.to_string()),
            Item::Type(value) => Some(value.ident.to_string()),
            Item::Impl(value) => match value.self_ty.as_ref() {
                Type::Path(path) => path
                    .path
                    .segments
                    .last()
                    .map(|segment| segment.ident.to_string()),
                _ => None,
            },
            _ => None,
        };
        let previous_table = self.byte_table;
        self.byte_table =
            matches!(item, Item::Const(value) if byte_type(&value.ty) && byte_array(&value.expr));
        syn::visit::visit_item(self, item);
        self.owner = previous_owner;
        self.byte_table = previous_table;
        self.item_depth -= 1;
    }

    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        let inline = item.content.is_some();
        if inline {
            self.module_stack.push(has_cfg_test(&item.attrs));
            self.scope.push(item.ident.to_string());
        }
        syn::visit::visit_item_mod(self, item);
        if inline {
            self.module_stack.pop();
            self.scope.pop();
        }
    }

    fn visit_item_fn(&mut self, item: &'ast ItemFn) {
        if self.fn_depth == 0 {
            self.local_fns
                .entry(self.scope.clone())
                .or_default()
                .insert(item.sig.ident.to_string());
        }
        self.check_bool_parameters(&item.sig);
        self.bindings.push(BTreeSet::new());
        self.fn_depth += 1;
        syn::visit::visit_item_fn(self, item);
        self.fn_depth -= 1;
        self.bindings.pop();
    }

    fn visit_impl_item_fn(&mut self, item: &'ast ImplItemFn) {
        let previous_method = self.method.replace(item.sig.ident.to_string());
        self.check_bool_parameters(&item.sig);
        self.bindings.push(BTreeSet::new());
        self.fn_depth += 1;
        syn::visit::visit_impl_item_fn(self, item);
        self.fn_depth -= 1;
        self.bindings.pop();
        self.method = previous_method;
    }

    fn visit_trait_item_fn(&mut self, item: &'ast TraitItemFn) {
        self.check_bool_parameters(&item.sig);
        self.bindings.push(BTreeSet::new());
        self.fn_depth += 1;
        syn::visit::visit_trait_item_fn(self, item);
        self.fn_depth -= 1;
        self.bindings.pop();
    }

    fn visit_item_struct(&mut self, item: &'ast ItemStruct) {
        let previous = self.field_index;
        self.field_index = 0;
        syn::visit::visit_item_struct(self, item);
        self.field_index = previous;
    }

    fn visit_field(&mut self, field: &'ast Field) {
        let previous = self.field_name.take();
        self.field_name = Some(
            field
                .ident
                .as_ref()
                .map_or_else(|| format!("#{}", self.field_index), ToString::to_string),
        );
        self.field_index += 1;
        syn::visit::visit_field(self, field);
        self.field_name = previous;
    }

    fn visit_item_enum(&mut self, item: &'ast ItemEnum) {
        for variant in &item.variants {
            let Fields::Unnamed(fields) = &variant.fields else {
                continue;
            };
            if fields.unnamed.len() != 1 {
                continue;
            }
            let Some(field) = fields.unnamed.first() else {
                continue;
            };
            if !is_bool_type(&field.ty) {
                continue;
            }
            let owner = variant.ident.to_string();
            if is_deferred_bool_parameter(&owner, "0")
                || SELF_DESCRIBING_BOOL_PAYLOADS.contains(&owner.as_str())
            {
                continue;
            }
            self.push_warn(
                field.ty.span().start().line,
                "enum variant carries a bare bool payload",
                format!("`{owner}(bool)` — introduce a two-variant enum"),
            );
        }
        syn::visit::visit_item_enum(self, item);
    }

    fn visit_pat_ident(&mut self, pat: &'ast PatIdent) {
        if let Some(scope) = self.bindings.last_mut() {
            scope.insert(pat.ident.to_string());
        }
        syn::visit::visit_pat_ident(self, pat);
    }

    fn visit_block(&mut self, block: &'ast Block) {
        self.next_scope += 1;
        self.lexical.push(self.next_scope);
        self.bindings.push(BTreeSet::new());
        syn::visit::visit_block(self, block);
        self.bindings.pop();
        self.lexical.pop();
    }

    fn visit_local(&mut self, local: &'ast Local) {
        let previous = self.byte_table;
        self.byte_table = matches!(&local.pat, Pat::Type(value) if byte_type(&value.ty))
            && local
                .init
                .as_ref()
                .is_some_and(|init| byte_array(&init.expr));
        for attribute in &local.attrs {
            self.visit_attribute(attribute);
        }
        if let Some(init) = &local.init {
            self.visit_local_init(init);
        }
        self.visit_pat(&local.pat);
        self.byte_table = previous;
    }

    fn visit_expr_let(&mut self, expr: &'ast ExprLet) {
        for attr in &expr.attrs {
            self.visit_attribute(attr);
        }
        self.visit_expr(&expr.expr);
        self.visit_pat(&expr.pat);
    }

    fn visit_expr_if(&mut self, expr: &'ast ExprIf) {
        for attr in &expr.attrs {
            self.visit_attribute(attr);
        }
        self.bindings.push(BTreeSet::new());
        self.visit_expr(&expr.cond);
        self.visit_block(&expr.then_branch);
        self.bindings.pop();
        if let Some((_, branch)) = &expr.else_branch {
            self.visit_expr(branch);
        }
    }

    fn visit_expr_while(&mut self, expr: &'ast ExprWhile) {
        for attr in &expr.attrs {
            self.visit_attribute(attr);
        }
        self.bindings.push(BTreeSet::new());
        self.visit_expr(&expr.cond);
        self.visit_block(&expr.body);
        self.bindings.pop();
    }

    fn visit_expr_closure(&mut self, closure: &'ast ExprClosure) {
        self.bindings.push(BTreeSet::new());
        syn::visit::visit_expr_closure(self, closure);
        self.bindings.pop();
    }

    fn visit_arm(&mut self, arm: &'ast Arm) {
        self.bindings.push(BTreeSet::new());
        syn::visit::visit_arm(self, arm);
        self.bindings.pop();
    }

    fn visit_expr_for_loop(&mut self, expr: &'ast ExprForLoop) {
        for attr in &expr.attrs {
            self.visit_attribute(attr);
        }
        self.visit_expr(&expr.expr);
        self.bindings.push(BTreeSet::new());
        self.visit_pat(&expr.pat);
        self.visit_block(&expr.body);
        self.bindings.pop();
    }

    fn visit_macro(&mut self, mac: &'ast Macro) {
        self.scan_macro_tokens(&mac.tokens);
        syn::visit::visit_macro(self, mac);
    }

    fn visit_item_use(&mut self, item: &'ast ItemUse) {
        let public = matches!(item.vis, Visibility::Public(_));
        let mut prefix = Vec::new();
        self.inspect_use_tree(&item.tree, &mut prefix, false, public);
        syn::visit::visit_item_use(self, item);
    }

    fn visit_attribute(&mut self, attribute: &'ast Attribute) {
        if is_rustfmt_skip(attribute) {
            let line = attribute.span().start().line;
            let registered = is_registered_file(&self.file, EXC_05_REGISTERED_FILES);
            let marked = registered && self.lines.has_marker(line, EXC_05, MARKER_LOOKBACK);
            if !registered || !self.byte_table {
                self.push(
                    line,
                    "rustfmt::skip is outside the EXC-05 byte tables",
                    "only babylon-graph/src/state_hash.rs and babylon-tick/src/world_hash.rs may skip the formatter",
                );
            } else if !marked {
                self.push(
                    line,
                    "rustfmt::skip lacks STYLE-EXCEPTION(EXC-05)",
                    "only manual byte-table alignment may skip the formatter",
                );
            }
        }
        syn::visit::visit_attribute(self, attribute);
    }

    fn visit_type_path(&mut self, type_path: &'ast TypePath) {
        self.inspect_type_path(type_path);
        if type_path.qself.is_none() {
            self.check_shared_pointer(&type_path.path);
        }
        syn::visit::visit_type_path(self, type_path);
    }

    fn visit_expr_path(&mut self, expr_path: &'ast ExprPath) {
        self.inspect_expr_path(expr_path);
        if expr_path.qself.is_none() {
            self.record_path_use(&expr_path.path);
        }
        syn::visit::visit_expr_path(self, expr_path);
    }

    fn visit_lit_int(&mut self, literal: &'ast LitInt) {
        let text = literal.to_string();
        if has_uppercase_hex_digit(&text) {
            self.push(
                literal.span().start().line,
                "hex literal contains an uppercase digit",
                format!("{text} — write the digits in lowercase"),
            );
        }
        syn::visit::visit_lit_int(self, literal);
    }
}

/// Check one Rust source file against the AST style rules.
///
/// # Errors
/// A string naming the file and the parse failure when the source is not
/// syntactically valid Rust.
pub fn check_rust_source(path: &Path, content: &str) -> Result<Vec<Finding>, String> {
    check_source(path, &path.display().to_string(), content)
}

/// Run the AST style check over the default `rust/crates` tree, or over every
/// Rust file beneath the given paths. The default tree skips `fixtures`
/// directories because they hold intentionally non-conforming test data; an
/// explicit path is checked exactly as given.
///
/// # Errors
/// A string naming the path and the filesystem or parse failure when a root is
/// missing, unreadable, or not valid Rust.
pub fn run(repo: &Repo, roots: &[String]) -> Result<Vec<Finding>, String> {
    let (requested, skip_fixtures) = if roots.is_empty() {
        (vec![repo.root.join("rust/crates")], true)
    } else {
        let mut resolved = Vec::with_capacity(roots.len());
        for root in roots {
            resolved.push(resolve_root(repo, root)?);
        }
        (resolved, false)
    };
    let mut files = Vec::new();
    for root in &requested {
        collect_rust_files(root, 0, skip_fixtures, &mut files)?;
    }
    files.sort();
    files.dedup();
    let mut findings = Vec::new();
    for file in &files {
        let content = std::fs::read_to_string(file)
            .map_err(|error| format!("{}: {error}", file.display()))?;
        let display = repo.display_path(file);
        findings.extend(check_source(file, &display, &content)?);
    }
    sort_findings(&mut findings);
    Ok(findings)
}

fn check_source(path: &Path, display: &str, content: &str) -> Result<Vec<Finding>, String> {
    let file = syn::parse_file(content)
        .map_err(|error| format!("{display}: Rust parse failed: {error}"))?;
    let in_client_crate = path
        .components()
        .any(|component| component.as_os_str() == "babylon-client");
    let mut visitor = StyleVisitor::new(
        display.to_owned(),
        is_non_leaf(path),
        in_client_crate,
        content,
    );
    if path
        .file_name()
        .is_some_and(|name| name.to_str() == Some("mod.rs"))
    {
        visitor.push(
            1,
            "module file uses the forbidden mod.rs layout",
            "use foo.rs beside a foo/ directory instead",
        );
    }
    visitor.visit_file(&file);
    Ok(visitor.finish())
}

fn resolve_root(repo: &Repo, root: &str) -> Result<PathBuf, String> {
    let repo_relative = repo.root.join(root);
    if repo_relative.exists() {
        return Ok(repo_relative);
    }
    let cwd = std::env::current_dir().map_err(|error| format!("current directory: {error}"))?;
    let cwd_relative = cwd.join(root);
    if cwd_relative.exists() {
        return Ok(cwd_relative);
    }
    Err(format!(
        "{root}: path does not exist beneath {} or the current directory",
        repo.root.display()
    ))
}

fn collect_rust_files(
    path: &Path,
    depth: usize,
    skip_fixtures: bool,
    output: &mut Vec<PathBuf>,
) -> Result<(), String> {
    if depth > MAX_WALK_DEPTH {
        return Err(format!(
            "{}: directory depth exceeds {MAX_WALK_DEPTH}",
            path.display()
        ));
    }
    if path.is_file() {
        if path.extension().is_some_and(|extension| extension == "rs") {
            output.push(path.to_path_buf());
        }
        return Ok(());
    }
    if !path.is_dir() {
        return Err(format!("{}: not a file or directory", path.display()));
    }
    let mut entries = Vec::new();
    for entry in std::fs::read_dir(path).map_err(|error| format!("{}: {error}", path.display()))? {
        let entry = entry.map_err(|error| format!("{}: {error}", path.display()))?;
        let name = entry.file_name();
        if matches!(name.to_str(), Some("target" | ".git")) {
            continue;
        }
        if skip_fixtures && name == "fixtures" {
            continue;
        }
        entries.push(entry.path());
    }
    entries.sort();
    for entry in &entries {
        collect_rust_files(entry, depth + 1, skip_fixtures, output)?;
    }
    Ok(())
}

fn is_non_leaf(path: &Path) -> bool {
    let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
        return false;
    };
    if name == "lib.rs" || name == "mod.rs" {
        return true;
    }
    let Some(stem) = name.strip_suffix(".rs") else {
        return false;
    };
    path.parent()
        .is_some_and(|parent| parent.join(stem).is_dir())
}

fn has_cfg_test(attributes: &[Attribute]) -> bool {
    attributes.iter().any(|attribute| {
        attribute.path().is_ident("cfg")
            && matches!(
                &attribute.meta,
                Meta::List(list) if list.tokens.to_string().contains("test")
            )
    })
}

fn is_rustfmt_skip(attribute: &Attribute) -> bool {
    let path = attribute.path();
    path.segments.len() == 2
        && path
            .segments
            .first()
            .is_some_and(|segment| segment.ident == "rustfmt")
        && path
            .segments
            .get(1)
            .is_some_and(|segment| segment.ident == "skip")
}

fn path_segments(path: &SynPath) -> Vec<String> {
    path.segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect()
}

fn is_upper_camel_case(name: &str) -> bool {
    let mut characters = name.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    first.is_ascii_uppercase() && name.chars().any(|character| character.is_ascii_lowercase())
}

fn is_lowercase_identifier(name: &str) -> bool {
    name.chars()
        .next()
        .is_some_and(|character| character.is_ascii_lowercase() || character == '_')
}

fn is_module_segment(name: &str) -> bool {
    is_lowercase_identifier(name)
}

fn is_use_keyword(name: &str) -> bool {
    matches!(name, "self" | "super" | "crate")
}

/// Whether `file` is one of the register entries. The walk reports
/// repository-relative paths, while tests may hand in a crate-relative or
/// absolute path, so an entry matches either the whole path or a trailing
/// path-segment run.
fn is_registered_file(file: &str, registry: &[&str]) -> bool {
    let normalized = file.replace('\\', "/");
    registry
        .iter()
        .any(|entry| normalized == *entry || normalized.ends_with(&format!("/{entry}")))
}

fn is_bool_type(ty: &Type) -> bool {
    let Type::Path(type_path) = ty else {
        return false;
    };
    if type_path.qself.is_some() || type_path.path.leading_colon.is_some() {
        return false;
    }
    let segments = path_segments(&type_path.path);
    segments.len() == 1 && segments.first().is_some_and(|name| name == "bool")
}

fn is_deferred_bool_parameter(owner: &str, parameter: &str) -> bool {
    DEFERRED_BOOL_PARAMETERS
        .iter()
        .any(|(deferred_owner, deferred_parameter)| {
            *deferred_owner == owner && *deferred_parameter == parameter
        })
}

/// Whether a macro-only direct import is in the Task 11 grandfather register.
fn residual_macro_import(file: &str, module: &str, name: &str) -> bool {
    residual_macro_imports().contains(&(file.to_owned(), module.to_owned(), name.to_owned()))
}

/// The parsed [`RESIDUAL_MACRO_IMPORTS`] register, built once per process.
fn residual_macro_imports() -> &'static BTreeSet<(String, String, String)> {
    static REGISTER: OnceLock<BTreeSet<(String, String, String)>> = OnceLock::new();
    REGISTER.get_or_init(|| {
        let mut entries = BTreeSet::new();
        let mut data_lines = 0;
        for line in RESIDUAL_MACRO_IMPORTS.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            data_lines += 1;
            let mut fields = line.split('|');
            let (Some(file), Some(module), Some(names)) =
                (fields.next(), fields.next(), fields.next())
            else {
                continue;
            };
            for name in names.split(',') {
                entries.insert((file.to_owned(), module.to_owned(), name.to_owned()));
            }
        }
        debug_assert_eq!(
            data_lines, RESIDUAL_MACRO_IMPORT_LINES,
            "the macro-import register changed without updating its pinned line count"
        );
        entries
    })
}

/// Whether a macro-token identifier is part of a path, field, named argument,
/// macro name, or closure binding rather than a bare value use. Those shapes
/// resolve to a namespace, a field, or an argument name, never to an imported
/// free function the file calls.
fn macro_ident_is_path_component(trees: &[TokenTree], index: usize) -> bool {
    let neighbour = |position: usize| trees.get(position);
    let punctuation = |position: usize| match neighbour(position) {
        Some(TokenTree::Punct(punct)) => Some(punct.as_char()),
        _ => None,
    };
    if index > 0 && matches!(punctuation(index - 1), Some(':' | '.' | '|')) {
        return true;
    }
    matches!(punctuation(index + 1), Some(':' | '.' | '!' | '=' | '|'))
}

fn render_path(prefix: &[String], tail: &str) -> String {
    let mut rendered = prefix.join("::");
    if !rendered.is_empty() {
        rendered.push_str("::");
    }
    rendered.push_str(tail);
    rendered
}

fn render_use_tree(tree: &UseTree) -> String {
    match tree {
        UseTree::Path(path) => {
            format!("{}::{}", path.ident, render_use_tree(&path.tree))
        }
        UseTree::Group(group) => {
            let items = group
                .items
                .iter()
                .map(render_use_tree)
                .collect::<Vec<_>>()
                .join(", ");
            format!("{{{items}}}")
        }
        UseTree::Glob(_) => "*".to_owned(),
        UseTree::Name(name) => name.ident.to_string(),
        UseTree::Rename(rename) => {
            format!("{} as {}", rename.ident, rename.rename)
        }
    }
}

fn arc_holds_vec(arguments: &PathArguments) -> bool {
    let PathArguments::AngleBracketed(bracketed) = arguments else {
        return false;
    };
    let Some(GenericArgument::Type(Type::Path(inner))) = bracketed.args.first() else {
        return false;
    };
    inner
        .path
        .segments
        .last()
        .is_some_and(|segment| segment.ident == "Vec")
}

fn has_uppercase_hex_digit(text: &str) -> bool {
    let digits = text.strip_prefix("0x").or_else(|| text.strip_prefix("0X"));
    digits.is_some_and(|rest| rest.chars().any(|character| character.is_ascii_uppercase()))
}

fn sort_findings(findings: &mut [Finding]) {
    findings.sort_by(|left, right| {
        (
            left.file.as_str(),
            left.line,
            left.what.as_str(),
            left.evidence.as_str(),
        )
            .cmp(&(
                right.file.as_str(),
                right.line,
                right.what.as_str(),
                right.evidence.as_str(),
            ))
    });
}

fn dedup_findings(findings: &mut Vec<Finding>) {
    findings.dedup_by(|left, right| {
        left.file == right.file
            && left.line == right.line
            && left.what == right.what
            && left.evidence == right.evidence
    });
}

fn byte_array(expr: &Expr) -> bool {
    match expr {
        Expr::Reference(reference) => byte_array(&reference.expr),
        Expr::Array(array) => array.elems.iter().all(|element| match element {
            Expr::Lit(lit) => match &lit.lit {
                syn::Lit::Int(value) => value.base10_parse::<u8>().is_ok(),
                syn::Lit::Byte(_) => true,
                _ => false,
            },
            _ => false,
        }),
        _ => false,
    }
}

fn registered_owner(file: &str, owner: &str) -> bool {
    const SITES: &[(&str, &[&str])] = &[
        (
            "babylon-kernel/src/geography/roster.rs",
            &["NationalCountyRoster"],
        ),
        (
            "babylon-tick/src/material_world/register.rs",
            &["MaterialReceiptHandle", "SharedCanonicalBytes"],
        ),
        (
            "babylon-persistence/src/economic_content.rs",
            &[
                "EconomicContentHandle",
                "EconomicContentRef",
                "EconomicAdmissionOwner",
            ],
        ),
        (
            "babylon-persistence/src/state_storage/register.rs",
            &["OpeningRegister"],
        ),
        (
            "babylon-persistence/src/observer_material/snapshot.rs",
            &["PeriodRegister"],
        ),
        (
            "babylon-persistence/src/economic_catalog/sources.rs",
            &["SourceArtifact"],
        ),
        (
            "babylon-persistence/src/archive_worker.rs",
            &["ArchiveWorkerCancellation"],
        ),
        ("babylon-client/src/logging.rs", &["RotatingSink"]),
        (
            "babylon-persistence/examples/michigan_experiment/artifacts.rs",
            &["ProgressHandle"],
        ),
        (
            "babylon-persistence/src/runtime_session/coordinator/tests/support.rs",
            &["DriverStateHandle"],
        ),
        (
            "babylon-persistence/tests/observer_material_live/runtime_process.rs",
            &["Diagnostics"],
        ),
    ];
    SITES
        .iter()
        .any(|(path, owners)| file.ends_with(path) && owners.contains(&owner))
}

fn byte_type(ty: &Type) -> bool {
    match ty {
        Type::Reference(reference) => byte_type(&reference.elem),
        Type::Slice(slice) => {
            matches!(slice.elem.as_ref(), Type::Path(path) if path.path.is_ident("u8"))
        }
        Type::Array(array) => {
            matches!(array.elem.as_ref(), Type::Path(path) if path.path.is_ident("u8"))
        }
        _ => false,
    }
}

fn registered_method(owner: &str, method: &str) -> bool {
    matches!(
        (owner, method),
        ("SharedCanonicalBytes", "from_vec" | "shares_allocation")
            | ("MaterialReceiptHandle", "new" | "shares_allocation")
            | (
                "EconomicContentHandle",
                "new" | "strong_count" | "downgrade"
            )
            | ("OpeningRegister", "from_opening")
            | ("PeriodRegister", "new")
            | ("RotatingSink", "open")
            | ("Diagnostics", "writer")
    )
}

#[cfg(test)]
mod tests {
    use std::path::Path;

    #[test]
    fn the_macro_residual_register_is_sorted_unique_and_pinned() {
        let data: Vec<&str> = super::RESIDUAL_MACRO_IMPORTS
            .lines()
            .map(str::trim)
            .filter(|line| !line.is_empty() && !line.starts_with('#'))
            .collect();
        assert_eq!(
            data.len(),
            super::RESIDUAL_MACRO_IMPORT_LINES,
            "the register's data-line count must match the pinned constant"
        );
        let mut sorted = data.clone();
        sorted.sort_unstable();
        assert_eq!(
            data, sorted,
            "register lines stay sorted so a shrink is a one-line diff"
        );
        let mut names = 0;
        for line in &data {
            let fields: Vec<&str> = line.split('|').collect();
            assert_eq!(
                fields.len(),
                3,
                "each register line needs file|module|names: {line}"
            );
            assert!(!fields[0].is_empty() && !fields[1].is_empty(), "{line}");
            for name in fields[2].split(',') {
                assert!(!name.is_empty(), "empty name in register line: {line}");
                names += 1;
            }
        }
        assert_eq!(
            super::residual_macro_imports().len(),
            names,
            "a repeated (file, module, name) entry would make the register lie"
        );
    }

    #[test]
    fn the_default_walk_skips_fixture_directories() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests");
        let mut files = Vec::new();
        super::collect_rust_files(&root, 0, true, &mut files)
            .expect("the tests tree must be readable");
        assert!(!files.is_empty(), "the walk must still find test sources");
        assert!(
            files
                .iter()
                .all(|file| !file.to_string_lossy().contains("/fixtures/")),
            "fixture sources must not enter the default walk: {files:?}"
        );
        let mut explicit = Vec::new();
        super::collect_rust_files(&root.join("fixtures"), 0, false, &mut explicit)
            .expect("the fixture tree must be readable");
        assert!(
            !explicit.is_empty(),
            "an explicit fixture path is still checked"
        );
    }
}
