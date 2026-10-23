//! AST sentinel for the Google Rust Style Guide rules that no formatter or
//! Clippy lint can express: module layout, import shape, inline qualified
//! types, shared pointers, exception markers, and hex literal casing.
//!
//! `docs/agents/rust-style.md` is the governed specification. The check stays
//! out of the default `all` set until the Tasks 5-10 refactors land (Task 11
//! enables it); `bsl-lint google-rust-style <path>` runs it by name meanwhile.
//!
//! Two deliberate scopes keep the rules honest: the default filesystem walk
//! skips `fixtures` directories (they hold intentionally non-conforming test
//! data), and a top-level `fn main` is not an API definition because Cargo
//! requires it in the crate root. Explicit paths are still checked exactly.

use crate::finding::{Finding, Severity};
use crate::repo::Repo;
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{
    Attribute, Expr, ExprCall, ExprPath, GenericArgument, ImplItemFn, Item, ItemFn, ItemMod,
    ItemUse, LitInt, Meta, Path as SynPath, PathArguments, TraitItemFn, Type, TypePath, UseGlob,
    UseTree, Visibility,
};

/// The CLI name of this check.
pub const CHECK: &str = "google-rust-style";

const EXCEPTION_PREFIX: &str = "STYLE-EXCEPTION(EXC-";
const EXC_04: &str = "STYLE-EXCEPTION(EXC-04";
const EXC_05: &str = "STYLE-EXCEPTION(EXC-05";
const MARKER_LOOKBACK: usize = 2;
const MAX_WALK_DEPTH: usize = 32;

/// A lowercase leaf imported from a module, pending confirmation that the file
/// calls it as a free function.
struct ImportCandidate {
    name: String,
    line: usize,
    rendered: String,
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
    fn_depth: usize,
    item_depth: usize,
    lines: SourceLines<'a>,
    findings: Vec<Finding>,
    imports: Vec<ImportCandidate>,
    calls: BTreeSet<String>,
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
            fn_depth: 0,
            item_depth: 0,
            lines: SourceLines::new(source),
            findings: Vec::new(),
            imports: Vec::new(),
            calls: BTreeSet::new(),
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

    fn finish(mut self) -> Vec<Finding> {
        self.finish_imports();
        self.finish_qualified_types();
        sort_findings(&mut self.findings);
        dedup_findings(&mut self.findings);
        self.findings
    }

    fn finish_imports(&mut self) {
        for candidate in std::mem::take(&mut self.imports) {
            if self.calls.contains(&candidate.name) {
                self.push(
                    candidate.line,
                    "free function is imported directly instead of its module",
                    format!(
                        "{} — import the module and call `{}` qualified",
                        candidate.rendered, candidate.name
                    ),
                );
            }
        }
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
        self.push(
            glob.star_token.span().start().line,
            "glob import is outside the EXC-03 allowances",
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
        let public_reexport = public
            && self.non_leaf
            && prefix.first().is_some_and(|name| {
                !name.is_empty() && name != "super" && name != "self" && name != "crate"
            });
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
        for segment in &path.segments {
            let line = segment.ident.span().start().line;
            if segment.ident == "Arc" {
                if arc_holds_vec(&segment.arguments) {
                    self.push(
                        line,
                        "Arc<Vec<_>> copies a heap buffer; use Arc<[_]>",
                        "Arc<Vec<_>> is a finding everywhere, even with an EXC-04 marker",
                    );
                } else if !self.lines.has_marker(line, EXC_04, MARKER_LOOKBACK) {
                    self.push(
                        line,
                        "shared pointer Arc is outside the EXC-04 register",
                        "add `// STYLE-EXCEPTION(EXC-04): <reason>` or remove the shared pointer",
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

    fn check_catch_unwind(&mut self, path: &SynPath) {
        let Some(last) = path.segments.last() else {
            return;
        };
        if last.ident != "catch_unwind" {
            return;
        }
        let line = last.ident.span().start().line;
        if !self
            .lines
            .has_marker(line, EXCEPTION_PREFIX, MARKER_LOOKBACK)
        {
            self.push(
                line,
                "panic::catch_unwind lacks a STYLE-EXCEPTION marker",
                "use #[should_panic] in tests or state the retained boundary exception",
            );
        }
    }
}

impl<'ast> Visit<'ast> for StyleVisitor<'_> {
    fn visit_item(&mut self, item: &'ast Item) {
        if self.item_depth == 0 {
            self.check_top_level_item(item);
        }
        self.item_depth += 1;
        syn::visit::visit_item(self, item);
        self.item_depth -= 1;
    }

    fn visit_item_mod(&mut self, item: &'ast ItemMod) {
        let inline = item.content.is_some();
        if inline {
            self.module_stack.push(has_cfg_test(&item.attrs));
        }
        syn::visit::visit_item_mod(self, item);
        if inline {
            self.module_stack.pop();
        }
    }

    fn visit_item_fn(&mut self, item: &'ast ItemFn) {
        self.fn_depth += 1;
        syn::visit::visit_item_fn(self, item);
        self.fn_depth -= 1;
    }

    fn visit_impl_item_fn(&mut self, item: &'ast ImplItemFn) {
        self.fn_depth += 1;
        syn::visit::visit_impl_item_fn(self, item);
        self.fn_depth -= 1;
    }

    fn visit_trait_item_fn(&mut self, item: &'ast TraitItemFn) {
        self.fn_depth += 1;
        syn::visit::visit_trait_item_fn(self, item);
        self.fn_depth -= 1;
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
            if !self.lines.has_marker(line, EXC_05, MARKER_LOOKBACK) {
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
        syn::visit::visit_expr_path(self, expr_path);
    }

    fn visit_expr_call(&mut self, call: &'ast ExprCall) {
        if let Expr::Path(expr_path) = call.func.as_ref() {
            if expr_path.qself.is_none() && expr_path.path.segments.len() == 1 {
                if let Some(segment) = expr_path.path.segments.first() {
                    self.calls.insert(segment.ident.to_string());
                }
            }
        }
        syn::visit::visit_expr_call(self, call);
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

#[cfg(test)]
mod tests {
    use std::path::Path;

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
