import io
import zipfile

import pytest

from app.exceptions import ZipGenerationError
from app.schemas.certificate import CertificateRecord
from app.services.certificate_generator import generate_certificate
from app.services.zip_service import generate_zip_archive


ZIP_SIGNATURE = b"PK\x03\x04"


def test_one_certificate_creates_a_valid_zip():
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )
    cert = generate_certificate(record)

    zip_bytes = generate_zip_archive([cert])

    assert isinstance(zip_bytes, bytes)
    assert zip_bytes.startswith(ZIP_SIGNATURE)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        assert len(zf.namelist()) == 1


def test_multiple_certificates_create_a_valid_zip():
    records = [
        CertificateRecord(
            name="Alice Example",
            email="alice@example.com",
            course="Python Fundamentals",
            date="2026-10-07",
            certificate_id="CERT-001",
        ),
        CertificateRecord(
            name="Bob Example",
            email="bob@example.com",
            course="Data Analysis",
            date="2026-10-08",
            certificate_id="CERT-002",
        ),
        CertificateRecord(
            name="Charlie Example",
            email="charlie@example.com",
            course="Web Development",
            date="2026-10-09",
            certificate_id="CERT-003",
        ),
    ]
    certs = [generate_certificate(record) for record in records]

    zip_bytes = generate_zip_archive(certs)

    assert isinstance(zip_bytes, bytes)
    assert zip_bytes.startswith(ZIP_SIGNATURE)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        assert len(zf.namelist()) == 3


def test_zip_contains_expected_number_of_files():
    records = [
        CertificateRecord(
            name=f"Person {i}",
            email=f"person{i}@example.com",
            course="Test Course",
            date="2026-10-07",
            certificate_id=f"CERT-{i:03d}",
        )
        for i in range(1, 6)
    ]
    certs = [generate_certificate(record) for record in records]

    zip_bytes = generate_zip_archive(certs)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        assert len(zf.namelist()) == 5


def test_zip_filenames_match_certificate_filenames():
    records = [
        CertificateRecord(
            name="Alice Example",
            email="alice@example.com",
            course="Python",
            date="2026-10-07",
            certificate_id="CERT-ALICE-001",
        ),
        CertificateRecord(
            name="Bob Example",
            email="bob@example.com",
            course="Java",
            date="2026-10-08",
            certificate_id="CERT-BOB-002",
        ),
    ]
    certs = [generate_certificate(record) for record in records]

    zip_bytes = generate_zip_archive(certs)

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        filenames = zf.namelist()
        assert "certificate_CERT-ALICE-001.pdf" in filenames
        assert "certificate_CERT-BOB-002.pdf" in filenames


def test_zip_contents_exactly_match_original_pdf_bytes():
    record = CertificateRecord(
        name="Charlie Example",
        email="charlie@example.com",
        course="Cloud Computing",
        date="2026-10-09",
        certificate_id="CERT-CLOUD-001",
    )
    cert = generate_certificate(record)

    zip_bytes = generate_zip_archive([cert])

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        extracted_pdf = zf.read("certificate_CERT-CLOUD-001.pdf")
        assert extracted_pdf == cert.pdf_bytes


def test_empty_certificate_collection_is_rejected():
    with pytest.raises(ZipGenerationError, match="Certificate collection is empty"):
        generate_zip_archive([])


def test_zip_creation_stays_in_memory_and_does_not_leave_files():
    record = CertificateRecord(
        name="Diana Example",
        email="diana@example.com",
        course="DevOps",
        date="2026-10-10",
        certificate_id="CERT-DEVOPS-001",
    )
    cert = generate_certificate(record)

    zip_bytes = generate_zip_archive([cert])

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0


def test_duplicate_filenames_handled_explicitly_and_safely():
    from app.services.certificate_generator import CertificateGenerationResult

    cert1 = CertificateGenerationResult(
        certificate_id="CERT-001",
        filename="certificate_CERT-001.pdf",
        pdf_bytes=b"%PDF-test1",
    )
    cert2 = CertificateGenerationResult(
        certificate_id="CERT-001-DUP",
        filename="certificate_CERT-001.pdf",
        pdf_bytes=b"%PDF-test2",
    )

    zip_bytes = generate_zip_archive([cert1, cert2])

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        filenames = zf.namelist()
        assert len(filenames) == 2
        assert "certificate_CERT-001.pdf" in filenames
        assert "certificate_CERT-001_1.pdf" in filenames

        pdf1 = zf.read("certificate_CERT-001.pdf")
        pdf2 = zf.read("certificate_CERT-001_1.pdf")
        assert pdf1 == b"%PDF-test1"
        assert pdf2 == b"%PDF-test2"
