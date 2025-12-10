"""Comprehensive test suite for Babylon's logging utilities.

This module tests the logging infrastructure defined in:
- babylon.utils.log (JSONFormatter, TRACE level, LogContext)
- babylon.config.logging_config (setup_logging, RotatingFileHandler)
- babylon.utils.exceptions (BabylonError.log() method)

The tests verify:
1. JSONFormatter produces valid JSONL output
2. TRACE level (value=5) is properly defined and usable
3. LogContext context manager propagates context correctly
4. ContextAwareFilter injects context into LogRecords
5. BabylonError.log() logs with structured context
6. RotatingFileHandler is configured correctly
7. setup_logging() creates proper handler hierarchy

TDD Approach: RED phase - these tests define expected behavior.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# TRACE LEVEL TESTS
# =============================================================================


@pytest.mark.unit
class TestTraceLevel:
    """Tests for the custom TRACE logging level (value=5)."""

    def test_trace_level_value_is_five(self) -> None:
        """TRACE level has numeric value 5."""
        from babylon.utils.log import TRACE

        assert TRACE == 5

    def test_trace_level_is_registered(self) -> None:
        """TRACE level is registered with logging module."""
        from babylon.utils.log import TRACE

        assert logging.getLevelName(TRACE) == "TRACE"
        assert logging.getLevelName("TRACE") == TRACE

    def test_logger_has_trace_method(self) -> None:
        """Logger instances have a trace() method."""
        logger = logging.getLogger("test.trace")
        assert hasattr(logger, "trace")
        assert callable(logger.trace)

    def test_trace_logs_at_trace_level(self) -> None:
        """trace() method logs messages at TRACE level."""
        from babylon.utils.log import TRACE

        logger = logging.getLogger("test.trace.level")
        logger.setLevel(TRACE)

        # Use a real handler with a StringIO stream to capture output
        import io

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(TRACE)
        handler.setFormatter(logging.Formatter("%(levelno)s|%(levelname)s|%(message)s"))
        logger.addHandler(handler)

        try:
            logger.trace("Test trace message")

            output = stream.getvalue()
            # Verify the log was recorded at TRACE level (5)
            assert "5|TRACE|Test trace message" in output
        finally:
            logger.removeHandler(handler)

    def test_trace_not_called_when_level_disabled(self) -> None:
        """trace() does not log when level is above TRACE."""
        logger = logging.getLogger("test.trace.disabled")
        logger.setLevel(logging.DEBUG)  # Above TRACE (5)

        handler = MagicMock()
        handler.level = logging.DEBUG
        handler.emit = MagicMock()
        handler.filter = MagicMock(return_value=True)
        logger.addHandler(handler)

        try:
            logger.trace("Should not appear")
            assert not handler.emit.called
        finally:
            logger.removeHandler(handler)

    def test_trace_supports_formatting_args(self) -> None:
        """trace() supports % formatting arguments."""
        from babylon.utils.log import TRACE

        logger = logging.getLogger("test.trace.format")
        logger.setLevel(TRACE)

        # Use a real handler with a StringIO stream to capture output
        import io

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(TRACE)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

        try:
            logger.trace("Value: %d, Name: %s", 42, "test")

            output = stream.getvalue()
            assert "Value: 42, Name: test" in output
        finally:
            logger.removeHandler(handler)


# =============================================================================
# JSON FORMATTER TESTS
# =============================================================================


@pytest.mark.unit
class TestJSONFormatter:
    """Tests for the custom JSONFormatter."""

    def test_format_returns_valid_json(self) -> None:
        """format() returns valid JSON string."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_format_includes_required_fields(self) -> None:
        """Output includes ts, level, logger, msg, func, line."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="babylon.engine",
            level=logging.ERROR,
            pathname="engine.py",
            lineno=100,
            msg="Error occurred",
            args=(),
            exc_info=None,
            func="run_tick",
        )

        result = json.loads(formatter.format(record))

        assert "ts" in result
        assert result["level"] == "ERROR"
        assert result["logger"] == "babylon.engine"
        assert result["msg"] == "Error occurred"
        assert result["func"] == "run_tick"
        assert result["line"] == 100

    def test_format_timestamp_is_iso8601(self) -> None:
        """Timestamp is in ISO 8601 format with timezone."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = json.loads(formatter.format(record))

        # Should be parseable as ISO 8601
        ts = result["ts"]
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None
        # Should have timezone info (UTC)
        assert parsed.tzinfo is not None

    def test_format_includes_extra_fields(self) -> None:
        """Extra fields (tick, correlation_id) are included in output."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        # Add extra fields
        record.tick = 42
        record.correlation_id = "abc-123"
        record.simulation_id = "sim_001"

        result = json.loads(formatter.format(record))

        assert result["tick"] == 42
        assert result["correlation_id"] == "abc-123"
        assert result["simulation_id"] == "sim_001"

    def test_format_includes_exception_dict(self) -> None:
        """Exception dict from BabylonError.to_dict() is included."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error",
            args=(),
            exc_info=None,
        )
        record.exception = {
            "error_type": "RagError",
            "error_code": "RAG_201",
            "message": "Embedding failed",
            "details": {"chunk_id": "chunk_001"},
        }

        result = json.loads(formatter.format(record))

        assert "exception" in result
        assert result["exception"]["error_code"] == "RAG_201"

    def test_format_handles_exception_info(self) -> None:
        """exc_info is formatted and included."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error",
            args=(),
            exc_info=exc_info,
        )

        result = json.loads(formatter.format(record))

        assert "exc_info" in result
        assert "ValueError" in result["exc_info"]
        assert "Test error" in result["exc_info"]

    def test_format_handles_non_serializable_values(self) -> None:
        """Non-JSON-serializable values are converted to strings."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        # Add non-serializable extra field
        record.custom_object = object()

        # Should not raise
        result = formatter.format(record)
        parsed = json.loads(result)

        # Object should be stringified
        assert "custom_object" in parsed
        assert isinstance(parsed["custom_object"], str)

    def test_format_excludes_standard_logrecord_fields(self) -> None:
        """Standard LogRecord fields are not duplicated in output."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = json.loads(formatter.format(record))

        # Standard fields should not appear (except in their mapped form)
        assert "args" not in result
        assert "created" not in result
        assert "pathname" not in result
        assert "process" not in result
        assert "thread" not in result

    def test_format_message_with_args_is_formatted(self) -> None:
        """getMessage() is called to format message with args."""
        from babylon.utils.log import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Value: %d",
            args=(42,),
            exc_info=None,
        )

        result = json.loads(formatter.format(record))

        assert result["msg"] == "Value: 42"


# =============================================================================
# LOG CONTEXT TESTS
# =============================================================================


@pytest.mark.unit
class TestLogContext:
    """Tests for log context propagation using contextvars."""

    def test_get_log_context_returns_empty_dict_by_default(self) -> None:
        """get_log_context() returns empty dict when no context set."""
        from babylon.utils.log import clear_log_context, get_log_context

        clear_log_context()
        context = get_log_context()

        assert context == {}

    def test_set_log_context_adds_fields(self) -> None:
        """set_log_context() adds fields to context."""
        from babylon.utils.log import clear_log_context, get_log_context, set_log_context

        clear_log_context()
        set_log_context(tick=42, simulation_id="sim_001")

        context = get_log_context()

        assert context["tick"] == 42
        assert context["simulation_id"] == "sim_001"

    def test_set_log_context_merges_fields(self) -> None:
        """set_log_context() merges with existing context."""
        from babylon.utils.log import clear_log_context, get_log_context, set_log_context

        clear_log_context()
        set_log_context(tick=1)
        set_log_context(correlation_id="abc")

        context = get_log_context()

        assert context["tick"] == 1
        assert context["correlation_id"] == "abc"

    def test_clear_log_context_removes_all_fields(self) -> None:
        """clear_log_context() removes all context fields."""
        from babylon.utils.log import clear_log_context, get_log_context, set_log_context

        set_log_context(tick=42)
        clear_log_context()

        assert get_log_context() == {}

    def test_get_log_context_returns_copy(self) -> None:
        """get_log_context() returns a copy, not the original."""
        from babylon.utils.log import clear_log_context, get_log_context, set_log_context

        clear_log_context()
        set_log_context(tick=42)

        context = get_log_context()
        context["tick"] = 999  # Modify the copy

        # Original should be unchanged
        assert get_log_context()["tick"] == 42


@pytest.mark.unit
class TestLogContextScope:
    """Tests for log_context_scope context manager."""

    def test_scope_sets_context_inside(self) -> None:
        """Context is set inside the scope."""
        from babylon.utils.log import (
            clear_log_context,
            get_log_context,
            log_context_scope,
        )

        clear_log_context()

        with log_context_scope(tick=42, simulation_id="test"):
            context = get_log_context()
            assert context["tick"] == 42
            assert context["simulation_id"] == "test"

    def test_scope_restores_context_after_exit(self) -> None:
        """Context is restored after exiting scope."""
        from babylon.utils.log import (
            clear_log_context,
            get_log_context,
            log_context_scope,
            set_log_context,
        )

        clear_log_context()
        set_log_context(tick=1)

        with log_context_scope(tick=42):
            assert get_log_context()["tick"] == 42

        assert get_log_context()["tick"] == 1

    def test_scope_restores_on_exception(self) -> None:
        """Context is restored even if exception occurs."""
        from babylon.utils.log import (
            clear_log_context,
            get_log_context,
            log_context_scope,
            set_log_context,
        )

        clear_log_context()
        set_log_context(tick=1)

        try:
            with log_context_scope(tick=42):
                raise ValueError("Test error")
        except ValueError:
            pass

        assert get_log_context()["tick"] == 1

    def test_nested_scopes(self) -> None:
        """Nested scopes work correctly."""
        from babylon.utils.log import (
            clear_log_context,
            get_log_context,
            log_context_scope,
        )

        clear_log_context()

        with log_context_scope(outer=True):
            assert get_log_context()["outer"] is True

            with log_context_scope(inner=True):
                context = get_log_context()
                assert context["outer"] is True
                assert context["inner"] is True

            # Inner scope ended
            context = get_log_context()
            assert context["outer"] is True
            assert "inner" not in context

    def test_scope_merges_with_existing_context(self) -> None:
        """Scope merges with existing context, doesn't replace."""
        from babylon.utils.log import (
            clear_log_context,
            get_log_context,
            log_context_scope,
            set_log_context,
        )

        clear_log_context()
        set_log_context(simulation_id="sim_001")

        with log_context_scope(tick=42):
            context = get_log_context()
            assert context["simulation_id"] == "sim_001"
            assert context["tick"] == 42


