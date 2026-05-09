# Contract: `SourceRegistry`

**Module**: `src/babylon/core/protocol_kit.py`
**Introduced by**: Spec 058 / FR-004, FR-006 (US1, Bundle 1)
**Status**: Draft (this is the contract; implementation lands in commits 4 and 6)

This contract specifies the public surface of `SourceRegistry`. Companion contracts: [`protocol_kit.md`](protocol_kit.md), [`bea_mappings.md`](bea_mappings.md).

---

## 1. Public surface

```python
class SourceRegistry:
    DEFAULT_VARIANT: str = "default"
    TEST_VARIANT: str = "test"

    def __init__(self) -> None: ...
    def register(
        self,
        protocol: type,
        factory: Callable[[], object],
        *,
        variant: str = DEFAULT_VARIANT,
    ) -> None: ...
    def get(self, protocol: type, *, variant: str = DEFAULT_VARIANT) -> object: ...
    def has(self, protocol: type, *, variant: str = DEFAULT_VARIANT) -> bool: ...
    def builtin_economics(self) -> "SourceRegistry": ...
```

---

## 2. Semantic guarantees

### `register(protocol, factory, *, variant)`

| Guarantee | Detail |
|-----------|--------|
| **Type-keyed** | The `protocol` argument is a Python class (typically a `Protocol`). Two registrations with the same `protocol` and `variant` are considered the same key. |
| **Re-registration replaces silently** | Calling `register(P, f1); register(P, f2)` is allowed; the second call replaces `f1`. No warning, no exception. Tests use this to swap implementations. |
| **`variant` discriminates** | `register(P, f_prod, variant="default"); register(P, f_test, variant="test")` registers two independent factories for the same Protocol. `get(P)` returns the default; `get(P, variant="test")` returns the test variant. |
| **Replaced factory's instances unaffected** | If `register(P, f1)` was called, `inst1 = registry.get(P)` was returned, and then `register(P, f2)` is called, `inst1` continues to behave per `f1`. The replacement only affects subsequent `get(P)` calls. Tests that need a clean slate SHOULD construct a fresh `SourceRegistry`. |
| **No registration ordering constraint** | Factories may register in any order. `builtin_economics()` registers them in a deterministic order (matters for documentation; does not matter for behavior). |

### `get(protocol, *, variant)`

| Guarantee | Detail |
|-----------|--------|
| **Construction per call** | Every `get(P)` call invokes the registered factory and returns a *new instance*. Callers that need a singleton MUST cache the instance themselves. (Rationale: simpler semantics; per-call construction matches the existing `create_*_services()` behavior; tests that need a singleton cache it in a fixture.) |
| **`LookupError` on unknown** | Raises `LookupError(f"No {variant!r} implementation registered for {P.__name__}")` if `(P, variant)` is not registered. NOT `KeyError` — `LookupError` is the broader Python class that includes `KeyError`; we use the broader form because the "key" is a `(type, str)` tuple, not a `dict` key directly. |
| **Factory exceptions propagate** | If the factory itself raises (e.g., the constructor raises `ValueError` for bad config), `get` re-raises that exception unchanged. No wrapping. |

### `has(protocol, *, variant)`

| Guarantee | Detail |
|-----------|--------|
| **Pure check, no construction** | Returns `True` if `(P, variant)` is registered, `False` otherwise. Does NOT invoke the factory. Useful for tests that probe the registry without paying construction cost. |

### `builtin_economics()`

| Guarantee | Detail |
|-----------|--------|
| **Self-returning (fluent chain)** | Returns `self`, enabling `SourceRegistry().builtin_economics().get(BEADataSource)`. |
| **Idempotent** | Calling `builtin_economics()` twice on the same registry re-registers each entry. Because re-registration replaces silently, the second call is a no-op behaviorally. |
| **At Bundle 1 commit-6 time**: registers exactly the 10 `melt/` + `gamma/` `Default*` classes that have migrated to `CachedSource[T]` in commit 5. The remaining 51 `Default*` classes continue to be wired by their original `create_*_services()` shim until ADR-002's "Steps 5+" follow-up bundle migrates them. |
| **Module-level import side effects** | Importing `babylon.core.protocol_kit` does NOT call `builtin_economics()`. The caller MUST do it explicitly: `registry = SourceRegistry().builtin_economics()`. The 4 `create_*_services()` shims in `economics/factory.py` perform this call internally per FR-006. |

