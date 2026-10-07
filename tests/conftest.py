import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

import app.db.database as db_module
import app.db.models as models_module
from app.db.models import Base

# Ensure any module-level imports during test collection (such as app.main calling init_db())
# do not touch the production data/certificates.db database.
_session_tmpdir = tempfile.TemporaryDirectory()
_session_db_path = Path(_session_tmpdir.name) / "session_init.db"
_session_engine = create_engine(
    f"sqlite:///{_session_db_path}",
    connect_args={"check_same_thread": False},
)
db_module.engine = _session_engine
models_module.engine = _session_engine
db_module.SessionLocal.configure(bind=_session_engine)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """
    Isolates the SQLite database for each test to prevent tests sharing persistent state.
    Creates a fresh temporary SQLite database file for the test duration,
    initializes all schema tables, and binds SessionLocal and engine to it.
    Cleans up connections and resources on test teardown.
    """
    test_db_path = tmp_path / "test.db"
    test_db_url = f"sqlite:///{test_db_path}"

    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=test_engine)

    db_module.SessionLocal.configure(bind=test_engine)
    db_module.engine = test_engine
    models_module.engine = test_engine

    try:
        yield test_engine
    finally:
        test_engine.dispose()
        db_module.SessionLocal.configure(bind=_session_engine)
        db_module.engine = _session_engine
        models_module.engine = _session_engine
