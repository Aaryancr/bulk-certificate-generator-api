import csv
import io
import re

from app.exceptions import ValidationError
from app.schemas.certificate import CertificateRecord

REQUIRED_COLUMNS = ("name", "email", "course", "date", "certificate_id")


def _normalize_row(row):
    if row is None:
        return {}
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[str(key).strip()] = "" if value is None else str(value).strip()
    return normalized


def _is_valid_email(email: str) -> bool:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.fullmatch(pattern, email))


def parse_csv_records(csv_input: str) -> list[dict[str, str]]:
    if csv_input is None or not str(csv_input).strip():
        raise ValidationError("CSV input is empty.")

    reader = csv.DictReader(io.StringIO(str(csv_input)))
    if reader.fieldnames is None:
        raise ValidationError("CSV input is empty.")

    fieldnames = [field.strip() if field is not None else field for field in reader.fieldnames]
    reader.fieldnames = fieldnames

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
    if missing_columns:
        raise ValidationError(f"Missing required columns: {', '.join(missing_columns)}.")

    seen_certificate_ids = set()
    valid_records = []

    for row_number, row in enumerate(reader, start=2):
        normalized_row = _normalize_row(row)

        if normalized_row and all((value == "") for value in normalized_row.values()):
            raise ValidationError(f"Row {row_number}: missing required values.")

        missing_values = [column for column in REQUIRED_COLUMNS if normalized_row.get(column, "") == ""]
        if missing_values:
            raise ValidationError(
                f"Row {row_number}: missing required value(s) for {', '.join(missing_values)}."
            )

        email = normalized_row["email"]
        if not _is_valid_email(email):
            raise ValidationError(f"Row {row_number}: invalid email '{email}'.")

        certificate_id = normalized_row["certificate_id"]
        if certificate_id in seen_certificate_ids:
            raise ValidationError(f"Row {row_number}: duplicate certificate_id '{certificate_id}'.")
        seen_certificate_ids.add(certificate_id)

        record = {
            "name": normalized_row["name"],
            "email": normalized_row["email"],
            "course": normalized_row["course"],
            "date": normalized_row["date"],
            "certificate_id": normalized_row["certificate_id"],
        }
        valid_records.append(CertificateRecord.model_validate(record).model_dump())

    return valid_records
