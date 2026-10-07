from pathlib import Path

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import GenerationRequest


class RequestNotFoundError(Exception):
    pass


class RequestStillProcessingError(Exception):
    pass


class GeneratedZipNotFoundError(Exception):
    pass


def get_request_status(request_id: str) -> dict:
    db = SessionLocal()
    try:
        gen_request = db.query(GenerationRequest).filter(
            GenerationRequest.request_id == request_id
        ).first()

        if not gen_request:
            raise RequestNotFoundError(f"Request '{request_id}' not found")

        return {
            "request_id": gen_request.request_id,
            "status": gen_request.status,
            "total": gen_request.total,
            "completed": gen_request.completed,
            "failed": gen_request.failed,
            "created_at": gen_request.created_at.isoformat() if gen_request.created_at else None,
            "completed_at": gen_request.completed_at.isoformat() if gen_request.completed_at else None,
            "available": gen_request.output_path is not None and Path(gen_request.output_path).exists(),
            "error_message": gen_request.error_message,
        }
    finally:
        db.close()


def download_request_zip(request_id: str) -> bytes:
    db = SessionLocal()
    try:
        gen_request = db.query(GenerationRequest).filter(
            GenerationRequest.request_id == request_id
        ).first()

        if not gen_request:
            raise RequestNotFoundError(f"Request '{request_id}' not found")

        if gen_request.status in ["pending", "processing"]:
            raise RequestStillProcessingError("Generation is still in progress")

        if not gen_request.output_path:
            raise GeneratedZipNotFoundError("No output generated")

        output_path = Path(gen_request.output_path)
        if not output_path.exists():
            raise GeneratedZipNotFoundError(f"Generated ZIP file not found at {gen_request.output_path}")

        with open(output_path, "rb") as f:
            return f.read()
    finally:
        db.close()
