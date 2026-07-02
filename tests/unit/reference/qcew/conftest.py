"""Shared fixtures for spec-086 QCEW loader tests.

NOTE: no directory-level ``importorskip`` here — ``test_schema_086.py``
exercises only the babylon ORM and must run in CI. Modules that import
``babylon_data.qcew.*`` guard themselves with::

    pytest.importorskip("babylon_data.qcew.<module>",
                        reason="babylon-data symlink not resolved (CI)")

The reusable engine/seed logic lives in :mod:`tests.fixtures.qcew.orm` so
integration modules can build identical databases without conftest
plugin registration.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from tests.fixtures.qcew.orm import create_qcew_engine, seed_qcew_dims


@pytest.fixture()
def qcew_orm_engine() -> Engine:
    """In-memory engine with the spec-086 table subset created from the ORM."""
    return create_qcew_engine()


@pytest.fixture()
def qcew_orm_session(qcew_orm_engine: Engine) -> Iterator[Session]:
    """Session over :func:`qcew_orm_engine` with dims pre-seeded."""
    with Session(qcew_orm_engine) as session:
        seed_qcew_dims(session)
        yield session