---

## 3. Migration shims (FR-006)

Per Spec 058 / FR-006: the existing 4 `create_*_services()` function names are kept as thin shims for one release cycle. Each shim is ~3 lines:

```python
# economics/factory.py — post-Bundle-1 shape (FR-006, ~150 LOC total)

from babylon.core.protocol_kit import SourceRegistry

_BUILTIN_REGISTRY: SourceRegistry | None = None


def _get_builtin_registry() -> SourceRegistry:
    """Lazy-construct the process-wide builtin registry."""
    global _BUILTIN_REGISTRY
    if _BUILTIN_REGISTRY is None:
        _BUILTIN_REGISTRY = SourceRegistry().builtin_economics()
    return _BUILTIN_REGISTRY


def create_economics_services(defines: GameDefines) -> EconomicsServices:
    """[Deprecated shim] Returns an EconomicsServices bundle.

    This shim is preserved for callers that haven't migrated to
    `_get_builtin_registry().get(P)` directly. The shim will be removed in
    Bundle 3 (post-spec-057 cleanup) once all callers are migrated.
    """
    reg = _get_builtin_registry()
    return EconomicsServices(
        bea_source=reg.get(BEADataSource),
        qcew_source=reg.get(QCEWDataSource),
        cpi_source=reg.get(CPIDataSource),
        # ... (same signature as before; just delegates)
    )

# Same shape for create_financial_services, create_circulation_services, create_vol1_services
```

The 3 `load_*_series_from_db` helpers in the original `economics/factory.py` (per R5 in research.md) either:
- (a) move to a new `economics/_db_helpers.py` module
- (b) inline into the relevant `Default*` `_fetch` body now that those classes use `CachedSource[T]`

Planner picks at commit 6 time based on call-site count. Both options keep `factory.py` under 150 LOC.

---

## 4. Test contract

`tests/unit/core/test_protocol_kit.py` MUST cover (in addition to the `CachedSource` tests):

1. **Register and get**: `reg.register(P, lambda: Impl()); assert isinstance(reg.get(P), Impl)`
2. **Get unknown raises `LookupError`**: `with pytest.raises(LookupError): reg.get(NeverRegistered)`
3. **`has` returns `True` for registered, `False` for unknown**
4. **Variant discrimination**: `reg.register(P, fp, variant="default"); reg.register(P, ft, variant="test"); assert reg.get(P) is not reg.get(P, variant="test")`
5. **Re-registration replaces**: `reg.register(P, f1); reg.register(P, f2); assert reg.get(P)` was constructed by `f2`
6. **Replaced factory's previous instance unaffected**: `inst1 = reg.get(P); reg.register(P, f2); assert isinstance(inst1, OriginalImpl)` — this verifies the "no retroactive update" guarantee
7. **Per-call construction**: `inst1 = reg.get(P); inst2 = reg.get(P); assert inst1 is not inst2`
8. **Factory exceptions propagate**: `reg.register(P, lambda: (_ for _ in ()).throw(ValueError("x"))); with pytest.raises(ValueError): reg.get(P)`
9. **`builtin_economics` is self-returning**: `assert SourceRegistry().builtin_economics() is itself`
10. **`builtin_economics` idempotent**: calling twice does not raise; second call returns same registry

`tests/unit/economics/test_factory_shims.py` MUST cover (FR-006 acceptance):

11. **Each `create_*_services()` shim returns an instance equivalent to the pre-Bundle-1 baseline**: structural equality on the returned `EconomicsServices` bundle's source-instance types (e.g., `isinstance(services.bea_source, DefaultBEASource)`)
12. **Process-wide singleton**: two `create_economics_services()` calls return services that share the same underlying registered factories (the registry instance is global)
13. **`factory.py` is under 150 LOC**: `assert sum(1 for _ in open(factory_path)) < 150` (mechanical line-count assertion that codifies SC-004)

---

## 5. Out-of-scope for Bundle 1

- A test-side `SourceRegistry.snapshot()` / `restore()` API for atomic save/restore of registry state across test boundaries (not needed for the 10-class migration; can be added later if testing needs grow)
- Async factories (registry is synchronous; matches Babylon's single-threaded engine)
- Multi-process registries (Babylon is single-process per Constitution X — no Docker, no multi-process supervision)
- Lazy imports beyond what's already in `builtin_economics()` (the imports inside the method are sufficient to break import cycles)