# =============================================================================
# CONTEXT AWARE FILTER TESTS
# =============================================================================


@pytest.mark.unit
class TestContextAwareFilter:
    """Tests for ContextAwareFilter logging filter."""

    def test_filter_injects_context_fields(self) -> None:
        """Filter adds context fields to LogRecord."""
        from babylon.utils.log import (
            ContextAwareFilter,
            clear_log_context,
            set_log_context,
        )

        clear_log_context()
        set_log_context(tick=42, correlation_id="abc")

        filter_instance = ContextAwareFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter_instance.filter(record)

        assert result is True  # Always passes
        assert record.tick == 42  # type: ignore[attr-defined]
        assert record.correlation_id == "abc"  # type: ignore[attr-defined]

    def test_filter_does_not_overwrite_existing_fields(self) -> None:
        """Filter does not overwrite fields already on record."""
        from babylon.utils.log import (
            ContextAwareFilter,
            clear_log_context,
            set_log_context,
        )

        clear_log_context()
        set_log_context(tick=1)

        filter_instance = ContextAwareFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.tick = 42  # Pre-existing value

        filter_instance.filter(record)

        assert record.tick == 42  # type: ignore[attr-defined]

    def test_filter_always_returns_true(self) -> None:
        """Filter always returns True (passes all records)."""
        from babylon.utils.log import ContextAwareFilter

        filter_instance = ContextAwareFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        assert filter_instance.filter(record) is True


