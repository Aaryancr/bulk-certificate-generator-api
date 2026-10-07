from __future__ import annotations

from app.exceptions import CertificateGenerationError
from app.schemas.certificate import CertificateRecord
from app.services.certificate_service import generate_certificate_pdf
from app.services.template_service import render_certificate_template


class CertificateGenerationResult:
    def __init__(self, certificate_id: str, filename: str, pdf_bytes: bytes):
        self.certificate_id = certificate_id
        self.filename = filename
        self.pdf_bytes = pdf_bytes


def generate_certificate(record: CertificateRecord | dict) -> CertificateGenerationResult:
    if isinstance(record, dict):
        record = CertificateRecord.model_validate(record)

    try:
        rendered_html = render_certificate_template(record)
    except Exception as exc:
        raise CertificateGenerationError(
            f"Failed to render certificate template for ID {record.certificate_id}"
        ) from exc

    try:
        pdf_bytes = generate_certificate_pdf(rendered_html)
    except Exception as exc:
        raise CertificateGenerationError(
            f"Failed to generate PDF for certificate ID {record.certificate_id}"
        ) from exc

    filename = f"certificate_{record.certificate_id}.pdf"

    return CertificateGenerationResult(
        certificate_id=record.certificate_id,
        filename=filename,
        pdf_bytes=pdf_bytes,
    )
