from pathlib import Path
import uuid
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.db.models import GenerationRequest
from app.exceptions import CertificateGenerationError, ValidationError, ZipGenerationError
from app.services.bulk_certificate_service import process_bulk_certificates
from app.services.template_service import TemplateService
from app.services.zip_service import generate_zip_archive

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "generated" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE_DIR = BASE_DIR / "templates"
TEMPLATE_NAME = "certificate.html"


def process_generation_request(request_id: str, csv_input: str) -> None:
    db = SessionLocal()
    try:
        gen_request = db.query(GenerationRequest).filter(
            GenerationRequest.request_id == request_id
        ).first()

        if not gen_request:
            return

        gen_request.status = "processing"
        db.commit()

        try:
            template_service = TemplateService(template_dir=TEMPLATE_DIR, template_name=TEMPLATE_NAME)
            template_service.load_template()
        except Exception as exc:
            gen_request.status = "failed"
            gen_request.error_message = f"Template loading error: {str(exc)}"
            db.commit()
            return

        try:
            bulk_result = process_bulk_certificates(csv_input)
        except ValidationError as exc:
            gen_request.status = "failed"
            gen_request.error_message = f"CSV validation error: {str(exc)}"
            db.commit()
            return
        except Exception as exc:
            gen_request.status = "failed"
            gen_request.error_message = f"Certificate processing error: {str(exc)}"
            db.commit()
            return

        if bulk_result.successful_count == 0:
            gen_request.status = "failed"
            gen_request.error_message = "No certificates could be generated"
            gen_request.total = bulk_result.total_records
            gen_request.failed = bulk_result.failed_count
            db.commit()
            return

        try:
            zip_bytes = generate_zip_archive(bulk_result.generated_certificates)
        except ZipGenerationError as exc:
            gen_request.status = "failed"
            gen_request.error_message = f"ZIP generation error: {str(exc)}"
            gen_request.total = bulk_result.total_records
            gen_request.completed = bulk_result.successful_count
            gen_request.failed = bulk_result.failed_count
            db.commit()
            return
        except Exception as exc:
            gen_request.status = "failed"
            gen_request.error_message = f"Unexpected error during ZIP creation: {str(exc)}"
            gen_request.total = bulk_result.total_records
            gen_request.completed = bulk_result.successful_count
            gen_request.failed = bulk_result.failed_count
            db.commit()
            return

        if bulk_result.failed_count > 0:
            import zipfile
            import io

            zip_with_failures = io.BytesIO()
            with zipfile.ZipFile(zip_with_failures, "w", zipfile.ZIP_DEFLATED) as zf:
                with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as orig_zf:
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

            zip_bytes = zip_with_failures.getvalue()

        output_path = OUTPUT_DIR / f"{request_id}.zip"
        with open(output_path, "wb") as f:
            f.write(zip_bytes)

        gen_request.total = bulk_result.total_records
        gen_request.completed = bulk_result.successful_count
        gen_request.failed = bulk_result.failed_count
        gen_request.output_path = str(output_path)

        if bulk_result.failed_count > 0:
            gen_request.status = "completed_with_errors"
        else:
            gen_request.status = "completed"

        gen_request.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        gen_request.status = "failed"
        gen_request.error_message = f"Unexpected error: {str(exc)}"
        db.commit()
    finally:
        db.close()
