from __future__ import annotations

from dataclasses import dataclass, field

from app.exceptions import CertificateGenerationError
from app.services.certificate_generator import CertificateGenerationResult, generate_certificate
from app.services.csv_service import parse_csv_records


@dataclass
class FailureRecord:
    row_number: int
    certificate_id: str | None
    error: str


@dataclass
class BulkCertificateResult:
    total_records: int
    successful_count: int
    failed_count: int
    failures: list[FailureRecord] = field(default_factory=list)
    generated_certificates: list[CertificateGenerationResult] = field(default_factory=list)


def process_bulk_certificates(csv_input: str) -> BulkCertificateResult:
    validated_records = parse_csv_records(csv_input)

    total_records = len(validated_records)
    generated_certificates = []
    failures = []

    for row_number, record_dict in enumerate(validated_records, start=2):
        certificate_id = record_dict.get("certificate_id", "UNKNOWN")

        try:
            cert_result = generate_certificate(record_dict)
            generated_certificates.append(cert_result)
        except CertificateGenerationError as exc:
            failures.append(
                FailureRecord(
                    row_number=row_number,
                    certificate_id=certificate_id,
                    error=str(exc),
                )
            )
        except Exception as exc:
            failures.append(
                FailureRecord(
                    row_number=row_number,
                    certificate_id=certificate_id,
                    error=f"Unexpected error: {str(exc)}",
                )
            )

    return BulkCertificateResult(
        total_records=total_records,
        successful_count=len(generated_certificates),
        failed_count=len(failures),
        failures=failures,
        generated_certificates=generated_certificates,
    )
