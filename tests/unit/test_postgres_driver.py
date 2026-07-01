"""Verify the PostgreSQL driver aligns with db_common's canonical psycopg 3 driver.

db_common declares ``postgresql+psycopg`` (psycopg 3) as its canonical — and
default — PostgreSQL driver. This project previously depended on the legacy
``psycopg2-binary`` package, which only backs the *different*
``postgresql+psycopg2`` dialect that db_common no longer exposes. With psycopg2
installed and psycopg 3 absent, db_common's default driver is unusable:

    >>> from sqlalchemy.dialects import registry
    >>> registry.load("postgresql+psycopg")
    sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgresql+psycopg

RED phase (before the fix) these tests FAIL because:
- ``import psycopg`` raises ``ModuleNotFoundError`` (only psycopg2 is installed),
- SQLAlchemy cannot resolve the ``postgresql+psycopg`` dialect, and
- the legacy ``psycopg2`` package is still present as a hard dependency.

GREEN phase (after the fix) the project depends on ``psycopg`` (v3), the
``postgresql+psycopg`` dialect resolves, and the legacy ``psycopg2`` is gone.

These are real integration-boundary checks (package importability + SQLAlchemy's
dialect registry), not string matches on pyproject.toml.
"""

from __future__ import annotations

import importlib.util

from vgnc_internal_orm.config import DatabaseDriver


class TestPostgresDriverIsPsycopg3:
    """Guard against drifting back to the legacy psycopg2 driver."""

    def test_db_common_canonical_postgres_driver_value(self):
        """db_common's PostgreSQL driver string must be the psycopg 3 dialect."""
        assert hasattr(DatabaseDriver, "POSTGRESQL_PSYCOPG")
        assert DatabaseDriver.POSTGRESQL_PSYCOPG.value == "postgresql+psycopg"

    def test_psycopg3_is_importable(self):
        """The psycopg 3 package must be installed (db_common's canonical PG driver)."""
        import psycopg  # noqa: PLC0415 — intentional runtime import

        major = str(psycopg.__version__).split(".", 1)[0]
        assert major == "3", f"expected psycopg 3.x, got psycopg {psycopg.__version__!r}"

    def test_legacy_psycopg2_is_not_installed(self):
        """The legacy psycopg2 package must not be a project dependency.

        psycopg2 backs the ``postgresql+psycopg2`` dialect; db_common uses
        ``postgresql+psycopg`` (psycopg 3), so shipping psycopg2 alongside
        psycopg 3 is dead weight that invites accidentally reverting to the
        wrong driver.
        """
        assert importlib.util.find_spec("psycopg2") is None, (
            "psycopg2 is installed — the project should depend on psycopg 3, "
            "which backs db_common's canonical 'postgresql+psycopg' driver"
        )

    def test_sqlalchemy_resolves_postgresql_psycopg_dialect(self):
        """SQLAlchemy must wire ``postgresql+psycopg`` to the psycopg 3 DBAPI.

        This is the exact path db_common exercises: it builds a URL with
        drivername ``postgresql+psycopg`` and hands it to ``create_engine``.
        ``create_engine`` is lazy, so we force DBAPI resolution via
        ``engine.dialect.dbapi`` — which raises ``ModuleNotFoundError`` when
        psycopg 3 is absent (the RED state) and returns the ``psycopg`` module
        once it is installed.
        """
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool

        import psycopg

        engine = create_engine(
            "postgresql+psycopg://test:test@localhost:5432/test",
            poolclass=NullPool,
        )
        assert type(engine.dialect).__module__ == "sqlalchemy.dialects.postgresql.psycopg"
        # Accessing .dbapi forces the dialect to import its driver module.
        assert engine.dialect.dbapi is psycopg, (
            "postgresql+psycopg must be backed by the psycopg 3 module, "
            f"got {engine.dialect.dbapi!r}"
        )
