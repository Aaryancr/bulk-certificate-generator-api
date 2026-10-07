# Bulk Certificate Generator API

This project is a simple FastAPI backend for generating bulk personalized certificates from a CSV file and a certificate HTML template.

## Overview

The service accepts a CSV file containing recipient data and an HTML template using Jinja2 variables. It validates the input, generates one PDF per valid record, and returns all generated certificates in a ZIP archive.

## Current Phase

This repository is in the initial project setup phase. The application includes the FastAPI app and a health endpoint, but certificate generation logic is not implemented yet.

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic
- Jinja2
- pytest

## Project Structure

```text
app/
  main.py
  api/
    routes.py
  schemas/
    certificate.py
  services/
  core/
    config.py
  exceptions.py
templates/
  certificate.html
tests/
requirements.txt
README.md
.gitignore
.env.example
Dockerfile
```

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then visit:

- http://localhost:8000/health

## Notes

This is a backend project intended for a software-engineering assignment. It intentionally keeps the implementation simple and avoids external services, authentication, and databases.
