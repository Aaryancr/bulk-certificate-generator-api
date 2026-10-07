from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

from app.exceptions import ZipGenerationError

if TYPE_CHECKING:
    from app.services.certificate_generator import CertificateGenerationResult


def generate_zip_archive(certificates: list[CertificateGenerationResult]) -> bytes:
    if not certificates or len(certificates) == 0:
        raise ZipGenerationError("Certificate collection is empty.")

    zip_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            filename_count = {}

            for cert in certificates:
                if not hasattr(cert, "filename") or not hasattr(cert, "pdf_bytes"):
                    raise ZipGenerationError(
                        f"Invalid certificate object: missing filename or pdf_bytes attribute."
                    )

                filename = cert.filename

                if filename in filename_count:
                    filename_count[filename] += 1
                    base, ext = filename.rsplit(".", 1)
                    unique_filename = f"{base}_{filename_count[filename]}.{ext}"
                else:
                    filename_count[filename] = 0
                    unique_filename = filename

                zf.writestr(unique_filename, cert.pdf_bytes)

    except ZipGenerationError:
        raise
    except Exception as exc:
        raise ZipGenerationError("Failed to create ZIP archive.") from exc

    if zip_buffer.tell() == 0:
        raise ZipGenerationError("Generated ZIP archive is empty.")

    zip_bytes = zip_buffer.getvalue()

    if not zip_bytes:
        raise ZipGenerationError("Generated ZIP archive is empty.")

    return zip_bytes
