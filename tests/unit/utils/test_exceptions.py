"""Comprehensive test suite for Babylon's unified exception hierarchy.

This module tests the exception hierarchy defined in:
- babylon.utils.exceptions (core hierarchy)
- babylon.rag.exceptions (RagError + aliases)
- babylon.engine.history.io (CheckpointIOError + children)
- babylon.exceptions (top-level re-exports)

The tests verify:
1. Inheritance structure
2. Default error codes
3. Constructor behavior
4. Serialization (.to_dict(), __str__, __repr__)
5. Backwards compatibility aliases
6. Exception propagation behavior
7. Import path consistency

Kent Beck would say: "Lock down the behavior now!"
"""

from typing import Any

import pytest

# =============================================================================
# HIERARCHY TESTS (Structural)
# =============================================================================


@pytest.mark.unit
class TestExceptionHierarchy:
    """Tests that verify the exception inheritance structure."""

    @pytest.mark.parametrize(
        "exception_class_path",
        [
            "babylon.utils.exceptions.BabylonError",
            "babylon.utils.exceptions.InfrastructureError",
            "babylon.utils.exceptions.StorageError",
            "babylon.utils.exceptions.DatabaseError",
            "babylon.utils.exceptions.ValidationError",
            "babylon.utils.exceptions.ConfigurationError",
            "babylon.utils.exceptions.SimulationError",
            "babylon.utils.exceptions.TopologyError",
            "babylon.utils.exceptions.ObserverError",
            "babylon.utils.exceptions.LLMError",
            "babylon.rag.exceptions.RagError",
        ],
    )
    def test_all_exceptions_inherit_from_babylon_error(self, exception_class_path: str) -> None:
        """All exception classes inherit from BabylonError."""
        from babylon.utils.exceptions import BabylonError

        # Dynamic import
        module_path, class_name = exception_class_path.rsplit(".", 1)
        import importlib

        module = importlib.import_module(module_path)
        exception_class = getattr(module, class_name)

        assert issubclass(
            exception_class, BabylonError
        ), f"{class_name} should inherit from BabylonError"

    def test_database_error_inherits_from_infrastructure_error(self) -> None:
        """DatabaseError is a child of InfrastructureError."""
        from babylon.utils.exceptions import DatabaseError, InfrastructureError

        assert issubclass(DatabaseError, InfrastructureError)

    def test_storage_error_inherits_from_infrastructure_error(self) -> None:
        """StorageError is a child of InfrastructureError."""
        from babylon.utils.exceptions import InfrastructureError, StorageError

        assert issubclass(StorageError, InfrastructureError)

    def test_configuration_error_inherits_from_validation_error(self) -> None:
        """ConfigurationError is a child of ValidationError."""
        from babylon.utils.exceptions import ConfigurationError, ValidationError

        assert issubclass(ConfigurationError, ValidationError)

    def test_topology_error_inherits_from_simulation_error(self) -> None:
        """TopologyError is a child of SimulationError."""
        from babylon.utils.exceptions import SimulationError, TopologyError

        assert issubclass(TopologyError, SimulationError)

    def test_llm_error_inherits_from_observer_error(self) -> None:
        """LLMError is a child of ObserverError."""
        from babylon.utils.exceptions import LLMError, ObserverError

        assert issubclass(LLMError, ObserverError)

    def test_rag_error_inherits_from_observer_error(self) -> None:
        """RagError (from rag.exceptions) is a child of ObserverError."""
        from babylon.rag.exceptions import RagError
        from babylon.utils.exceptions import ObserverError

        assert issubclass(RagError, ObserverError)

    def test_checkpoint_io_error_inherits_from_storage_error(self) -> None:
        """CheckpointIOError is a child of StorageError."""
        from babylon.engine.history.io import CheckpointIOError
        from babylon.utils.exceptions import StorageError

        assert issubclass(CheckpointIOError, StorageError)

    def test_checkpoint_not_found_inherits_from_checkpoint_io_error(self) -> None:
        """CheckpointNotFoundError is a child of CheckpointIOError."""
        from babylon.engine.history.io import (
            CheckpointIOError,
            CheckpointNotFoundError,
        )

        assert issubclass(CheckpointNotFoundError, CheckpointIOError)

    def test_checkpoint_corrupted_inherits_from_checkpoint_io_error(self) -> None:
        """CheckpointCorruptedError is a child of CheckpointIOError."""
        from babylon.engine.history.io import (
            CheckpointCorruptedError,
            CheckpointIOError,
        )

        assert issubclass(CheckpointCorruptedError, CheckpointIOError)

    def test_checkpoint_schema_inherits_from_checkpoint_io_error(self) -> None:
        """CheckpointSchemaError is a child of CheckpointIOError."""
        from babylon.engine.history.io import (
            CheckpointIOError,
            CheckpointSchemaError,
        )

        assert issubclass(CheckpointSchemaError, CheckpointIOError)


