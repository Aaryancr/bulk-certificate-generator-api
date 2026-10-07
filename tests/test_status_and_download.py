import io
import json
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import GenerationRequest
from datetime import datetime, timezone

client = TestClient(app)


@pytest.fixture
def valid_csv():
    return "name,email,course,date,certificate_id\nAlice,alice@example.com,Python,2026-10-07,CERT-001\n"


def test_get_status_pending_request(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202
    request_id = response.json()["request_id"]

    status_response = client.get(f"/api/v1/certificates/{request_id}")

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["request_id"] == request_id
    assert data["status"] in ["pending", "processing", "completed"]
    assert data["total"] >= 0
    assert data["completed"] >= 0
    assert data["failed"] >= 0
    assert "created_at" in data
    assert "completed_at" in data
    assert "available" in data
    assert isinstance(data["available"], bool)


def test_get_status_completed_request(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202
    request_id = response.json()["request_id"]

    status_response = client.get(f"/api/v1/certificates/{request_id}")

    assert status_response.status_code == 200
    data = status_response.json()
    assert "status" in data
    assert data["status"] in ["pending", "processing", "completed", "completed_with_errors", "failed"]


def test_get_status_unknown_request_id():
    response = client.get("/api/v1/certificates/nonexistent-request-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_status_response_has_required_fields(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    request_id = response.json()["request_id"]

    status_response = client.get(f"/api/v1/certificates/{request_id}")

    assert status_response.status_code == 200
    data = status_response.json()

    required_fields = ["request_id", "status", "total", "completed", "failed", "created_at", "completed_at", "available"]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


def test_get_status_created_at_is_iso_format(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    request_id = response.json()["request_id"]

    status_response = client.get(f"/api/v1/certificates/{request_id}")

    data = status_response.json()
    created_at = data["created_at"]
    assert created_at is not None
    try:
        datetime.fromisoformat(created_at)
    except ValueError:
        pytest.fail(f"created_at is not ISO format: {created_at}")


def test_download_completed_zip(valid_csv, tmp_path, monkeypatch):
    from app.services import generation_job_service

    original_output_dir = generation_job_service.OUTPUT_DIR
    generation_job_service.OUTPUT_DIR = tmp_path / "output"
    generation_job_service.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        response = client.post(
            "/api/v1/certificates/bulk",
            files={
                "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            },
        )

        request_id = response.json()["request_id"]

        download_response = client.get(f"/api/v1/certificates/{request_id}/download")

        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/zip"
        assert "certificates_" in download_response.headers.get("content-disposition", "")
        assert request_id in download_response.headers.get("content-disposition", "")
        assert download_response.content.startswith(b"PK\x03\x04")
    finally:
        generation_job_service.OUTPUT_DIR = original_output_dir


def test_download_processing_returns_409(valid_csv):
    db = SessionLocal()
    try:
        gen_request = GenerationRequest(
            request_id="test-processing",
            status="processing",
            total=0,
            completed=0,
            failed=0,
        )
        db.add(gen_request)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/certificates/test-processing/download")

    assert response.status_code == 409
    assert "progress" in response.json()["detail"].lower()


def test_download_pending_returns_409(valid_csv):
    db = SessionLocal()
    try:
        gen_request = GenerationRequest(
            request_id="test-pending",
            status="pending",
            total=0,
            completed=0,
            failed=0,
        )
        db.add(gen_request)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/certificates/test-pending/download")

    assert response.status_code == 409


def test_download_unknown_request_returns_404():
    response = client.get("/api/v1/certificates/nonexistent-id/download")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_download_completed_no_zip_returns_404():
    db = SessionLocal()
    try:
        gen_request = GenerationRequest(
            request_id="test-no-zip",
            status="completed",
            total=1,
            completed=1,
            failed=0,
            output_path=None,
        )
        db.add(gen_request)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/certificates/test-no-zip/download")

    assert response.status_code == 404


def test_download_failed_request_returns_404():
    db = SessionLocal()
    try:
        gen_request = GenerationRequest(
            request_id="test-failed",
            status="failed",
            total=0,
            completed=0,
            failed=0,
            error_message="Test failure",
        )
        db.add(gen_request)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/certificates/test-failed/download")

    assert response.status_code == 404


def test_download_content_type_is_zip(valid_csv, tmp_path, monkeypatch):
    from app.services import generation_job_service

    original_output_dir = generation_job_service.OUTPUT_DIR
    generation_job_service.OUTPUT_DIR = tmp_path / "output"
    generation_job_service.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        response = client.post(
            "/api/v1/certificates/bulk",
            files={
                "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            },
        )

        request_id = response.json()["request_id"]

        download_response = client.get(f"/api/v1/certificates/{request_id}/download")

        if download_response.status_code == 200:
            assert download_response.headers["content-type"] == "application/zip"
    finally:
        generation_job_service.OUTPUT_DIR = original_output_dir


def test_download_filename_includes_request_id(valid_csv, tmp_path, monkeypatch):
    from app.services import generation_job_service

    original_output_dir = generation_job_service.OUTPUT_DIR
    generation_job_service.OUTPUT_DIR = tmp_path / "output"
    generation_job_service.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        response = client.post(
            "/api/v1/certificates/bulk",
            files={
                "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            },
        )

        request_id = response.json()["request_id"]

        download_response = client.get(f"/api/v1/certificates/{request_id}/download")

        if download_response.status_code == 200:
            content_disposition = download_response.headers.get("content-disposition", "")
            assert request_id in content_disposition
            assert content_disposition.endswith(".zip")
    finally:
        generation_job_service.OUTPUT_DIR = original_output_dir


def test_status_error_message_included_on_failure():
    db = SessionLocal()
    try:
        gen_request = GenerationRequest(
            request_id="test-error-msg",
            status="failed",
            total=0,
            completed=0,
            failed=0,
            error_message="CSV validation failed",
        )
        db.add(gen_request)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/certificates/test-error-msg")

    assert response.status_code == 200
    data = response.json()
    assert data["error_message"] == "CSV validation failed"


def test_status_available_false_when_no_output_path():
    db = SessionLocal()
    try:
        gen_request = GenerationRequest(
            request_id="test-no-output",
            status="completed",
            total=0,
            completed=0,
            failed=0,
            output_path=None,
        )
        db.add(gen_request)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/certificates/test-no-output")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False


def test_status_available_true_when_zip_exists(tmp_path):
    db = SessionLocal()
    try:
        test_zip_path = tmp_path / "test.zip"
        test_zip_path.write_bytes(b"PK\x03\x04test")

        gen_request = GenerationRequest(
            request_id="test-with-zip",
            status="completed",
            total=1,
            completed=1,
            failed=0,
            output_path=str(test_zip_path),
        )
        db.add(gen_request)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/certificates/test-with-zip")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
