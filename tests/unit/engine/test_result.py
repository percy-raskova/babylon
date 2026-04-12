"""RED phase: Tests for Result[T, E] type.

Spec 040 Discipline 2: Total Functions with Explicit Error Channels.
Systems return Result[WorldState, TransitionError] instead of raising.
"""

from __future__ import annotations

import pytest


class TestOk:
    """Tests for the Ok variant."""

    def test_ok_holds_value(self) -> None:
        from babylon.engine.result import Ok

        result = Ok(42)
        assert result.value == 42

    def test_ok_is_ok(self) -> None:
        from babylon.engine.result import Ok

        result = Ok("hello")
        assert result.is_ok() is True

    def test_ok_is_not_err(self) -> None:
        from babylon.engine.result import Ok

        result = Ok("hello")
        assert result.is_err() is False

    def test_ok_unwrap_returns_value(self) -> None:
        from babylon.engine.result import Ok

        result = Ok(99)
        assert result.unwrap() == 99

    def test_ok_is_frozen(self) -> None:
        from babylon.engine.result import Ok

        result = Ok(42)
        with pytest.raises(AttributeError):
            result.value = 100  # type: ignore[misc]

    def test_ok_map_transforms_value(self) -> None:
        from babylon.engine.result import Ok

        result = Ok(10)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_ok()
        assert mapped.unwrap() == 20


class TestErr:
    """Tests for the Err variant."""

    def test_err_holds_error(self) -> None:
        from babylon.engine.result import Err

        result = Err("something failed")
        assert result.error == "something failed"

    def test_err_is_err(self) -> None:
        from babylon.engine.result import Err

        result = Err("fail")
        assert result.is_err() is True

    def test_err_is_not_ok(self) -> None:
        from babylon.engine.result import Err

        result = Err("fail")
        assert result.is_ok() is False

    def test_err_unwrap_raises(self) -> None:
        from babylon.engine.result import Err

        result = Err("kaboom")
        with pytest.raises(ValueError, match="kaboom"):
            result.unwrap()

    def test_err_is_frozen(self) -> None:
        from babylon.engine.result import Err

        result = Err("oops")
        with pytest.raises(AttributeError):
            result.error = "changed"  # type: ignore[misc]

    def test_err_map_passes_through(self) -> None:
        from babylon.engine.result import Err

        result: Err[str] = Err("fail")
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_err()
        assert mapped.error == "fail"


class TestResultTypeAlias:
    """Tests for the Result union type alias."""

    def test_result_accepts_ok(self) -> None:
        from babylon.engine.result import Ok, Result

        r: Result[int, str] = Ok(42)
        assert r.is_ok()

    def test_result_accepts_err(self) -> None:
        from babylon.engine.result import Err, Result

        r: Result[int, str] = Err("fail")
        assert r.is_err()

    def test_ok_and_err_are_distinct(self) -> None:
        from babylon.engine.result import Err, Ok

        ok = Ok(1)
        err = Err("x")
        assert type(ok) is not type(err)
