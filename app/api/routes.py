from __future__ import annotations

import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.exceptions import BulkCertificateError, ValidationError, ZipGenerationError
from app.services.bulk_certificate_service import process_bulk_certificates
from app.services.zip_service import generate_zip_archive

router = APIRouter(prefix="/api/v1")


@router.post(
    "/certificates/bulk",
    tags=["Certificates"],
    summary="Generate bulk certificates from CSV and template",
    responses={
        200: {"description": "ZIP archive containing generated certificate PDFs (with optional FAILURES.txt)"},
        400: {"description": "Invalid input (missing files, invalid format, or no valid certificates)"},
        422: {"description": "Unprocessable entity (all certificate generations failed)"},
        500: {"description": "Internal server error"},
    },
)
async def bulk_generate_certificates(
    csv_file: UploadFile = File(..., description="CSV file with certificate records (required columns: name, email, course, date, certificate_id)"),
    template_file: UploadFile = File(..., description="HTML template for certificate rendering (must contain Jinja2 variables: {{ name }}, {{ course }}, {{ date }}, {{ certificate_id }})"),
):
    """
    Generate bulk certificates from CSV and HTML template.

    ## Process

    1. **Parse CSV**: Validates required columns (name, email, course, date, certificate_id)
    2. **Render Templates**: Applies Jinja2 template substitution for each certificate record
    3. **Generate PDFs**: Converts rendered HTML to PDF for each certificate
    4. **Create ZIP**: Packages all generated PDFs into a single ZIP archive

    ## Input Requirements

    ### CSV File
    - Must have .csv extension
    - Required columns: name, email, course, date, certificate_id
    - Values are trimmed of whitespace
    - All required fields must be non-empty
    - Email must be valid
    - certificate_id values must be unique

    ### HTML Template
    - Must have .html extension
    - Must contain valid Jinja2 syntax
    - Supported variables: {{ name }}, {{ course }}, {{ date }}, {{ certificate_id }}
    - CSS can be embedded for styling

    ## Response

    ### Success (200)
    - Returns a ZIP file containing all generated certificate PDFs
    - Filenames follow pattern: `certificate_<certificate_id>.pdf`
    - If any records failed to generate, `FAILURES.txt` is included with error details

    ### Partial Failures
    - Successfully generated certificates are still returned in the ZIP
    - `FAILURES.txt` contains row number, certificate ID, and error message for each failure
    - Response is still 200 OK

    ### Failure Cases
    - **400 Bad Request**: Missing/empty files, invalid extensions, invalid CSV data, no valid records
    - **422 Unprocessable Entity**: All certificate generations failed
    - **500 Internal Server Error**: PDF or ZIP generation error

    ## Example Errors

    The `FAILURES.txt` file format (when partial failures occur):
    ```
    Certificate Generation Failures
    ========================================

    Row 3
    Certificate ID: CERT-002
    Error: Invalid email 'not-an-email'

    Row 5
    Certificate ID: CERT-004
    Error: Missing required value(s) for date
    ```
    """
    if not csv_file:
        raise HTTPException(status_code=400, detail="CSV file is required")

    if not template_file:
        raise HTTPException(status_code=400, detail="Template file is required")

    if not csv_file.filename or not csv_file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file must have .csv extension")

    if not template_file.filename or not template_file.filename.lower().endswith(".html"):
        raise HTTPException(status_code=400, detail="Template file must have .html extension")

    csv_content = await csv_file.read()
    if not csv_content:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    template_content = await template_file.read()
    if not template_content:
        raise HTTPException(status_code=400, detail="Template file is empty")

    csv_text = csv_content.decode("utf-8")
    template_text = template_content.decode("utf-8")

    try:
        bulk_result = process_bulk_certificates(csv_text)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"CSV validation error: {str(exc)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Certificate processing error: {str(exc)}")

    if bulk_result.successful_count == 0 and bulk_result.failed_count > 0:
        failure_details = "\n".join(
            [f"Row {f.row_number}: {f.certificate_id} - {f.error}" for f in bulk_result.failures]
        )
        raise HTTPException(
            status_code=422,
            detail=f"No certificates could be generated. Failures:\n{failure_details}",
        )

    if bulk_result.successful_count == 0:
        raise HTTPException(status_code=400, detail="No valid certificates to generate")

    try:
        zip_bytes = generate_zip_archive(bulk_result.generated_certificates)
    except ZipGenerationError as exc:
        raise HTTPException(status_code=500, detail=f"ZIP generation error: {str(exc)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error during ZIP creation: {str(exc)}")

    zip_buffer = io.BytesIO(zip_bytes)

    if bulk_result.failed_count > 0:
        import zipfile

        zip_with_failures = io.BytesIO()
        with zipfile.ZipFile(zip_with_failures, "w", zipfile.ZIP_DEFLATED) as zf:
            with zipfile.ZipFile(zip_buffer, "r") as orig_zf:
                for filename in orig_zf.namelist():
                    zf.writestr(filename, orig_zf.read(filename))

            failure_text = "Certificate Generation Failures\n"
            failure_text += "=" * 40 + "\n\n"
            for failure in bulk_result.failures:
                failure_text += f"Row {failure.row_number}\n"
                failure_text += f"Certificate ID: {failure.certificate_id}\n"
                failure_text += f"Error: {failure.error}\n"
                failure_text += "\n"

            zf.writestr("FAILURES.txt", failure_text.encode("utf-8"))

        zip_buffer = zip_with_failures

    return StreamingResponse(
        io.BytesIO(zip_buffer.getvalue()),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=certificates.zip"},
    )
