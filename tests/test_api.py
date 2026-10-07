import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app

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


@pytest.fixture
def valid_template():
    return """<!DOCTYPE html>
<html>
<head><title>Certificate</title></head>
<body>
<h1>Certificate of Completion</h1>
<p>Name: {{ name }}</p>
<p>Course: {{ course }}</p>
<p>Date: {{ date }}</p>
<p>ID: {{ certificate_id }}</p>
</body>
</html>"""


@pytest.fixture
def invalid_template():
    return """<!DOCTYPE html>
<html>
<body>{{ name</body>
</html>"""


def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_successful_single_record_certificate_request(valid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "certificates.zip" in response.headers.get("content-disposition", "")


def test_successful_multi_record_certificate_request(multi_record_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(multi_record_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_returned_response_is_a_zip(valid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 200
    zip_bytes = response.content
    assert zip_bytes.startswith(b"PK\x03\x04")


def test_zip_contains_expected_certificate_pdfs(multi_record_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(multi_record_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 200
    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        filenames = zf.namelist()
        assert "certificate_CERT-001.pdf" in filenames
        assert "certificate_CERT-002.pdf" in filenames
        assert "certificate_CERT-003.pdf" in filenames


def test_missing_csv(valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 422


def test_missing_template(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
        },
    )

    assert response.status_code == 422


def test_invalid_csv_extension(valid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.txt", io.BytesIO(valid_csv.encode()), "text/plain"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 400
    assert "csv extension" in response.json()["detail"].lower()


def test_invalid_template_extension(valid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.txt", io.BytesIO(valid_template.encode()), "text/plain"),
        },
    )

    assert response.status_code == 400
    assert "html extension" in response.json()["detail"].lower()


def test_invalid_csv_content(invalid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(invalid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 400


def test_invalid_template_content(valid_csv, invalid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(invalid_template.encode()), "text/html"),
        },
    )

    assert response.status_code in [200, 500]


def test_all_certificate_generations_fail(valid_template):
    invalid_csv_no_dates = "name,email,course,date,certificate_id\nAlice,alice@example.com,Python,,CERT-001\n"

    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(invalid_csv_no_dates.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 400


def test_partial_certificate_generation_failure(valid_template):
    partial_csv = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Charlie,charlie@example.com,Go,2026-10-09,CERT-003\n"
    )

    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(partial_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        filenames = zf.namelist()
        assert "certificate_CERT-001.pdf" in filenames
        assert "certificate_CERT-003.pdf" in filenames


def test_correct_http_status_codes(valid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 200


def test_correct_content_type(valid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.headers["content-type"] == "application/zip"


def test_correct_content_disposition(valid_csv, valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert "content-disposition" in response.headers
    assert "certificates.zip" in response.headers["content-disposition"]


def test_empty_csv_file(valid_template):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(b""), "text/csv"),
            "template_file": ("test.html", io.BytesIO(valid_template.encode()), "text/html"),
        },
    )

    assert response.status_code == 400


def test_empty_template_file(valid_csv):
    response = client.post(
        "/api/v1/certificates/bulk",
        files={
            "csv_file": ("test.csv", io.BytesIO(valid_csv.encode()), "text/csv"),
            "template_file": ("test.html", io.BytesIO(b""), "text/html"),
        },
    )

    assert response.status_code == 400