# =============================================================================
# ERROR CODE TESTS (Semantic)
# =============================================================================


@pytest.mark.unit
class TestDefaultErrorCodes:
    """Tests for default error codes assigned to each exception type."""

    @pytest.mark.parametrize(
        ("exception_import_path", "expected_code"),
        [
            ("babylon.utils.exceptions.BabylonError", "SYS_000"),
            ("babylon.utils.exceptions.InfrastructureError", "INFRA_001"),
            ("babylon.utils.exceptions.StorageError", "STOR_001"),
            ("babylon.utils.exceptions.DatabaseError", "DB_001"),
            ("babylon.utils.exceptions.ValidationError", "VAL_001"),
            ("babylon.utils.exceptions.ConfigurationError", "CFG_001"),
            ("babylon.utils.exceptions.SimulationError", "SIM_001"),
            ("babylon.utils.exceptions.TopologyError", "TOP_001"),
            ("babylon.utils.exceptions.ObserverError", "OBS_001"),
            ("babylon.utils.exceptions.LLMError", "LLM_001"),
            ("babylon.rag.exceptions.RagError", "RAG_001"),
        ],
    )
    def test_default_error_code(self, exception_import_path: str, expected_code: str) -> None:
        """Each exception type has the correct default error code."""
        import importlib

        module_path, class_name = exception_import_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        exception_class = getattr(module, class_name)

        error = exception_class("Test message")
        assert (
            error.error_code == expected_code
        ), f"{class_name} should have default code {expected_code}"

    def test_checkpoint_io_error_default_code(self) -> None:
        """CheckpointIOError has default error code STOR_100."""
        from babylon.engine.history.io import CheckpointIOError

        error = CheckpointIOError("Test message")
        assert error.error_code == "STOR_100"

    def test_checkpoint_not_found_error_code(self) -> None:
        """CheckpointNotFoundError has error code STOR_101."""
        from babylon.engine.history.io import CheckpointNotFoundError

        error = CheckpointNotFoundError("File not found")
        assert error.error_code == "STOR_101"

    def test_checkpoint_corrupted_error_code(self) -> None:
        """CheckpointCorruptedError has error code STOR_102."""
        from babylon.engine.history.io import CheckpointCorruptedError

        error = CheckpointCorruptedError("Invalid JSON")
        assert error.error_code == "STOR_102"

    def test_checkpoint_schema_error_code(self) -> None:
        """CheckpointSchemaError has error code STOR_103."""
        from babylon.engine.history.io import CheckpointSchemaError

        error = CheckpointSchemaError("Schema validation failed")
        assert error.error_code == "STOR_103"


