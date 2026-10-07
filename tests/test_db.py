import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, GenerationRequest, init_db


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite:///{tmpdir}/test.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        yield session, engine
        session.close()
        engine.dispose()


def test_database_initialization(temp_db):
    session, engine = temp_db
    assert Base.metadata.tables is not None
    assert "generation_requests" in Base.metadata.tables


def test_generation_request_creation(temp_db):
    session, engine = temp_db
    gen_request = GenerationRequest(request_id="test-001", status="pending")
    session.add(gen_request)
    session.commit()

    retrieved = session.query(GenerationRequest).filter(
        GenerationRequest.request_id == "test-001"
    ).first()

    assert retrieved is not None
    assert retrieved.request_id == "test-001"
    assert retrieved.status == "pending"


def test_generation_request_initial_pending_state(temp_db):
    session, engine = temp_db
    gen_request = GenerationRequest(request_id="test-002")
    session.add(gen_request)
    session.commit()

    retrieved = session.query(GenerationRequest).filter(
        GenerationRequest.request_id == "test-002"
    ).first()

    assert retrieved.status == "pending"
    assert retrieved.total == 0
    assert retrieved.completed == 0
    assert retrieved.failed == 0
    assert retrieved.output_path is None
    assert retrieved.error_message is None


def test_generation_request_update_status(temp_db):
    session, engine = temp_db
    gen_request = GenerationRequest(request_id="test-003", status="pending")
    session.add(gen_request)
    session.commit()

    gen_request.status = "processing"
    session.commit()

    retrieved = session.query(GenerationRequest).filter(
        GenerationRequest.request_id == "test-003"
    ).first()

    assert retrieved.status == "processing"


def test_generation_request_update_counts(temp_db):
    session, engine = temp_db
    gen_request = GenerationRequest(request_id="test-004", status="pending")
    session.add(gen_request)
    session.commit()

    gen_request.total = 10
    gen_request.completed = 8
    gen_request.failed = 2
    gen_request.status = "completed_with_errors"
    session.commit()

    retrieved = session.query(GenerationRequest).filter(
        GenerationRequest.request_id == "test-004"
    ).first()

    assert retrieved.total == 10
    assert retrieved.completed == 8
    assert retrieved.failed == 2
    assert retrieved.status == "completed_with_errors"
