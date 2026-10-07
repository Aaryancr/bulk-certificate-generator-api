from app.exceptions import TemplateError
from app.schemas.certificate import CertificateRecord
from app.services.template_service import TemplateService


def test_valid_template_loads_successfully():
    service = TemplateService()

    template = service.load_template()

    assert template is not None
    assert hasattr(template, "render")


def test_valid_record_renders_successfully():
    service = TemplateService()
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )

    rendered = service.render_certificate(record)

    assert isinstance(rendered, str)
    assert "Alice Example" in rendered


def test_name_variable_is_replaced_correctly():
    service = TemplateService()
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )

    rendered = service.render_certificate(record)

    assert "Alice Example" in rendered
    assert "{{ name }}" not in rendered


def test_course_variable_is_replaced_correctly():
    service = TemplateService()
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )

    rendered = service.render_certificate(record)

    assert "Python Fundamentals" in rendered
    assert "{{ course }}" not in rendered


def test_date_variable_is_replaced_correctly():
    service = TemplateService()
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )

    rendered = service.render_certificate(record)

    assert "2026-10-07" in rendered
    assert "{{ date }}" not in rendered


def test_certificate_id_variable_is_replaced_correctly():
    service = TemplateService()
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )

    rendered = service.render_certificate(record)

    assert "CERT-001" in rendered
    assert "{{ certificate_id }}" not in rendered


def test_malformed_template_raises_expected_application_error(tmp_path):
    bad_template = tmp_path / "bad_template.html"
    bad_template.write_text("<!DOCTYPE html><html>{{ name", encoding="utf-8")
    service = TemplateService(template_dir=tmp_path, template_name="bad_template.html")

    try:
        service.load_template()
        assert False, "Template service should raise TemplateError for malformed template syntax."
    except TemplateError as exc:
        assert "Malformed template syntax" in str(exc)


def test_rendered_output_is_a_non_empty_html_string():
    service = TemplateService()
    record = CertificateRecord(
        name="Alice Example",
        email="alice@example.com",
        course="Python Fundamentals",
        date="2026-10-07",
        certificate_id="CERT-001",
    )

    rendered = service.render_certificate(record)

    assert isinstance(rendered, str)
    assert rendered.strip() != ""
    assert "<html" in rendered.lower()
