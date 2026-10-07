# Bulk Certificate Generator API

A FastAPI backend for generating personalized certificates in bulk from a CSV file and an HTML/Jinja2 template.

The API validates the input data, renders a certificate for each valid record, converts the rendered HTML into PDF, packages the generated certificates into a ZIP archive, and returns the ZIP as the API response.

## Features

- CSV validation and parsing
- Jinja2 HTML template rendering
- Personalized PDF certificate generation
- Bulk certificate processing
- Partial failure handling
- In-memory ZIP generation
- REST API with FastAPI
- Automated test suite
- No database or external services required

## Tech Stack

- Python 3.12
- FastAPI
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
├── schemas/
│   └── certificate.py
├── services/
│   ├── csv_service.py
│   ├── template_service.py
│   ├── certificate_service.py
│   ├── certificate_generator.py
│   ├── bulk_certificate_service.py
│   └── zip_service.py
└── exceptions.py

templates/
└── certificate.html

tests/
├── test_health.py
├── test_csv_service.py
├── test_template_service.py
├── test_certificate_service.py
├── test_certificate_generator.py
├── test_bulk_certificate_service.py
├── test_zip_service.py
└── test_api.py

requirements.txt
README.md
.gitignore
.env.example
Dockerfile
```

## Running Locally

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## API Endpoints

### Health Check

```http
GET /health
```

Returns the health status of the application.

### Bulk Certificate Generation

```http
POST /api/v1/certificates/bulk
```

Accepts a `multipart/form-data` request containing:

- `csv_file` — recipient CSV file
- `template_file` — HTML certificate template

The API generates certificates for valid records and returns a ZIP archive.

## CSV Format

The CSV file must contain the following columns:

```text
name,email,course,date,certificate_id
```

Example:

```csv
name,email,course,date,certificate_id
Aaryan,aaryan@example.com,Python Development,2026-10-07,CERT-001
Rahul,rahul@example.com,FastAPI Development,2026-10-07,CERT-002
```

The service validates required columns, required values, email addresses, and duplicate certificate IDs.

## Template

The certificate template is an HTML file using Jinja2 variables.

Supported variables include:

```html
{{ name }}
{{ email }}
{{ course }}
{{ date }}
{{ certificate_id }}
```

Example:

```html
<h1>Certificate of Completion</h1>

<p>This certificate is awarded to {{ name }}</p>

<p>for successfully completing {{ course }}</p>

<p>Date: {{ date }}</p>

<p>Certificate ID: {{ certificate_id }}</p>
```

## Output

For each successfully processed record, the API generates a PDF with a deterministic filename:

```text
certificate_<certificate_id>.pdf
```

For example:

```text
certificate_CERT-001.pdf
certificate_CERT-002.pdf
```

All successful certificates are packaged into a ZIP archive and returned to the client.

When some records fail while others succeed, the ZIP also contains:

```text
FAILURES.txt
```

This file contains information about the failed records instead of silently discarding them.

## Error Handling

The API handles invalid input and processing failures with appropriate HTTP responses.

Typical responses include:

| Status | Meaning |
|---|---|
| `200` | Certificates generated successfully, including partial-success cases |
| `400` | Invalid request or file input |
| `422` | No certificates could be generated |
| `500` | Unexpected server-side failure |

## Running Tests

Run the complete test suite with:

```bash
python -m pytest -q
```

The project currently contains **67 automated tests** covering CSV validation, template rendering, PDF generation, certificate orchestration, ZIP generation, bulk processing, and API behavior.

## Design

The project intentionally keeps the architecture simple and focused on the assignment requirements.

The request flow is:

```text
CSV + HTML Template
        ↓
   API Validation
        ↓
    CSV Parsing
        ↓
 Template Rendering
        ↓
   PDF Generation
        ↓
 Bulk Processing
        ↓
   ZIP Generation
        ↓
    ZIP Response
```

Business logic is kept in service modules rather than being implemented directly inside the API route.

The project does not use a database, authentication, background workers, message queues, or external cloud services.

## License

This project was created as a software-engineering assignment and learning project.