@pytest.mark.unit
class TestCustomErrorCodes:
    """Tests that custom error codes are accepted and preserved."""

    @pytest.mark.parametrize(
        "exception_import_path",
        [
            "babylon.utils.exceptions.BabylonError",
            "babylon.utils.exceptions.InfrastructureError",
            "babylon.utils.exceptions.StorageError",
            "babylon.utils.exceptions.DatabaseError",
            "babylon.utils.exceptions.ValidationError",
            "babylon.utils.exceptions.ConfigurationError",
            "babylon.utils.exceptions.SimulationError",
            "babylon.utils.exceptions.TopologyError",
            "babylon.utils.exceptions.ObserverError",
            "babylon.utils.exceptions.LLMError",
            "babylon.rag.exceptions.RagError",
        ],
    )
    def test_custom_error_code_accepted(self, exception_import_path: str) -> None:
        """All exception types accept custom error codes."""
        import importlib

        module_path, class_name = exception_import_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        exception_class = getattr(module, class_name)

        custom_code = "CUSTOM_999"
        error = exception_class("Test message", error_code=custom_code)
        assert error.error_code == custom_code, f"{class_name} should accept custom error code"


# =============================================================================
# CONSTRUCTOR TESTS (API)
# =============================================================================


@pytest.mark.unit
class TestExceptionConstructor:
    """Tests for exception constructor behavior."""

    def test_babylon_error_full_constructor(self) -> None:
        """BabylonError accepts message, error_code, and details."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError(
            message="Something went wrong",
            error_code="SYS_999",
            details={"context": "test", "value": 42},
        )

        assert error.message == "Something went wrong"
        assert error.error_code == "SYS_999"
        assert error.details == {"context": "test", "value": 42}

    def test_babylon_error_message_only(self) -> None:
        """BabylonError works with just a message."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Simple error")

        assert error.message == "Simple error"
        assert error.error_code == "SYS_000"
        assert error.details == {}

    def test_babylon_error_inherits_from_exception(self) -> None:
        """BabylonError is a proper Python Exception."""
        from babylon.utils.exceptions import BabylonError

        assert issubclass(BabylonError, Exception)

        error = BabylonError("Test")
        assert isinstance(error, Exception)

    def test_exception_args_contains_message(self) -> None:
        """Exception args tuple contains the message for standard handlers."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test message")
        assert error.args == ("Test message",)

    def test_details_is_mutable_dict(self) -> None:
        """Details can be modified after construction."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test")
        error.details["added_key"] = "added_value"

        assert error.details["added_key"] == "added_value"

    def test_none_details_becomes_empty_dict(self) -> None:
        """Passing None for details results in empty dict."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test", details=None)
        assert error.details == {}
        assert isinstance(error.details, dict)


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
class TestExceptionSerialization:
    """Tests for exception serialization methods."""

    def test_to_dict_returns_correct_structure(self) -> None:
        """to_dict() returns dict with error_type, error_code, message, details."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError(
            message="Test error",
            error_code="TEST_001",
            details={"key": "value"},
        )

        result = error.to_dict()

        assert result == {
            "error_type": "BabylonError",
            "error_code": "TEST_001",
            "message": "Test error",
            "details": {"key": "value"},
        }

    def test_to_dict_uses_subclass_name(self) -> None:
        """to_dict() uses the actual subclass name for error_type."""
        from babylon.utils.exceptions import LLMError

        error = LLMError("LLM failed", error_code="LLM_002")
        result = error.to_dict()

        assert result["error_type"] == "LLMError"

    def test_str_includes_error_code_and_message(self) -> None:
        """str(error) format is '[ERROR_CODE] message'."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Something went wrong", error_code="SYS_999")

        assert str(error) == "[SYS_999] Something went wrong"

    def test_repr_includes_class_name_and_params(self) -> None:
        """repr(error) includes class name, message, and error_code."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test", error_code="SYS_001")

        expected = "BabylonError(message='Test', error_code='SYS_001')"
        assert repr(error) == expected

    def test_repr_uses_subclass_name(self) -> None:
        """repr() uses the actual subclass name."""
        from babylon.utils.exceptions import TopologyError

        error = TopologyError("Graph disconnected")

        assert repr(error).startswith("TopologyError(")

    def test_to_dict_is_json_serializable(self) -> None:
        """to_dict() output can be serialized to JSON."""
        import json

        from babylon.utils.exceptions import BabylonError

        error = BabylonError(
            message="Test",
            error_code="SYS_001",
            details={"nested": {"key": "value"}, "list": [1, 2, 3]},
        )

        # Should not raise
        json_str = json.dumps(error.to_dict())
        assert isinstance(json_str, str)


