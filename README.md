# Bulk Certificate Generator API

A FastAPI backend for asynchronously generating personalized PDF certificates in bulk from CSV data using a predefined HTML/Jinja2 template.

The API validates recipient data, schedules certificate generation as a background task, persists job status and progress in an SQLite database, and packages generated certificates into downloadable ZIP archives.

## Features

- Asynchronous bulk certificate generation via FastAPI background tasks
- SQLite database persistence with SQLAlchemy for tracking generation requests
- Job progress and status tracking (`pending`, `processing`, `completed`, `completed_with_errors`, `failed`)
- Detailed progress metrics (`total`, `completed`, `failed`)
- CSV validation, sanitization, and duplicate detection
- Jinja2 template rendering using a predefined template (`templates/certificate.html`)
- PDF certificate generation with WeasyPrint
- Deterministic output naming (`certificate_<certificate_id>.pdf`)
- Persistent ZIP storage with on-demand download endpoint
- Partial failure handling with detailed error reporting via `FAILURES.txt` inside the ZIP
- Automated test suite with isolated SQLite database fixtures

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Jinja2
- WeasyPrint
- pytest

## Project Structure

```text
app/
├── main.py
├── api/
│   └── routes.py
├── core/
│   └── config.py
├── db/
│   ├── database.py
│   └── models.py
├── schemas/
│   └── certificate.py
├── services/
│   ├── bulk_certificate_service.py
│   ├── certificate_generator.py
│   ├── certificate_service.py
│   ├── csv_service.py
│   ├── generation_job_service.py
│   ├── request_lookup_service.py
│   ├── template_service.py
│   └── zip_service.py
└── exceptions.py

templates/
└── certificate.html

tests/
├── conftest.py
├── test_api.py
├── test_bulk_certificate_service.py
├── test_certificate_generator.py
├── test_certificate_service.py
├── test_csv_service.py
├── test_db.py
├── test_generation_job.py
├── test_health.py
├── test_status_and_download.py
├── test_template_service.py
└── test_zip_service.py

requirements.txt
README.md
.gitignore
.env.example
Dockerfile
```

## Running Locally

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the API server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation (Swagger UI) is available at:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

### Health Check

```http
GET /health
```

Returns the health status of the application (`{"status": "ok"}`).

---

### Submit Bulk Certificate Generation

```http
POST /api/v1/certificates/bulk
```

Accepts a `multipart/form-data` request with a single file parameter:

- `csv_file` — recipient CSV data (`.csv` file)

The endpoint validates the CSV records, persists a new `GenerationRequest` in the SQLite database, schedules the generation job in the background, and immediately returns **HTTP 202 Accepted** with a unique `request_id`:

```json
{
  "request_id": "c9d4ef82-3d5b-4899-b14a-7186d9a04f21",
  "status": "pending"
}
```

The certificate template is predefined at `templates/certificate.html`. Clients do not provide a template file.

---

### Check Request Status

```http
GET /api/v1/certificates/{request_id}
```

Retrieves the current status, counts, and metadata for a generation request:

```json
{
  "request_id": "c9d4ef82-3d5b-4899-b14a-7186d9a04f21",
  "status": "completed",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "created_at": "2026-10-07T12:00:00+00:00",
  "completed_at": "2026-10-07T12:00:04+00:00",
  "available": true,
  "error_message": null
}
```

#### Status Values

| Status | Description |
|---|---|
| `pending` | Request accepted and queued for processing |
| `processing` | Background worker is actively generating certificates |
| `completed` | All certificates generated successfully |
| `completed_with_errors` | Completed with partial failures (some certificates generated, some failed) |
| `failed` | Processing failed entirely (e.g., all rows failed or template error) |

#### Progress Fields

- `total` — total number of recipient records from CSV
- `completed` — number of certificates successfully rendered and packaged
- `failed` — number of records that failed generation
- `available` — boolean indicating whether the output ZIP is ready for download
- `error_message` — error description if generation failed

---

### Download Generated Certificates

```http
GET /api/v1/certificates/{request_id}/download
```

Downloads the generated ZIP archive once processing is finished.

- **HTTP 200**: Returns `application/zip` stream named `certificates_<request_id>.zip`
- **HTTP 404**: Request not found or ZIP archive not available
- **HTTP 409**: Request is still `pending` or `processing`

## CSV Format

The uploaded CSV file must contain the following columns:

```text
name,email,course,date,certificate_id
```

### Column Descriptions

- `name` — Full name of the recipient
- `email` — Recipient email address (validated for correct format)
- `course` — Name of the course, training, or event
- `date` — Issue date of the certificate
- `certificate_id` — Unique identifier for the certificate (used in output filenames)

### Example

```csv
name,email,course,date,certificate_id
Alice Johnson,alice@example.com,Python Programming,2026-10-07,CERT-001
Bob Smith,bob@example.com,FastAPI Development,2026-10-07,CERT-002
```

## Template

Certificates are rendered using the predefined template at `templates/certificate.html`. The template uses Jinja2 syntax and supports the following variables matching the CSV columns:

- `{{ name }}` — Recipient's name
- `{{ email }}` — Recipient's email address
- `{{ course }}` — Course name
- `{{ date }}` — Issue date
- `{{ certificate_id }}` — Certificate identifier

## Output & Error Handling

- **PDF Naming**: For each successful record, a PDF named `certificate_<certificate_id>.pdf` is created.
- **ZIP Packaging**: All generated PDFs are packaged into a ZIP archive stored at `generated/output/<request_id>.zip`.
- **Partial Failure Handling**: If some records fail while others succeed:
  - Request status is set to `completed_with_errors`.
  - Successfully generated certificates are included in the ZIP.
  - A `FAILURES.txt` file is included in the ZIP describing each failed row, certificate ID, and error reason.

## Running Tests

Run the complete test suite with:

```bash
python -m pytest -q
```

The test suite contains **86 passing tests** with automated SQLite test database isolation covering:
- CSV parsing and validation
- Jinja2 template rendering
- PDF generation with WeasyPrint
- Bulk certificate processing
- ZIP packaging and failure report generation
- Database models and CRUD operations
- Asynchronous generation background jobs
- API endpoints (bulk generation submission, status polling, and ZIP downloading)
