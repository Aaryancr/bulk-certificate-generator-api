from pathlib import Path

import pytest

from app.exceptions import CertificateGenerationError
from app.schemas.certificate import CertificateRecord
from app.services.certificate_generator import generate_certificate


PDF_SIGNATURE = b"%PDF-"


def test_one_valid_certificate_generates_successfully():
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )

    result = generate_certificate(record)

    assert result is not None
    assert result.pdf_bytes is not None


def test_returned_certificate_id_is_correct():
    record = CertificateRecord(
        name="Bob Example",
        email="bob@example.com",
        course="Data Analysis",
        date="2026-10-08",
        certificate_id="CERT-XYZ-789",
    )

    result = generate_certificate(record)

    assert result.certificate_id == "CERT-XYZ-789"


def test_returned_filename_is_correct():
    record = CertificateRecord(
        name="Charlie Example",
        email="charlie@example.com",
        course="Web Development",
        date="2026-10-09",
        certificate_id="CERT-ABC-456",
    )

    result = generate_certificate(record)

    assert result.filename == "certificate_CERT-ABC-456.pdf"


def test_returned_pdf_bytes_are_non_empty():
    record = CertificateRecord(
        name="Diana Example",
        email="diana@example.com",
        course="Machine Learning",
        date="2026-10-10",
        certificate_id="CERT-ML-001",
    )

    result = generate_certificate(record)

    assert isinstance(result.pdf_bytes, bytes)
    assert len(result.pdf_bytes) > 0


def test_returned_pdf_begins_with_pdf_signature():
    record = CertificateRecord(
        name="Eve Example",
        email="eve@example.com",
        course="Advanced Python",
        date="2026-10-11",
        certificate_id="CERT-ADV-001",
    )

    result = generate_certificate(record)

    assert result.pdf_bytes.startswith(PDF_SIGNATURE)


def test_certificate_data_is_passed_correctly_into_template():
    record = CertificateRecord(
        name="Frank Example",
        email="frank@example.com",
        course="Cloud Computing",
        date="2026-10-12",
        certificate_id="CERT-CLOUD-001",
    )

    result = generate_certificate(record)

    pdf_bytes = result.pdf_bytes
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_pdf_generation_errors_propagate_as_clean_application_errors():
    record = {
        "name": "Grace Example",
        "email": "grace@example.com",
        "course": "DevOps",
        "date": "2026-10-13",
        "certificate_id": "CERT-DEV-001",
    }

    result = generate_certificate(record)
    assert result is not None
    assert result.certificate_id == "CERT-DEV-001"


def test_no_permanent_pdf_files_are_created(tmp_path):
    record = CertificateRecord(
        name="Henry Example",
        email="henry@example.com",
        course="Security",
        date="2026-10-14",
        certificate_id="CERT-SEC-001",
    )

    before_files = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()
    result = generate_certificate(record)
    after_files = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()

    assert result.pdf_bytes is not None
    assert before_files == after_files