# =============================================================================
# BABYLON ERROR LOG METHOD TESTS
# =============================================================================


@pytest.mark.unit
class TestBabylonErrorLog:
    """Tests for BabylonError.log() helper method."""

    def test_log_method_exists(self) -> None:
        """BabylonError has a log() method."""
        from babylon.utils.exceptions import BabylonError

        assert hasattr(BabylonError, "log")
        assert callable(BabylonError.log)

    def test_log_method_signature(self) -> None:
        """log() method has correct signature."""
        import inspect

        from babylon.utils.exceptions import BabylonError

        sig = inspect.signature(BabylonError.log)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "logger" in params
        assert "level" in params
        assert "exc_info" in params

    def test_log_method_logs_at_error_level_by_default(self) -> None:
        """log() logs at ERROR level by default."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test error", error_code="TEST_001")
        logger = MagicMock(spec=logging.Logger)

        error.log(logger)

        logger.log.assert_called_once()
        call_args = logger.log.call_args
        assert call_args[0][0] == logging.ERROR

    def test_log_method_includes_exception_dict(self) -> None:
        """log() includes exception.to_dict() in extra."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test error", error_code="TEST_001", details={"key": "value"})
        logger = MagicMock(spec=logging.Logger)

        error.log(logger)

        call_kwargs = logger.log.call_args[1]
        assert "extra" in call_kwargs
        assert "exception" in call_kwargs["extra"]
        assert call_kwargs["extra"]["exception"]["error_code"] == "TEST_001"

    def test_log_method_accepts_custom_level(self) -> None:
        """log() accepts custom log level."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Warning", error_code="WARN_001")
        logger = MagicMock(spec=logging.Logger)

        error.log(logger, level=logging.WARNING)

        call_args = logger.log.call_args
        assert call_args[0][0] == logging.WARNING

    def test_log_method_includes_exc_info_by_default(self) -> None:
        """log() includes exc_info=True by default."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test error")
        logger = MagicMock(spec=logging.Logger)

        error.log(logger)

        call_kwargs = logger.log.call_args[1]
        assert call_kwargs.get("exc_info") is True

    def test_log_method_can_disable_exc_info(self) -> None:
        """log() can disable exc_info."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test error")
        logger = MagicMock(spec=logging.Logger)

        error.log(logger, exc_info=False)

        call_kwargs = logger.log.call_args[1]
        assert call_kwargs.get("exc_info") is False

    def test_log_method_uses_str_as_message(self) -> None:
        """log() uses str(self) as the log message."""
        from babylon.utils.exceptions import BabylonError

        error = BabylonError("Test message", error_code="ERR_001")
        logger = MagicMock(spec=logging.Logger)

        error.log(logger)

        call_args = logger.log.call_args
        # Message should be str(error) = "[ERR_001] Test message"
        assert call_args[0][1] == str(error)


# =============================================================================
# ROTATING FILE HANDLER TESTS
# =============================================================================


@pytest.mark.unit
class TestLoggingConfigRotatingHandler:
    """Tests for RotatingFileHandler configuration in logging_config.py."""

    def test_setup_logging_creates_rotating_main_handler(self) -> None:
        """setup_logging() creates a RotatingFileHandler for main log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                root_logger = logging.getLogger()
                rotating_handlers = [
                    h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)
                ]

                assert len(rotating_handlers) >= 1
                # Clean up
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)

    def test_rotating_handler_has_correct_max_bytes(self) -> None:
        """RotatingFileHandler has maxBytes=10_000_000 (10MB) for main log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                root_logger = logging.getLogger()
                rotating_handlers = [
                    h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)
                ]

                # Find main handler (not error-only)
                main_handler = next(
                    (h for h in rotating_handlers if h.level != logging.ERROR),
                    None,
                )
                assert main_handler is not None
                assert main_handler.maxBytes == 10_000_000

                # Clean up
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)

    def test_rotating_handler_has_correct_backup_count(self) -> None:
        """RotatingFileHandler has backupCount=5 for main log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                root_logger = logging.getLogger()
                rotating_handlers = [
                    h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)
                ]

                main_handler = next(
                    (h for h in rotating_handlers if h.level != logging.ERROR),
                    None,
                )
                assert main_handler is not None
                assert main_handler.backupCount == 5

                # Clean up
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)

    def test_setup_logging_creates_error_only_handler(self) -> None:
        """setup_logging() creates an error-only RotatingFileHandler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                root_logger = logging.getLogger()
                error_handlers = [
                    h
                    for h in root_logger.handlers
                    if isinstance(h, RotatingFileHandler) and h.level == logging.ERROR
                ]

                assert len(error_handlers) >= 1

                # Clean up
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)

    def test_error_handler_has_correct_limits(self) -> None:
        """Error handler has maxBytes=5_000_000 and backupCount=10."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                root_logger = logging.getLogger()
                error_handlers = [
                    h
                    for h in root_logger.handlers
                    if isinstance(h, RotatingFileHandler) and h.level == logging.ERROR
                ]

                assert len(error_handlers) >= 1
                error_handler = error_handlers[0]
                assert error_handler.maxBytes == 5_000_000
                assert error_handler.backupCount == 10

                # Clean up
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)


