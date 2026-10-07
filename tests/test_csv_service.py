import pytest

from app.exceptions import ValidationError
from app.services.csv_service import parse_csv_records


def test_valid_csv_with_one_record():
    csv_input = "name,email,course,date,certificate_id\nAlice,alice@example.com,Python Fundamentals,2026-10-07,CERT-001\n"

    records = parse_csv_records(csv_input)

    assert records == [
        {
            "name": "Alice",
            "email": "alice@example.com",
            "course": "Python Fundamentals",
            "date": "2026-10-07",
            "certificate_id": "CERT-001",
        }
    ]


def test_valid_csv_with_multiple_records():
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python Fundamentals,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Data Analysis,2026-10-08,CERT-002\n"
    )

    records = parse_csv_records(csv_input)

    assert records == [
        {
            "name": "Alice",
            "email": "alice@example.com",
            "course": "Python Fundamentals",
            "date": "2026-10-07",
            "certificate_id": "CERT-001",
        },
        {
            "name": "Bob",
            "email": "bob@example.com",
            "course": "Data Analysis",
            "date": "2026-10-08",
            "certificate_id": "CERT-002",
        },
    ]


def test_missing_required_column():
    csv_input = "name,email,course,date\nAlice,alice@example.com,Python Fundamentals,2026-10-07\n"

    with pytest.raises(ValidationError, match="Missing required columns: certificate_id"):
        parse_csv_records(csv_input)


def test_empty_csv():
    with pytest.raises(ValidationError, match="CSV input is empty"):
        parse_csv_records("")


def test_missing_required_value():
    csv_input = "name,email,course,date,certificate_id\nAlice,alice@example.com,,2026-10-07,CERT-001\n"

    with pytest.raises(ValidationError, match=r"Row 2: missing required value\(s\) for course"):
        parse_csv_records(csv_input)


def test_invalid_email():
    csv_input = "name,email,course,date,certificate_id\nAlice,not-an-email,Python Fundamentals,2026-10-07,CERT-001\n"

    with pytest.raises(ValidationError, match="Row 2: invalid email 'not-an-email'"):
        parse_csv_records(csv_input)


def test_duplicate_certificate_id():
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python Fundamentals,2026-10-07,CERT-001\n"
        "Bob,bob@example.com,Data Analysis,2026-10-08,CERT-001\n"
    )

    with pytest.raises(ValidationError, match="Row 3: duplicate certificate_id 'CERT-001'"):
        parse_csv_records(csv_input)


def test_whitespace_trimming():
    csv_input = "name,email,course,date,certificate_id\n  Alice  , alice@example.com , Python Fundamentals , 2026-10-07 , CERT-001 \n"

    records = parse_csv_records(csv_input)

    assert records == [
        {
            "name": "Alice",
            "email": "alice@example.com",
            "course": "Python Fundamentals",
            "date": "2026-10-07",
            "certificate_id": "CERT-001",
        }
    ]


def test_row_number_included_in_validation_errors():
    csv_input = (
        "name,email,course,date,certificate_id\n"
        "Alice,alice@example.com,Python Fundamentals,2026-10-07,CERT-001\n"
        "Bob,invalid-email,Data Analysis,2026-10-08,CERT-002\n"
    )

    with pytest.raises(ValidationError, match=r"Row 3"):
        parse_csv_records(csv_input)