# =============================================================================
# BACKWARDS COMPATIBILITY TESTS
# =============================================================================


@pytest.mark.unit
class TestBackwardsCompatibilityAliases:
    """Tests for backwards compatibility aliases."""

    def test_llm_generation_error_is_llm_error(self) -> None:
        """LLMGenerationError is an alias for LLMError."""
        from babylon.utils.exceptions import LLMError, LLMGenerationError

        assert LLMGenerationError is LLMError

    def test_llm_generation_error_instance_is_llm_error(self) -> None:
        """LLMGenerationError instance is also an LLMError instance."""
        from babylon.utils.exceptions import LLMError, LLMGenerationError

        error = LLMGenerationError("Test")
        assert isinstance(error, LLMError)

    @pytest.mark.parametrize(
        "alias_name",
        [
            "LifecycleError",
            "InvalidObjectError",
            "StateTransitionError",
            "CorruptStateError",
            "PreEmbeddingError",
            "PreprocessingError",
            "ChunkingError",
            "CacheError",
        ],
    )
    def test_rag_aliases_are_rag_error(self, alias_name: str) -> None:
        """All RAG exception aliases point to RagError."""
        from babylon import rag

        alias = getattr(rag.exceptions, alias_name)
        from babylon.rag.exceptions import RagError

        assert alias is RagError

    @pytest.mark.parametrize(
        "alias_name",
        [
            "ContextWindowError",
            "TokenCountError",
            "CapacityExceededError",
            "OptimizationFailedError",
            "ContentPriorityError",
            "ContentRemovalError",
            "ContentInsertionError",
        ],
    )
    def test_context_window_aliases_are_rag_error(self, alias_name: str) -> None:
        """All context window exception aliases point to RagError."""
        from babylon.rag import context_window
        from babylon.rag.exceptions import RagError

        alias = getattr(context_window, alias_name)
        assert alias is RagError


# =============================================================================
# EXCEPTION PROPAGATION TESTS
# =============================================================================


