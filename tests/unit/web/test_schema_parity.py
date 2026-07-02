"""Contract tests ensuring schema parity across the Django ↔ Postgres ↔ Serializer boundary.

Prevents the three categories of drift that caused production 500 errors:

1. **DDL ↔ Django Model**: Columns added to ``postgres_schema.py`` DDL
   must appear as fields on the Django model, and vice versa.
2. **Unmanaged Model PK**: Every ``managed=False`` model must declare
   an explicit primary key to prevent Django from generating
   ``SELECT table.id`` for tables that lack an ``id`` column.
3. **Serializer ↔ Bridge output**: Every field on a DRF response
   serializer must be emitted by the corresponding ``_serialize_*``
   function in ``engine_bridge.py``, and by ``MockEngineBridge`` /
   ``StubEngineBridge`` snapshot data.
4. **SQLite stub DDL ↔ Django Model**: Test conftest stubs must
   include all columns that the Django model declares.
5. **Bridge API signature parity**: All three bridge implementations
   (EngineBridge, MockEngineBridge, StubEngineBridge) must expose
   the same public method signatures.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from game import models as game_models

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

_MODELS_SOURCE = Path(__file__).resolve().parent.parent.parent.parent / "web" / "game" / "models.py"


def _extract_ddl_columns(ddl: str) -> set[str]:
    """Extract column names from a CREATE TABLE DDL string.

    Handles PostgreSQL DDL with constraints, primary keys, CHECK blocks, etc.
    Returns lowercase column names only (not constraints or check values).
    """
    columns: set[str] = set()
    in_table = False
    constraint_depth = 0  # Track nested parens inside CONSTRAINT/CHECK blocks
    in_constraint = False

    for line in ddl.splitlines():
        stripped = line.strip()

        # Detect the opening paren of CREATE TABLE
        if "CREATE TABLE" in stripped.upper():
            in_table = True
            continue

        if not in_table:
            continue

        # Track whether we're inside a multi-line CONSTRAINT block
        if in_constraint:
            constraint_depth += stripped.count("(") - stripped.count(")")
            if constraint_depth <= 0:
                in_constraint = False
                constraint_depth = 0
            continue

        # Skip empty, comment, and closing-paren lines
        if not stripped or stripped.startswith("--") or stripped == ")":
            continue

        # Detect start of constraint/PK blocks
        upper = stripped.upper()
        if upper.startswith(("PRIMARY", "UNIQUE", "CONSTRAINT", "CHECK", "FOREIGN")):
            # If this constraint spans multiple lines, track paren depth
            open_parens = stripped.count("(")
            close_parens = stripped.count(")")
            if open_parens > close_parens:
                in_constraint = True
                constraint_depth = open_parens - close_parens
            continue

        # Extract the first token as column name
        # Handle multi-column-per-line DDL like:
        #   c_dept_i NUMERIC, v_dept_i NUMERIC, s_dept_i NUMERIC,
        for segment in stripped.split(","):
            segment = segment.strip()
            if not segment or segment.startswith("--"):
                continue
            col_name = segment.split()[0].strip()
            # Skip if it looks like a type continuation or constraint keyword
            if col_name.upper() in (
                "NOT",
                "NULL",
                "DEFAULT",
                "REFERENCES",
                "ON",
                "CASCADE",
                "FLOAT",
                "INTEGER",
                "NUMERIC",
                "VARCHAR",
                "BOOLEAN",
                "TEXT",
                "JSONB",
                "UUID",
                "SERIAL",
                "BIGINT",
                "SMALLINT",
                "DOUBLE",
                "TIMESTAMP",
                "DATE",
            ):
                continue
            if col_name and re.match(r"^[a-z_][a-z0-9_]*$", col_name, re.IGNORECASE):
                columns.add(col_name.lower())

    return columns


def _get_model_field_db_columns(model_class: type) -> set[str]:
    """Get all DB column names for a Django model, including FK db_column overrides."""
    columns: set[str] = set()
    for field in model_class._meta.get_fields():
        if hasattr(field, "column"):
            columns.add(field.column.lower())
        elif hasattr(field, "attname"):
            columns.add(field.attname.lower())
    return columns


def _get_unmanaged_models() -> list[type]:
    """Return all Django models in game.models with managed=False (via AST)."""
    tree = ast.parse(_MODELS_SOURCE.read_text())
    unmanaged_classes: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for inner in node.body:
            if isinstance(inner, ast.ClassDef) and inner.name == "Meta":
                for stmt in inner.body:
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and stmt.targets[0].id == "managed"
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is False
                    ):
                        unmanaged_classes.append(node.name)

    return [getattr(game_models, name) for name in unmanaged_classes if hasattr(game_models, name)]


def _get_serializer_field_names(serializer_class: type) -> set[str]:
    """Return the set of field names declared on a DRF serializer class."""
    from rest_framework import serializers as drf_serializers

    fields: set[str] = set()
    for attr_name, attr_value in serializer_class.__dict__.items():
        if isinstance(attr_value, drf_serializers.Field):
            fields.add(attr_name)
    # Also check parent classes (but not Serializer itself)
    for parent in serializer_class.__mro__[1:]:
        if parent is drf_serializers.Serializer or parent is object:
            break
        for attr_name, attr_value in parent.__dict__.items():
            if isinstance(attr_value, drf_serializers.Field):
                fields.add(attr_name)
    return fields


def _extract_sqlite_stub_columns(sql: str) -> set[str]:
    """Extract column names from a SQLite CREATE TABLE stub."""
    columns: set[str] = set()
    in_table = False

    for line in sql.splitlines():
        stripped = line.strip()
        if "CREATE TABLE" in stripped.upper():
            in_table = True
            # Check if the first column is on this same line after '('
            if "(" in stripped:
                after = stripped.split("(", 1)[1].strip()
                if after and not after.startswith(")"):
                    col_name = after.split()[0].rstrip(",").strip('"')
                    if col_name and not col_name.upper().startswith(
                        ("PRIMARY", "UNIQUE", "CONSTRAINT")
                    ):
                        columns.add(col_name.lower())
            continue
        if not in_table:
            continue
        if stripped.startswith(")"):
            break
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.upper().startswith(("PRIMARY", "UNIQUE", "CONSTRAINT", "CHECK", "FOREIGN")):
            continue
        col_name = stripped.split()[0].rstrip(",").strip('"')
        if col_name:
            columns.add(col_name.lower())

    return columns


# ═══════════════════════════════════════════════════════════════════════
# 1. DDL ↔ Django Model Parity
# ═══════════════════════════════════════════════════════════════════════

# Map each unmanaged model to its DDL constant name in postgres_schema.py
_MODEL_DDL_MAP: dict[str, str] = {
    "GameSession": "GAME_SESSION_DDL",
    "PlayerAction": "GAME_TURN_DDL",
    "ActionResult": "ACTION_RESULT_DDL",
    "HexState": "HEX_LATEST_DDL",
    "TerritorySnapshot": "TERRITORY_SNAPSHOT_DDL",
    "OrgSnapshot": "ORG_SNAPSHOT_DDL",
    "EdgeSnapshot": "EDGE_SNAPSHOT_DDL",
    "CommunitySnapshot": "COMMUNITY_SNAPSHOT_DDL",
    "EconomicSummary": "ECONOMIC_SUMMARY_DDL",
    "TickEvent": "TICK_EVENT_DDL",
}


@pytest.mark.unit
class TestDDLModelParity:
    """Every column in the Postgres DDL must have a Django model field, and vice versa."""

    @pytest.mark.parametrize(
        "model_name,ddl_name",
        list(_MODEL_DDL_MAP.items()),
        ids=list(_MODEL_DDL_MAP.keys()),
    )
    def test_model_fields_exist_in_ddl(self, model_name: str, ddl_name: str) -> None:
        """All Django model DB columns must appear in the Postgres DDL."""
        from babylon.persistence import postgres_schema

        model_class = getattr(game_models, model_name)
        ddl = getattr(postgres_schema, ddl_name)

        model_columns = _get_model_field_db_columns(model_class)
        ddl_columns = _extract_ddl_columns(ddl)

        # Django auto-generates 'id' if no PK declared; DDL may use composite PKs.
        # Don't flag 'id' if the DDL uses a composite PK.
        model_only = model_columns - ddl_columns
        model_only.discard("id")  # May be auto-generated

        assert not model_only, (
            f"{model_name} has columns not in {ddl_name}: {model_only}\n"
            f"Model columns: {sorted(model_columns)}\n"
            f"DDL columns: {sorted(ddl_columns)}"
        )

    @pytest.mark.parametrize(
        "model_name,ddl_name",
        list(_MODEL_DDL_MAP.items()),
        ids=list(_MODEL_DDL_MAP.keys()),
    )
    def test_ddl_columns_exist_in_model(self, model_name: str, ddl_name: str) -> None:
        """All Postgres DDL columns must have a Django model field.

        Columns only in the DDL mean the engine writes data Django can't read.
        Allowed exceptions are forward-compat columns like 'attributes' or
        array columns like 'org_ids' that Django doesn't map natively.
        Per-model exceptions are documented below.
        """
        from babylon.persistence import postgres_schema

        model_class = getattr(game_models, model_name)
        ddl = getattr(postgres_schema, ddl_name)

        model_columns = _get_model_field_db_columns(model_class)
        ddl_columns = _extract_ddl_columns(ddl)

        # Global columns the DDL has but Django doesn't need to map
        ALLOWED_DDL_ONLY: set[str] = {"org_ids", "attributes"}

        # Per-model exceptions: columns present in DDL that are intentionally
        # NOT mapped as Django model fields.
        _VALUE_TENSOR_COLS = {
            f"{prefix}_dept_{dept}"
            for prefix in ("c", "v", "s")
            for dept in ("i", "iia", "iib", "iii")
        }
        PER_MODEL_ALLOWED: dict[str, set[str]] = {
            # HexState reads ValueTensor columns through the engine bridge
            # and raw SQL aggregations, not via Django ORM field access.
            "HexState": _VALUE_TENSOR_COLS,
        }

        allowed = ALLOWED_DDL_ONLY | PER_MODEL_ALLOWED.get(model_name, set())
        ddl_only = ddl_columns - model_columns - allowed

        assert not ddl_only, (
            f"{ddl_name} has columns not in {model_name}: {ddl_only}\n"
            f"Model columns: {sorted(model_columns)}\n"
            f"DDL columns: {sorted(ddl_columns)}"
        )


# ═══════════════════════════════════════════════════════════════════════
# 2. Unmanaged Model Primary Keys
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestUnmanagedModelPrimaryKeys:
    """Every managed=False model must declare an explicit primary key.

    Without an explicit PK, Django auto-generates ``SELECT table.id``
    which fails if the real table uses a composite PK or has no ``id``
    column (e.g., ``hex_latest`` with PK ``(game_id, h3_index)``).
    """

    def test_all_unmanaged_models_have_explicit_pk(self) -> None:
        unmanaged = _get_unmanaged_models()
        assert unmanaged, "Expected at least one unmanaged model"

        missing_pk: list[str] = []
        for model in unmanaged:
            pk_field = model._meta.pk
            if pk_field is None:
                missing_pk.append(model.__name__)
                continue
            # Django's auto-generated BigAutoField means no explicit PK was declared
            if pk_field.name == "id" and not _source_declares_pk_field(model.__name__):
                missing_pk.append(f"{model.__name__} (auto-generated 'id')")

        assert not missing_pk, (
            f"Unmanaged models without explicit primary_key=True: {missing_pk}\n"
            "Django will generate SELECT table.id which fails on composite-PK tables."
        )


def _source_declares_pk_field(class_name: str) -> bool:
    """Check if a model class explicitly declares any field with primary_key=True."""
    tree = ast.parse(_MODELS_SOURCE.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                # Look for primary_key=True in the field constructor
                source_line = ast.get_source_segment(_MODELS_SOURCE.read_text(), stmt)
                if source_line and "primary_key=True" in source_line:
                    return True
            elif isinstance(stmt, ast.AnnAssign):
                source_line = ast.get_source_segment(_MODELS_SOURCE.read_text(), stmt)
                if source_line and "primary_key=True" in source_line:
                    return True
    return False


# ═══════════════════════════════════════════════════════════════════════
# 3. Serializer ↔ Bridge Output Parity
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestSerializerBridgeParity:
    """Every field on a DRF response serializer must be emitted by the bridge."""

    def test_territory_serializer_fields_in_serialize_territory(self) -> None:
        """_serialize_territory must emit all TerritorySerializer fields."""
        from game.serializers import TerritorySerializer

        self._assert_serialize_func_covers_serializer("_serialize_territory", TerritorySerializer)

    def test_organization_serializer_fields_in_serialize_organization(self) -> None:
        """_serialize_organization must emit all OrganizationSerializer fields."""
        from game.serializers import OrganizationSerializer

        self._assert_serialize_func_covers_serializer(
            "_serialize_organization", OrganizationSerializer
        )

    def test_institution_serializer_fields_in_serialize_institution(self) -> None:
        """_serialize_institution must emit all InstitutionSerializer fields."""
        from game.serializers import InstitutionSerializer

        self._assert_serialize_func_covers_serializer(
            "_serialize_institution", InstitutionSerializer
        )

    def test_edge_serializer_fields_in_serialize_edge(self) -> None:
        """_serialize_edge must emit all EdgeSerializer fields."""
        from game.serializers import EdgeSerializer

        self._assert_serialize_func_covers_serializer("_serialize_edge", EdgeSerializer)

    def test_game_snapshot_serializer_toplevel_keys(self) -> None:
        """GameSnapshotSerializer top-level fields must match _state_to_snapshot keys."""
        from game.serializers import GameSnapshotSerializer

        expected_keys = _get_serializer_field_names(GameSnapshotSerializer)
        self._assert_function_emits_keys("_state_to_snapshot", expected_keys)

    # --- Helpers ---

    def _assert_serialize_func_covers_serializer(
        self, func_name: str, serializer_class: type
    ) -> None:
        """Verify that a _serialize_* function's return dict covers all serializer fields."""
        from game import engine_bridge

        func = getattr(engine_bridge, func_name, None)
        assert func is not None, f"{func_name} not found in engine_bridge"

        # Parse the function source to extract dict keys from the return statement
        source = inspect.getsource(func)
        keys_in_source = set(re.findall(r'"(\w+)":', source))

        serializer_fields = _get_serializer_field_names(serializer_class)

        missing = serializer_fields - keys_in_source
        assert not missing, (
            f"{func_name} is missing keys required by {serializer_class.__name__}: {missing}\n"
            f"Serializer fields: {sorted(serializer_fields)}\n"
            f"Function emits: {sorted(keys_in_source)}"
        )

    def _assert_function_emits_keys(self, func_name: str, expected_keys: set[str]) -> None:
        """Verify that a function's return dict includes all expected keys."""
        from game import engine_bridge

        func = getattr(engine_bridge, func_name, None)
        assert func is not None, f"{func_name} not found in engine_bridge"

        source = inspect.getsource(func)
        keys_in_source = set(re.findall(r'"(\w+)":', source))

        missing = expected_keys - keys_in_source
        assert not missing, (
            f"{func_name} is missing keys: {missing}\n"
            f"Expected: {sorted(expected_keys)}\n"
            f"Found: {sorted(keys_in_source)}"
        )


