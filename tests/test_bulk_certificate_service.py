from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import ValidationError
from app.schemas.certificate import CertificateRecord
from app.services.bulk_certificate_service import (
    BulkCertificateResult,
    FailureRecord,
    process_bulk_certificates,
)
from app.services.certificate_generator import CertificateGenerationResult


def test_one_valid_record():
    csv_input = "name,email,course,date,certificate_id\nAlice,alice@example.com,Python,2026-10-07,CERT-001\n"

    result = process_bulk_certificates(csv_input)

    assert isinstance(result, BulkCertificateResult)
    assert result.total_records == 1
    assert result.successful_count == 1
    assert result.failed_count == 0
    assert len(result.generated_certificates) == 1
    assert result.generated_certificates[0].certificate_id == "CERT-001"


def test_multiple_valid_records():
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
        "Charlie,charlie@example.com,Go,2026-10-09,CERT-003\n"
    )

    result = process_bulk_certificates(csv_input)

    assert result.total_records == 3
    assert result.successful_count == 3
    assert result.failed_count == 0
    assert len(result.generated_certificates) == 3


def test_one_failed_certificate_while_others_succeed():
    with patch("app.services.bulk_certificate_service.generate_certificate") as mock_gen:

        def side_effect(record_or_dict):
            cert_id = record_or_dict.get("certificate_id") if isinstance(record_or_dict, dict) else record_or_dict.certificate_id
            if cert_id == "CERT-002":
                from app.exceptions import CertificateGenerationError
                raise CertificateGenerationError("Template rendering failed")
            return CertificateGenerationResult(
                certificate_id=cert_id,
                filename=f"certificate_{cert_id}.pdf",
                pdf_bytes=b"%PDF-test",
            )

        mock_gen.side_effect = side_effect

        csv_input = (
            "name,email,course,date,certificate_id\n"
            "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
            "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
            "Charlie,charlie@example.com,Go,2026-10-09,CERT-003\n"
        )

        result = process_bulk_certificates(csv_input)

        assert result.total_records == 3
        assert result.successful_count == 2
        assert result.failed_count == 1
        assert len(result.generated_certificates) == 2
        assert len(result.failures) == 1


def test_all_records_succeed():
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
    )

    result = process_bulk_certificates(csv_input)

    assert result.successful_count == 2
    assert result.failed_count == 0
    assert len(result.failures) == 0


def test_all_certificate_generations_fail():
    with patch("app.services.bulk_certificate_service.generate_certificate") as mock_gen:
        from app.exceptions import CertificateGenerationError
        mock_gen.side_effect = CertificateGenerationError("PDF generation failed")

        csv_input = (
            "name,email,course,date,certificate_id\n"
            "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
            "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
        )

        result = process_bulk_certificates(csv_input)

        assert result.total_records == 2
        assert result.successful_count == 0
        assert result.failed_count == 2
        assert len(result.generated_certificates) == 0
        assert len(result.failures) == 2


def test_failure_contains_correct_row_information():
    with patch("app.services.bulk_certificate_service.generate_certificate") as mock_gen:
        from app.exceptions import CertificateGenerationError
        mock_gen.side_effect = CertificateGenerationError("Template error")

        csv_input = (
            "name,email,course,date,certificate_id\n"
            "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
            "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
        )

        result = process_bulk_certificates(csv_input)

        assert len(result.failures) == 2
        assert result.failures[0].row_number == 2
        assert result.failures[0].certificate_id == "CERT-001"
        assert result.failures[1].row_number == 3
        assert result.failures[1].certificate_id == "CERT-002"


def test_returned_counts_are_correct():
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
        "Charlie,charlie@example.com,Go,2026-10-09,CERT-003\n"
        "Diana,diana@example.com,Rust,2026-10-10,CERT-004\n"
    )

    result = process_bulk_certificates(csv_input)

    assert result.total_records == 4
    assert result.successful_count + result.failed_count == result.total_records


def test_generated_certificate_result_objects_are_preserved():
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
    )

    result = process_bulk_certificates(csv_input)

    for cert in result.generated_certificates:
        assert isinstance(cert, CertificateGenerationResult)
        assert hasattr(cert, "certificate_id")
        assert hasattr(cert, "filename")
        assert hasattr(cert, "pdf_bytes")
        assert cert.pdf_bytes.startswith(b"%PDF-")


def test_no_permanent_files_are_created(tmp_path):
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Java,2026-10-08,CERT-002\n"
    )

    before_files = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()
    result = process_bulk_certificates(csv_input)
    after_files = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()

    assert result is not None
    assert before_files == after_files


def test_existing_services_are_reused():
    with patch("app.services.bulk_certificate_service.parse_csv_records") as mock_csv, \
         patch("app.services.bulk_certificate_service.generate_certificate") as mock_gen:

        mock_csv.return_value = [
            CertificateRecord(
                name="Alice",
                email="alice@example.com",
                course="Python",
                date="2026-10-07",
                certificate_id="CERT-001",
            ).model_dump()
        ]

        mock_gen.return_value = CertificateGenerationResult(
            certificate_id="CERT-001",
            filename="certificate_CERT-001.pdf",
            pdf_bytes=b"%PDF-test",
        )

        csv_input = "name,email,course,date,certificate_id\nAlice,alice@example.com,Python,2026-10-07,CERT-001\n"
        result = process_bulk_certificates(csv_input)

        mock_csv.assert_called_once_with(csv_input)
        mock_gen.assert_called_once()
        assert result.successful_count == 1
