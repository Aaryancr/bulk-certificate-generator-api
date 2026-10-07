from __future__ import annotations

from weasyprint import HTML

from app.exceptions import CertificateGenerationError


def generate_certificate_pdf(rendered_html: str) -> bytes:
    if rendered_html is None or not str(rendered_html).strip():
        raise CertificateGenerationError("Rendered HTML is empty.")

    try:
        pdf_bytes = HTML(string=str(rendered_html)).write_pdf()
    except Exception as exc:
        raise CertificateGenerationError("Failed to generate certificate PDF.") from exc

    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes:
        raise CertificateGenerationError("Generated PDF output is empty.")

    return bytes(pdf_bytes)