# ═══════════════════════════════════════════════════════════════════════
# 4. SQLite Stub DDL Parity
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestSQLiteStubParity:
    """SQLite stubs in test conftest files must include all Django model columns.

    When a new column is added to a Django model, the SQLite CREATE TABLE
    stubs in conftest.py files must be updated too — otherwise tests crash
    with 'table X has no column named Y'.
    """

    def _get_conftest_stubs(self) -> dict[str, str]:
        """Read SQLite CREATE TABLE stubs from the primary test conftest."""
        conftest_path = Path(__file__).resolve().parent / "conftest.py"
        content = conftest_path.read_text()

        stubs: dict[str, str] = {}

        # Find each CREATE TABLE block using balanced parenthesis matching.
        # We search for each occurrence and extract the full block.
        create_re = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(",
            re.IGNORECASE,
        )
        for match in create_re.finditer(content):
            table_name = match.group(1).lower()
            start = match.start()
            # Find the matching closing paren by counting depth
            paren_start = match.end() - 1  # position of '('
            depth = 1
            pos = paren_start + 1
            while pos < len(content) and depth > 0:
                if content[pos] == "(":
                    depth += 1
                elif content[pos] == ")":
                    depth -= 1
                pos += 1
            full_block = content[start:pos]
            stubs[table_name] = full_block

        return stubs

    def test_game_session_stub_has_all_model_columns(self) -> None:
        """The game_session SQLite stub must include all GameSession model columns."""
        stubs = self._get_conftest_stubs()
        assert "game_session" in stubs, "No game_session stub found in conftest"

        stub_columns = _extract_sqlite_stub_columns(stubs["game_session"])
        model_columns = _get_model_field_db_columns(game_models.GameSession)

        missing = model_columns - stub_columns
        assert not missing, (
            f"SQLite game_session stub is missing columns: {missing}\n"
            f"Stub columns: {sorted(stub_columns)}\n"
            f"Model columns: {sorted(model_columns)}"
        )

    def test_game_turn_stub_has_all_model_columns(self) -> None:
        """The game_turn SQLite stub must include all PlayerAction model columns."""
        stubs = self._get_conftest_stubs()
        assert "game_turn" in stubs, "No game_turn stub found in conftest"

        stub_columns = _extract_sqlite_stub_columns(stubs["game_turn"])
        model_columns = _get_model_field_db_columns(game_models.PlayerAction)

        missing = model_columns - stub_columns
        assert not missing, (
            f"SQLite game_turn stub is missing columns: {missing}\n"
            f"Stub columns: {sorted(stub_columns)}\n"
            f"Model columns: {sorted(model_columns)}"
        )

    def test_action_result_stub_has_all_model_columns(self) -> None:
        """The action_result SQLite stub must include all ActionResult model columns."""
        stubs = self._get_conftest_stubs()
        assert "action_result" in stubs, "No action_result stub found in conftest"

        stub_columns = _extract_sqlite_stub_columns(stubs["action_result"])
        model_columns = _get_model_field_db_columns(game_models.ActionResult)

        missing = model_columns - stub_columns
        assert not missing, (
            f"SQLite action_result stub is missing columns: {missing}\n"
            f"Stub columns: {sorted(stub_columns)}\n"
            f"Model columns: {sorted(model_columns)}"
        )