# =============================================================================
# SETUP LOGGING HANDLER HIERARCHY TESTS
# =============================================================================


@pytest.mark.unit
class TestSetupLoggingHandlers:
    """Tests for setup_logging() handler hierarchy."""

    def test_setup_logging_uses_json_formatter_for_file_handlers(self) -> None:
        """File handlers use JSONFormatter."""
        from babylon.utils.log import JSONFormatter

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                root_logger = logging.getLogger()
                file_handlers = [
                    h
                    for h in root_logger.handlers
                    if isinstance(h, logging.FileHandler | RotatingFileHandler)
                ]

                for handler in file_handlers:
                    assert isinstance(handler.formatter, JSONFormatter)

                # Clean up
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)

    def test_setup_logging_console_handler_exists(self) -> None:
        """setup_logging() creates a console (stream) handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                root_logger = logging.getLogger()
                stream_handlers = [
                    h
                    for h in root_logger.handlers
                    if isinstance(h, logging.StreamHandler)
                    and not isinstance(h, logging.FileHandler)
                ]

                assert len(stream_handlers) >= 1

                # Clean up
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)

    def test_setup_logging_suppresses_noisy_loggers(self) -> None:
        """setup_logging() suppresses chromadb, httpx, httpcore loggers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            with patch("babylon.config.base.BaseConfig.LOG_DIR", log_dir):
                from babylon.config.logging_config import setup_logging

                setup_logging()

                assert logging.getLogger("chromadb").level >= logging.WARNING
                assert logging.getLogger("httpx").level >= logging.WARNING
                assert logging.getLogger("httpcore").level >= logging.WARNING

                # Clean up
                root_logger = logging.getLogger()
                for h in root_logger.handlers[:]:
                    root_logger.removeHandler(h)


