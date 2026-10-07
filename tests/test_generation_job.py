import tempfile
from pathlib import Path
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, GenerationRequest, init_db


@pytest.fixture
def valid_csv():
    return "name,email,course,date,certificate_id\nAlice,alice@example.com,Python,2026-10-07,CERT-001\n"


@pytest.fixture
def multi_record_csv():
    return (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
    )


@pytest.fixture
def invalid_csv():
    return "name,email,course\nAlice,alice@example.com,Python\n"


def test_background_job_can_be_imported():
    from app.services import generation_job_service
    assert hasattr(generation_job_service, 'process_generation_request')


def test_generation_request_status_transitions():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite:///{tmpdir}/test.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = SessionLocal()
        
        gen_request = GenerationRequest(request_id="test-001", status="pending")
        session.add(gen_request)
        session.commit()
        
        gen_request.status = "processing"
        session.commit()
        
        gen_request.status = "completed"
        session.commit()
        
        retrieved = session.query(GenerationRequest).filter(
            GenerationRequest.request_id == "test-001"
        ).first()
        
        assert retrieved.status == "completed"
        session.close()


def test_generation_request_with_counts():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite:///{tmpdir}/test.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = SessionLocal()
        
        gen_request = GenerationRequest(request_id="test-002", status="pending", total=5)
        session.add(gen_request)
        session.commit()
        
        gen_request.completed = 3
        gen_request.failed = 2
        gen_request.status = "completed_with_errors"
        session.commit()
        
        retrieved = session.query(GenerationRequest).filter(
            GenerationRequest.request_id == "test-002"
        ).first()
        
        assert retrieved.total == 5
        assert retrieved.completed == 3
        assert retrieved.failed == 2
        assert retrieved.status == "completed_with_errors"
        session.close()


def test_generation_request_with_error_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite:///{tmpdir}/test.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = SessionLocal()
        
        gen_request = GenerationRequest(request_id="test-003", status="failed", error_message="Test error")
        session.add(gen_request)
        session.commit()
        
        retrieved = session.query(GenerationRequest).filter(
            GenerationRequest.request_id == "test-003"
        ).first()
        
        assert retrieved.status == "failed"
        assert retrieved.error_message == "Test error"
        session.close()


def test_generation_request_with_output_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite:///{tmpdir}/test.db"
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = SessionLocal()
        
        output_path = f"{tmpdir}/output/test-004.zip"
        gen_request = GenerationRequest(request_id="test-004", status="completed", output_path=output_path)
        session.add(gen_request)
        session.commit()
        
        retrieved = session.query(GenerationRequest).filter(
            GenerationRequest.request_id == "test-004"
        ).first()
        
        assert retrieved.output_path == output_path
        session.close()

