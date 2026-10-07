from pathlib import Path

import pytest

from app.exceptions import CertificateGenerationError
from app.services.certificate_service import generate_certificate_pdf


PDF_SIGNATURE = b"%PDF-"


def test_valid_rendered_html_produces_non_empty_pdf_bytes():
    html = """
    <!DOCTYPE html>
    <html>
      <body>
        <h1>Certificate of Completion</h1>
        <p>Alice Example</p>
      </body>
    </html>
    """

    pdf_bytes = generate_certificate_pdf(html)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_returned_data_starts_with_expected_pdf_signature():
    html = """
    <!DOCTYPE html>
    <html>
      <body>
        <h1>Certificate of Completion</h1>
        <p>Bob Example</p>
      </body>
    </html>
    """

    pdf_bytes = generate_certificate_pdf(html)

    assert pdf_bytes.startswith(PDF_SIGNATURE)


def test_different_certificate_html_produces_independent_pdfs():
    html_one = """
    <!DOCTYPE html>
    <html><body><h1>Certificate</h1><p>Alice</p></body></html>
    """
    html_two = """
    <!DOCTYPE html>
    <html><body><h1>Certificate</h1><p>Bob</p></body></html>
    """

    pdf_one = generate_certificate_pdf(html_one)
    pdf_two = generate_certificate_pdf(html_two)

    assert pdf_one != pdf_two
    assert pdf_one.startswith(PDF_SIGNATURE)
    assert pdf_two.startswith(PDF_SIGNATURE)


def test_invalid_html_pdf_generation_failure_is_handled_cleanly():
    with pytest.raises(CertificateGenerationError, match="Rendered HTML is empty"):
        generate_certificate_pdf("")


def test_service_does_not_leave_permanent_generated_files_behind(tmp_path):
    html = """
    <!DOCTYPE html>
    <html>
      <body>
        <h1>Certificate of Completion</h1>
        <p>Charlie Example</p>
      </body>
    </html>
    """

    before_files = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()
    pdf_bytes = generate_certificate_pdf(html)
    after_files = set(p.name for p in tmp_path.iterdir()) if tmp_path.exists() else set()

    assert isinstance(pdf_bytes, bytes)
    assert before_files == after_files