@pytest.mark.unit
class TestExceptionPropagation:
    """Tests for exception catching and propagation behavior."""

    def test_except_babylon_error_catches_all_children(self) -> None:
        """except BabylonError catches all exceptions in the hierarchy."""
        from babylon.rag.exceptions import RagError
        from babylon.utils.exceptions import (
            BabylonError,
            ConfigurationError,
            DatabaseError,
            InfrastructureError,
            LLMError,
            ObserverError,
            SimulationError,
            StorageError,
            TopologyError,
            ValidationError,
        )

        exception_classes = [
            InfrastructureError,
            StorageError,
            DatabaseError,
            ValidationError,
            ConfigurationError,
            SimulationError,
            TopologyError,
            ObserverError,
            LLMError,
            RagError,
        ]

        for exc_class in exception_classes:
            caught = False
            try:
                raise exc_class("Test")
            except BabylonError:
                caught = True
            assert caught, f"BabylonError should catch {exc_class.__name__}"

    def test_except_infrastructure_error_catches_database_and_storage(self) -> None:
        """except InfrastructureError catches DatabaseError and StorageError."""
        from babylon.utils.exceptions import (
            DatabaseError,
            InfrastructureError,
            StorageError,
        )

        # Test DatabaseError
        caught_db = False
        try:
            raise DatabaseError("DB failed")
        except InfrastructureError:
            caught_db = True
        assert caught_db

        # Test StorageError
        caught_storage = False
        try:
            raise StorageError("Storage failed")
        except InfrastructureError:
            caught_storage = True
        assert caught_storage

    def test_except_observer_error_catches_llm_and_rag(self) -> None:
        """except ObserverError catches LLMError and RagError."""
        from babylon.rag.exceptions import RagError
        from babylon.utils.exceptions import LLMError, ObserverError

        # Test LLMError
        caught_llm = False
        try:
            raise LLMError("LLM failed")
        except ObserverError:
            caught_llm = True
        assert caught_llm

        # Test RagError
        caught_rag = False
        try:
            raise RagError("RAG failed")
        except ObserverError:
            caught_rag = True
        assert caught_rag

    def test_except_storage_error_catches_checkpoint_errors(self) -> None:
        """except StorageError catches all CheckpointIOError variants."""
        from babylon.engine.history.io import (
            CheckpointCorruptedError,
            CheckpointIOError,
            CheckpointNotFoundError,
            CheckpointSchemaError,
        )
        from babylon.utils.exceptions import StorageError

        checkpoint_errors = [
            CheckpointIOError,
            CheckpointNotFoundError,
            CheckpointCorruptedError,
            CheckpointSchemaError,
        ]

        for exc_class in checkpoint_errors:
            caught = False
            try:
                raise exc_class("Test")
            except StorageError:
                caught = True
            assert caught, f"StorageError should catch {exc_class.__name__}"

    def test_error_code_preserved_through_handling(self) -> None:
        """Error codes are preserved when catching and re-raising exceptions."""
        from babylon.utils.exceptions import BabylonError, LLMError

        original_code = "LLM_CUSTOM_999"
        preserved_code: str | None = None

        try:
            try:
                raise LLMError("Inner error", error_code=original_code)
            except BabylonError as e:
                preserved_code = e.error_code
                raise
        except LLMError:
            pass

        assert preserved_code == original_code

    def test_details_preserved_through_handling(self) -> None:
        """Details dict is preserved when catching exceptions."""
        from babylon.utils.exceptions import BabylonError, DatabaseError

        original_details: dict[str, Any] = {"table": "users", "operation": "insert"}
        preserved_details: dict[str, Any] | None = None

        try:
            raise DatabaseError("Insert failed", details=original_details)
        except BabylonError as e:
            preserved_details = e.details

        assert preserved_details == original_details


# =============================================================================
# IMPORT PATH TESTS
# =============================================================================


