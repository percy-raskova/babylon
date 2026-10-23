# Rust Style: Google Rust Style Guide Conformance

Babylon Rust code follows the
[Google Rust Style Guide](https://google.github.io/styleguide/rustguide.html).
That guide is the authority for Rust style in this repository. If a local
preference differs from the guide, the guide wins.

This page is the governed specification for PER-350. The
`bsl-lint google-rust-style` check reads these rules. ADR286 records the
decision and the reasoning.

## Authority and local inputs

- [Google Rust Style Guide](https://google.github.io/styleguide/rustguide.html)
- [Rust Style Guide](https://doc.rust-lang.org/nightly/style-guide/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- `docs/agents/coding-standards.md` for repository-wide source rules
- `rust/rustfmt.toml` and `rust/Cargo.toml` for the mechanical settings

The Google guide defers to the public Rust style rules where the two agree.
The formatter owns formatting. The Google guide owns the remaining choices:
code organization, API shape, ownership, error reporting, naming, and tests.

## Enforcement

Three layers enforce the guide. PER-350 delivers all three in one change set.

| Layer | Mechanism | Check |
| --- | --- | --- |
| Formatting | `rust/rustfmt.toml` with `max_width = 100` | `cargo fmt --all -- --check` |
| Lints | `[workspace.lints]` inherited by every crate | `cargo clippy --workspace --all-targets` |
| AST style | `bsl-lint google-rust-style` | `mise run rust:check-no-docs` |

One lint needs a stated scope. `non_exhaustive_omitted_patterns` is unstable on
the pinned 1.91.1 toolchain (rust-lang/rust#89554), so the workspace table drops
it rather than emitting `unknown_lints` on every crate. EXC-02's exhaustive-match
obligation and the `bsl-lint google-rust-style` wildcard-arm check carry that
coverage. Conformance tests keep exactly two file-scope allows,
`clippy::float_cmp` and `clippy::unreadable_literal`, because their fixtures
assert exact authored values; every other pedantic finding in test code is fixed
or annotated at the item that earns it.

A change that fails one layer does not merge. A style refactoring must keep
canonical bytes equal. `GraphStateHash`, `NominalWorldHash`, `TickContentHash`,
and the SQL schema stay unchanged (Constitution III.7).

## Rule summary

<!-- Vale: the tables preserve literal crate, macro, and lint identifiers. -->
<!-- vale Vale.Spelling = NO -->
<!-- vale ste.NounClusters = NO -->

### Code organization

| Guide rule | Babylon rule |
| --- | --- |
| Prefer small crates `[chrome]` | Each crate owns one abstraction. Do not merge crates for convenience. |
| Flat file layout `[chrome]` | Not applied (EXC-01). Use the Cargo module layout. |
| Name leaf modules after the primary item | `Foo` lives in `foo.rs`. Babylon forbids `mod.rs` (EXC-01). |
| No APIs in non-leaf modules | Non-leaf modules hold `mod` declarations and `pub use` only. |
| No glob imports | See EXC-03 for the Bevy prelude and the three guide allowances. |
| One module per `use` | No `::` inside a brace group. The AST check rejects a nested path. |
| Local trait imports | Import a trait inside the function that calls its methods. |
| Qualify free functions | `use std::mem;` then `mem::size_of()` not `use std::mem::size_of`. |
| Unqualified type names | `use regex::Regex;` then `Regex`. Rename on collision. |
| Import mechanism `[chrome]` | Not applied (EXC-01). Standard Cargo paths. |

### Formatting

| Guide rule | Babylon rule |
| --- | --- |
| Use the formatting tool | `cargo fmt` owns every byte. CI runs the check form. |
| `max_width = 100` | Set in `rust/rustfmt.toml`. |
| Shorthand initializers | Set `use_field_init_shorthand` and `use_try_shorthand`. |
| Lowercase hex literals | The AST check rejects an uppercase hex digit in a literal. |
| Macro matcher formatting | Format the matcher. The guide gives the form. |
| Invisible characters | Write the escape form, such as `\u{200D}`, in the literal. |
| Opt out of formatting | Only the byte tables in EXC-05 skip rustfmt. |

### Ownership and borrowing

| Guide rule | Babylon rule |
| --- | --- |
| Avoid `Rc` and `Arc` | Unique ownership and borrows by default. `Rc` and `Arc<Vec<T>>` are findings. Retained shared pointers follow EXC-04. |
| Prefer borrows over deep copies | Clone only for a real deep copy. Do not clone to dodge a borrow. |

### Function inputs and outputs

| Guide rule | Babylon rule |
| --- | --- |
| Flexible references | `&T`, `&[T]`, `&str`, and `Option<&T>`. Never `&Vec<T>` or `&String`. |
| Iterator returns | Library code returns `impl Iterator` when the caller consumes it. |
| Iterator parameters | Library code accepts `impl IntoIterator` when it only iterates. |
| `impl Into<T>` | Library APIs only, when call-site ergonomics earn the cost. |
| `enum` over `bool` | No `bool` parameter whose meaning is not obvious at the call site. |
| Error reporting | `Option` for simple absence, `Result` for caller-recoverable faults, `panic!` for a broken invariant. |

### Types and traits

| Guide rule | Babylon rule |
| --- | --- |
| Newtype over alias | Newtype when the value has its own semantics or API. |
| Named fields | No tuple struct except a one-field newtype. |
| Add impls when needed | Application crates add a trait impl at the first real consumer. |
| Standard traits first | Use `FromStr`, `From`, and `Display` instead of lookalike methods. |
| Derive when possible | Manual `impl` needs a reason the derive cannot express. |
| Generics over `dyn` | Generic parameters in library code. `dyn` only for object safety or code size. |
| Trait versus inherent | A trait exists for bounds, `impl Trait`, `dyn`, or an extension trait. |
| Extension traits | Suffix `Ext`. The owner of the type owns the trait. |
| `From` plus constructor | Pair an important `From` impl with `new` or `from_foo`. |
| Options structs | Derive or write `Default` for an all-public options bag. |

### Concurrency, macros, naming

| Guide rule | Babylon rule |
| --- | --- |
| Poison handling | Never read the value inside a poisoned mutex. Map the poison to an error. |
| No `async` `[chrome]` | Not applied (EXC-01). Babylon has no async runtime. |
| No `std::thread` `[chrome]` | Not applied (EXC-01). Babylon uses `std::thread` and scoped threads. |
| `fuchsia_sync::Mutex` `[Fuchsia]` | Not applied (EXC-01). Use `std::sync`. |
| Prefer functions over macros | Function, then `macro_rules!`, then code generation, then `proc_macro`. |
| Naming | Follow the standard library: `as_`, `to_`, `into_`, `new`, `try_new`, `set_`, `with_`. |
| Lifetimes | Descriptive names. `'a` and `'b` only for a direct input to output link. |
| Generic parameters | Short and indicative, taken from the main bound. |
| No abbreviations | Spell the word. Keep established terms such as `IpAddr` and `H3`. |

### Documentation

- Public items need a `///` doc comment. Modules need a `//!` header.
- Document panic cases, `unsafe` invariants, and `# Errors` for `Result`.
- Use Markdown and full sentences with capital letters and punctuation.
- Do not restate the type or the name. Say what the item guarantees.
- Never access a `#[doc(hidden)]` item that another crate owns.

### Other language features

| Guide rule | Babylon rule |
| --- | --- |
| Unsafe code | Avoid it. A required block needs a `SAFETY:` comment and a justification. |
| No unstable features | Stable Rust only. |
| Getters and setters | `foo`, `foo_mut`, `take_foo`, `set_foo`, `with_foo`, `replace_foo`. |
| Expected API sets | `len` comes with `is_empty`. |
| Const functions | `const` only with a commitment to keep it `const`. |
| Operator overloading | Mathematical meaning only. |
| `#[non_exhaustive]` | Not applied (EXC-02). |
| `#[must_use]` | On a function whose ignored result is a defect. On the matching error type. |
| Code before `main` | Not permitted. No `ctor` style initializer. |

### Implementation concerns

| Guide rule | Babylon rule |
| --- | --- |
| Type inference | Annotate generic returns, `.into()`, `.parse()`, and long iterator chains. |
| Pattern matching | `if let` or `let ... else` instead of `is_some()` plus `unwrap()`. |
| `expect` over `unwrap` | Every `expect` states the invariant that holds. A bare `unwrap` is a finding. |
| `non_exhaustive` matching | List every known variant. A wildcard covers only unknown variants. |
| Assertion context | A failing assertion explains why it holds and what broke. |
| Iterator clarity | A `for` loop beats a long combinator chain. |
| `panic::catch_unwind` | Not permitted in tests. Use `#[should_panic]`. |
| String building | `format!` and `write!` over manual concatenation. |

### Tests

Babylon uses `cargo-nextest` with Rust's built-in test harness. A test asserts
a behavior contract. A test does not repeat implementation text. Every failing
assertion carries context.

<!-- vale ste.NounClusters = YES -->
<!-- vale Vale.Spelling = YES -->

## Exception register

An exception is a named and bounded deviation from one guide rule. An exception
does not create a new style. Only this register allows a deviation, and every
exception has a mechanical marker or a linter scope.

### EXC-01: Chromium and Fuchsia platform rules

**Scope:** The `[chrome]` and `[Fuchsia]` sections of the guide.

**Excluded rules:** `chromium::import!`, `rust_gtest_interop`,
`fuchsia_sync::Mutex`, the ban on `std::thread`, and the flat GN file layout.

**Justification:** These rules describe the Chromium and Fuchsia build systems.
Babylon uses a standard Cargo workspace with `std::sync`, `std::thread`, and
`cargo-nextest`. A GN layout and the Chromium import macro have no meaning in
this repository. The platform scope makes the exclusion local and complete.

**Retained obligations:** The code organization rules still apply in full. Babylon
forbids `mod.rs` and allows API implementation in leaf modules only.

### EXC-02: `#[non_exhaustive]` on public enums and structs

**Scope:** Every public enum and every public struct with public fields in the
workspace crates.

**Excluded rule:** The guide rule to mark a public enum or an all-public
struct `#[non_exhaustive]`.

**Justification:** The guide grants this exception to a codebase that commits
to fixing breakage with a large-scale change. Babylon is one repository with
one campaign compiler, one persistence schema, and one commit authority. Every
caller changes in the same commit. Exhaustive matching is load-bearing
compile-time safety here. A new material variant or receipt family must stop
the build until each mechanic handles it. A wildcard arm would hide an
unhandled causal case and can change a world hash without notice.

**Retained obligations:** A new variant or public field updates every consumer
in the same commit. Review rejects a wildcard arm that discards a known
variant. `#[non_exhaustive]` stays allowed where a crate already uses it for a
genuine external boundary.

### EXC-03: Approved prelude glob in `babylon-client`

**Scope:** `rust/crates/babylon-client/`, for `use bevy::prelude::*` only.

**Excluded rule:** The ban on glob imports.

**Justification:** The guide permits a third-party prelude at reviewer
discretion. Bevy derive macros and systems need a large set of traits and
types. A hand-written import list adds noise and breaks on a Bevy upgrade.
The Bevy client is the only crate with this dependency.

**Retained obligations:** The check rejects every other glob import. Three
guide allowances survive unchanged: `use super::*` inside an inline
`#[cfg(test)]` module, `use Enum::*` inside a function that mainly handles
that enum, and `pub use submodule::*` inside a non-leaf module. Defining a
prelude for Babylon code stays banned.

### EXC-04: Retained `Rc` and `Arc` sites

**Scope:** The shared-pointer sites that the check permits. The table lists
each retained site. `Arc<Vec<T>>` becomes `Arc<[T]>` and is not a retained
site.

**Excluded rule:** The preference for unique ownership and borrowing over
`Rc` and `Arc`.

**Justification:** Each site has cross-thread state or a multi-MB immutable
snapshot. The alternative ownership structure would copy the snapshot or
serialize the readers. The guide allows a shared pointer when the borrow
structure would be unreasonably complex. These sites form the smallest set
that Babylon needs.

| Site | Role |
| --- | --- |
| `babylon-kernel/src/geography/roster.rs` `NationalCountyRoster` | Immutable county identifier snapshot shared by every material reader. |
| `babylon-tick/src/material_world/register.rs` `MaterialTickReceipts` | Immutable receipt family held as `Arc<MaterialTickReceipts>` between committed ticks. |
| `babylon-persistence/src/economic_content.rs` `EconomicContentAdmission` | Admitted immutable foundation shared across worker and reader threads. |
| `babylon-persistence/src/archive_worker.rs` `ArchiveWorkerCancellation` | `Arc<AtomicBool>` cancellation flag read by the worker thread. |
| `babylon-client/src/logging.rs` `SinkState` | Cross-thread log writer behind `Arc<Mutex<SinkState>>`. |
| `babylon-ls/tests/protocol.rs` `stderr_buf` | Test harness buffer shared with the spawned language server. |

**Retained obligations:** Every retained site in the table carries a
`// STYLE-EXCEPTION(EXC-04): <reason>` comment. A new retained site needs an
amendment to this register. `Rc<T>` and `Rc<RefCell<T>>` are findings
everywhere. `Arc<Vec<T>>` is a finding everywhere and becomes `Arc<[T]>`.

### EXC-05: Manual byte-table alignment

**Scope:** `babylon-graph/src/state_hash.rs` and
`babylon-tick/src/world_hash.rs`, inside a literal byte table.

**Excluded rule:** The ban on `#[rustfmt::skip]` outside manual alignment.

**Justification:** These tables encode canonical hash input. A column-aligned
literal shows the byte layout, and the formatter would scatter it. The guide
allows `#[rustfmt::skip]` for manual alignment and for generated code. These
tables are hand-maintained data, so the alignment case applies.

**Retained obligations:** Each skipped block carries a
`// STYLE-EXCEPTION(EXC-05): manual byte-table alignment` comment. A skip for
personal style, or outside a table, is a finding.

## Changing this register

A new exception weakens a governed rule. It needs Director approval and an
ADR amendment that states the scope, the justification, and the retained
obligations. The amendment updates this page and the linter in one commit. An
inline comment alone never creates an exception, and a comment cannot widen an
existing scope.

## Related records

- ADR286 records the adoption decision and the alternatives.
- `docs/agents/coding-standards.md` carries the repository-wide source rules.
- `docs/agents/testing.md` describes the current test gates.