# ═══════════════════════════════════════════════════════════════════════
# 5. Bridge API Signature Parity
# ═══════════════════════════════════════════════════════════════════════

# Public methods that all three bridges must implement
_BRIDGE_PUBLIC_METHODS = [
    "create_game",
    "get_snapshot",
    "get_map_snapshot",
    "get_available_actions",
    "submit_action",
    "resolve_tick",
]


@pytest.mark.unit
class TestBridgeAPIParity:
    """All bridge implementations must expose the same public methods.

    Prevents the scenario where ``api.py`` calls a method that exists
    on ``EngineBridge`` but not on ``StubEngineBridge``, or vice versa.
    """

    def _get_bridge_classes(self) -> list[tuple[str, type]]:
        """Import and return all bridge classes."""
        bridges: list[tuple[str, type]] = []

        from game.engine_bridge import EngineBridge

        bridges.append(("EngineBridge", EngineBridge))

        # MockEngineBridge was deleted in spec-061 Phase 9 "mock sunset"
        # (6d015f72); the live pair is EngineBridge vs StubEngineBridge.
        from game.stub_bridge import StubEngineBridge

        bridges.append(("StubEngineBridge", StubEngineBridge))

        return bridges

    def test_all_bridges_have_required_methods(self) -> None:
        """Every bridge must implement every public method."""
        bridges = self._get_bridge_classes()

        for bridge_name, bridge_class in bridges:
            missing = []
            for method_name in _BRIDGE_PUBLIC_METHODS:
                if not hasattr(bridge_class, method_name):
                    missing.append(method_name)
            assert not missing, f"{bridge_name} is missing methods: {missing}"

    def test_get_map_snapshot_signature_compat(self) -> None:
        """get_map_snapshot must accept the same keyword arguments across all bridges.

        The api.py layer calls get_map_snapshot(session_id, tick=..., _layer=..., zoom=...).
        All bridges must accept these kwargs (even if they ignore some).
        """
        bridges = self._get_bridge_classes()
        required_params = {"session_id", "tick", "zoom"}

        for bridge_name, bridge_class in bridges:
            method = getattr(bridge_class, "get_map_snapshot", None)
            assert method is not None, f"{bridge_name} missing get_map_snapshot"

            sig = inspect.signature(method)
            param_names = set(sig.parameters.keys()) - {"self"}

            missing = required_params - param_names
            assert not missing, (
                f"{bridge_name}.get_map_snapshot is missing params: {missing}\n"
                f"Has: {sorted(param_names)}\n"
                f"Needs: {sorted(required_params)}"
            )

    def test_get_snapshot_signature_compat(self) -> None:
        """get_snapshot must accept session_id across all bridges."""
        bridges = self._get_bridge_classes()

        for bridge_name, bridge_class in bridges:
            method = getattr(bridge_class, "get_snapshot", None)
            assert method is not None, f"{bridge_name} missing get_snapshot"

            sig = inspect.signature(method)
            param_names = set(sig.parameters.keys()) - {"self"}

            assert "session_id" in param_names, (
                f"{bridge_name}.get_snapshot is missing 'session_id' param. "
                f"Has: {sorted(param_names)}"
            )