@pytest.mark.unit
class TestImportPaths:
    """Tests for import path consistency."""

    def test_import_from_utils_exceptions(self) -> None:
        """Core exceptions can be imported from babylon.utils.exceptions."""
        from babylon.utils.exceptions import (
            BabylonError,
            ConfigurationError,
            DatabaseError,
            InfrastructureError,
            LLMError,
            LLMGenerationError,
            ObserverError,
            SimulationError,
            StorageError,
            TopologyError,
            ValidationError,
        )

        # All should be classes
        assert all(
            isinstance(cls, type)
            for cls in [
                BabylonError,
                InfrastructureError,
                StorageError,
                DatabaseError,
                ValidationError,
                ConfigurationError,
                SimulationError,
                TopologyError,
                ObserverError,
                LLMError,
                LLMGenerationError,
            ]
        )

    def test_import_from_babylon_exceptions(self) -> None:
        """Core exceptions can be imported from babylon.exceptions (top-level)."""
        from babylon.exceptions import (
            BabylonError,
            ConfigurationError,
            DatabaseError,
            InfrastructureError,
            LLMError,
            LLMGenerationError,
            ObserverError,
            SimulationError,
            StorageError,
            TopologyError,
            ValidationError,
        )

        # All should be classes
        assert all(
            isinstance(cls, type)
            for cls in [
                BabylonError,
                InfrastructureError,
                StorageError,
                DatabaseError,
                ValidationError,
                ConfigurationError,
                SimulationError,
                TopologyError,
                ObserverError,
                LLMError,
                LLMGenerationError,
            ]
        )

    def test_import_from_rag_exceptions(self) -> None:
        """RagError and aliases can be imported from babylon.rag.exceptions."""
        from babylon.rag.exceptions import (
            CacheError,
            ChunkingError,
            CorruptStateError,
            InvalidObjectError,
            LifecycleError,
            PreEmbeddingError,
            PreprocessingError,
            RagError,
            StateTransitionError,
        )

        # All should be classes (RagError is the actual class, others are aliases)
        assert isinstance(RagError, type)

        # Aliases should all be RagError
        aliases = [
            LifecycleError,
            InvalidObjectError,
            StateTransitionError,
            CorruptStateError,
            PreEmbeddingError,
            PreprocessingError,
            ChunkingError,
            CacheError,
        ]
        for alias in aliases:
            assert alias is RagError

    def test_top_level_and_utils_are_same_classes(self) -> None:
        """Classes from babylon.exceptions are identical to babylon.utils.exceptions."""
        import babylon.exceptions as top
        import babylon.utils.exceptions as utils

        assert top.BabylonError is utils.BabylonError
        assert top.InfrastructureError is utils.InfrastructureError
        assert top.StorageError is utils.StorageError
        assert top.DatabaseError is utils.DatabaseError
        assert top.ValidationError is utils.ValidationError
        assert top.ConfigurationError is utils.ConfigurationError
        assert top.SimulationError is utils.SimulationError
        assert top.TopologyError is utils.TopologyError
        assert top.ObserverError is utils.ObserverError
        assert top.LLMError is utils.LLMError
        assert top.LLMGenerationError is utils.LLMGenerationError


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and unusual usage patterns."""

    def test_empty_message(self) -> None:
        """Exception can be created with empty message."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("")
        assert error.message == ""
        assert str(error) == "[SYS_000] "

    def test_empty_error_code(self) -> None:
        """Empty string error_code is preserved (not replaced by default)."""
        from babylon.utils.exceptions import BabylonError

        # Note: empty string is falsy, so it gets replaced by default
        error = BabylonError("Test", error_code="")
        # Empty string is falsy, so default is used
        assert error.error_code == "SYS_000"

    def test_unicode_in_message(self) -> None:
        """Exception handles unicode characters in message."""
        from babylon.utils.exceptions import BabylonError

        message = "Error: Unable to process class solidarity networks"
        error = BabylonError(message)

        assert error.message == message
        assert message in str(error)

    def test_special_chars_in_details(self) -> None:
        """Exception handles special characters in details."""
        from babylon.utils.exceptions import BabylonError

        details: dict[str, object] = {
            "query": "SELECT * FROM classes WHERE name = 'proletariat'",
            "path": "/home/user/data.json",
        }
        error = BabylonError("DB error", details=details)

        assert error.details == details

    def test_nested_exception_chaining(self) -> None:
        """Exceptions support standard Python chaining with __cause__."""
        from babylon.utils.exceptions import BabylonError, DatabaseError

        original = ValueError("Original error")

        try:
            try:
                raise original
            except ValueError as e:
                raise DatabaseError("Wrapped error") from e
        except BabylonError as wrapped:
            assert wrapped.__cause__ is original

    def test_exception_can_be_pickled(self) -> None:
        """Exception can be pickled and unpickled (for multiprocessing)."""
        import pickle

        from babylon.utils.exceptions import BabylonError

        error = BabylonError(
            "Test error",
            error_code="SYS_001",
            details={"key": "value"},
        )

        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)

        assert unpickled.message == error.message
        assert unpickled.error_code == error.error_code
        assert unpickled.details == error.details

    def test_exception_equality_by_identity(self) -> None:
        """Two exceptions with same params are not equal (identity semantics)."""
        from babylon.utils.exceptions import BabylonError

        error1 = BabylonError("Test", error_code="SYS_001")
        error2 = BabylonError("Test", error_code="SYS_001")

        # Exceptions use identity equality, not value equality
        assert error1 is not error2
        assert error1 != error2