# =============================================================================
# MAIN MODULE TESTS (no basicConfig)
# =============================================================================


@pytest.mark.unit
class TestMainModuleLogging:
    """Tests that __main__.py does not use basicConfig."""

    def test_main_module_does_not_call_basicconfig(self) -> None:
        """__main__.py should not call logging.basicConfig()."""
        import ast
        from pathlib import Path

        # Find the __main__.py file
        main_path = Path(__file__).parent.parent.parent.parent / "src" / "babylon" / "__main__.py"

        if not main_path.exists():
            pytest.skip("__main__.py not found at expected path")

        source = main_path.read_text()
        tree = ast.parse(source)

        # Look for calls to logging.basicConfig or basicConfig
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    if func.attr == "basicConfig":
                        pytest.fail(
                            "Found logging.basicConfig() call in __main__.py. "
                            "Use setup_logging() instead."
                        )
                elif isinstance(func, ast.Name) and func.id == "basicConfig":
                    pytest.fail(
                        "Found basicConfig() call in __main__.py. " "Use setup_logging() instead."
                    )


# =============================================================================
# LOGGING YAML TESTS
# =============================================================================


@pytest.mark.unit
class TestLoggingYaml:
    """Tests that logging.yaml does not reference pythonjsonlogger."""

    def test_logging_yaml_no_pythonjsonlogger(self) -> None:
        """logging.yaml should not reference pythonjsonlogger."""
        from pathlib import Path

        yaml_path = Path(__file__).parent.parent.parent.parent / "logging.yaml"

        if not yaml_path.exists():
            pytest.skip("logging.yaml not found at expected path")

        content = yaml_path.read_text()

        assert "pythonjsonlogger" not in content, (
            "logging.yaml references pythonjsonlogger which is not in dependencies. "
            "Use babylon.utils.log.JSONFormatter instead."
        )


