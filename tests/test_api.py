import io
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import GenerationRequest

client = TestClient(app)


@pytest.fixture
def valid_csv():
    return "name,email,course,date,certificate_id\nAlice,alice@example.com,Python,2026-10-07,CERT-001\n"


@pytest.fixture
def multi_record_csv():
    return (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
        "Charlie,charlie@example.com,Go,2026-10-09,CERT-003\n"
    )


@pytest.fixture
def invalid_csv():
    return "name,email,course\nAlice,alice@example.com,Python\n"


def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_bulk_generate_returns_202(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202


def test_bulk_generate_response_contains_request_id(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] is not None
    assert len(data["request_id"]) > 0


def test_bulk_generate_response_contains_status(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert "status" in data
    assert data["status"] == "pending"


def test_template_file_no_longer_required(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202


def test_csv_only_required(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202
    assert response.json()["request_id"] is not None


def test_missing_csv_returns_error():
    response = client.post(
        "/api/v1/certificates/bulk",
        files={},
    )

    assert response.status_code == 422


def test_invalid_csv_extension(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.txt", io.BytesIO(valid_csv.encode()), "text/plain"),
        },
    )

    assert response.status_code == 400
    assert "csv extension" in response.json()["detail"].lower()


def test_invalid_csv_content(invalid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(invalid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 400


def test_empty_csv_file():
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(b""), "text/csv"),
        },
    )

    assert response.status_code == 400


def test_generation_request_created_in_database(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 202
    request_id = response.json()["request_id"]

    db = SessionLocal()
    try:
        gen_request = db.query(GenerationRequest).filter(
            GenerationRequest.request_id == request_id
        ).first()

        assert gen_request is not None
        assert gen_request.status in ["pending", "processing", "completed", "completed_with_errors"]
    finally:
        db.close()
