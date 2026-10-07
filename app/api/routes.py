from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.db.models import GenerationRequest
from app.exceptions import ValidationError
from app.services.csv_service import parse_csv_records
from app.services.generation_job_service import process_generation_request
from app.services.request_lookup_service import (
    RequestNotFoundError,
    RequestStillProcessingError,
    GeneratedZipNotFoundError,
    get_request_status,
    download_request_zip,
)

router = APIRouter(prefix="/api/v1")


class GenerationRequestResponse(BaseModel):
    request_id: str
    status: str


class GenerationStatusResponse(BaseModel):
    request_id: str
    status: str
    total: int
    completed: int
    failed: int
    created_at: str | None
    completed_at: str | None
    available: bool
    error_message: str | None


@router.post(
    "/certificates/bulk",
    tags=["Certificates"],
    summary="Submit a bulk certificate generation request",
    responses={
        202: {"description": "Generation request accepted and scheduled for processing"},
        400: {"description": "Invalid input (missing CSV or invalid format)"},
        500: {"description": "Internal server error"},
    },
    status_code=202,
)
async def bulk_generate_certificates(
    csv_file: UploadFile = File(..., description="CSV file with certificate records (required columns: name, email, course, date, certificate_id)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    if not csv_file:
        raise HTTPException(status_code=400, detail="CSV file is required")

    if not csv_file.filename or not csv_file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file must have .csv extension")

    csv_content = await csv_file.read()
    if not csv_content:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    csv_text = csv_content.decode("utf-8")

    try:
        parse_csv_records(csv_text)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"CSV validation error: {str(exc)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CSV parsing error: {str(exc)}")

    request_id = str(uuid.uuid4())

    db = SessionLocal()
    try:
        gen_request = GenerationRequest(request_id=request_id, status="pending")
        db.add(gen_request)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create generation request: {str(exc)}")
    finally:
        db.close()

    background_tasks.add_task(process_generation_request, request_id, csv_text)

    return GenerationRequestResponse(request_id=request_id, status="pending")


@router.get(
    "/certificates/{request_id}",
    tags=["Certificates"],
    summary="Get the status of a generation request",
    responses={
        200: {"description": "Generation request status"},
        404: {"description": "Request not found"},
    },
)
def get_generation_status(request_id: str):
    try:
        status_data = get_request_status(request_id)
        return GenerationStatusResponse(**status_data)
    except RequestNotFoundError:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {str(exc)}")


@router.get(
    "/certificates/{request_id}/download",
    tags=["Certificates"],
    summary="Download generated certificates ZIP",
    responses={
        200: {"description": "ZIP file containing generated certificates"},
        404: {"description": "Request not found or ZIP file not available"},
        409: {"description": "Generation still in progress"},
    },
)
def download_certificates(request_id: str):
    try:
        zip_bytes = download_request_zip(request_id)
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=certificates_{request_id}.zip"},
        )
    except RequestNotFoundError:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    except RequestStillProcessingError:
        raise HTTPException(
            status_code=409,
            detail="Generation is still in progress. Please try again later.",
        )
    except GeneratedZipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error downloading certificates: {str(exc)}")