# =============================================================================
# INTEGRATION-STYLE TESTS (using real loggers)
# =============================================================================


@pytest.mark.unit
class TestJSONFormatterIntegration:
    """Integration tests for JSONFormatter with real loggers."""

    def test_json_formatter_with_real_logger(self) -> None:
        """JSONFormatter works with a real logger and handler."""
        from babylon.utils.log import JSONFormatter

        logger = logging.getLogger("test.json.integration")
        logger.setLevel(logging.DEBUG)

        # Capture output
        import io

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        try:
            logger.info("Test message", extra={"tick": 42})

            output = stream.getvalue()
            parsed = json.loads(output)

            assert parsed["msg"] == "Test message"
            assert parsed["tick"] == 42
            assert parsed["level"] == "INFO"
        finally:
            logger.removeHandler(handler)

    def test_context_aware_filter_with_json_formatter(self) -> None:
        """ContextAwareFilter + JSONFormatter work together."""
        from babylon.utils.log import (
            ContextAwareFilter,
            JSONFormatter,
            clear_log_context,
            log_context_scope,
        )

        clear_log_context()
        logger = logging.getLogger("test.context.json")
        logger.setLevel(logging.DEBUG)

        # Capture output
        import io

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        handler.addFilter(ContextAwareFilter())
        logger.addHandler(handler)

        try:
            with log_context_scope(tick=42, simulation_id="sim_001"):
                logger.info("Tick complete")

            output = stream.getvalue()
            parsed = json.loads(output)

            assert parsed["msg"] == "Tick complete"
            assert parsed["tick"] == 42
            assert parsed["simulation_id"] == "sim_001"
        finally:
            logger.removeHandler(handler)


# =============================================================================
# EXPORTS TEST
# =============================================================================


@pytest.mark.unit
class TestLogModuleExports:
    """Tests for log module __all__ exports."""

    def test_all_exports_are_defined(self) -> None:
        """All items in __all__ are actually defined in the module."""
        from babylon.utils import log

        for name in log.__all__:
            assert hasattr(log, name), f"{name} is in __all__ but not defined"

    def test_expected_exports_present(self) -> None:
        """Expected exports are present in __all__."""
        from babylon.utils import log

        expected = [
            "TRACE",
            "JSONFormatter",
            "ContextAwareFilter",
            "get_log_context",
            "set_log_context",
            "clear_log_context",
            "log_context_scope",
        ]

        for name in expected:
            assert name in log.__all__, f"{name} should be exported in __all__"
