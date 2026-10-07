from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, TemplateSyntaxError, select_autoescape

from app.exceptions import TemplateError
from app.schemas.certificate import CertificateRecord

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = BASE_DIR / "templates"
TEMPLATE_NAME = "certificate.html"


class TemplateService:
    def __init__(self, template_dir: str | Path | None = None, template_name: str = TEMPLATE_NAME):
        self.template_dir = Path(template_dir) if template_dir is not None else TEMPLATE_DIR
        self.template_name = template_name
        self.environment = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def load_template(self) -> Template:
        try:
            return self.environment.get_template(self.template_name)
        except TemplateSyntaxError as exc:
            raise TemplateError(f"Malformed template syntax in '{self.template_name}': {exc.message}") from exc
        except FileNotFoundError as exc:
            raise TemplateError(f"Template '{self.template_name}' was not found.") from exc
        except Exception as exc:
            raise TemplateError("Unable to load the certificate template.") from exc

    def render_certificate(self, record: CertificateRecord | dict) -> str:
        if isinstance(record, dict):
            record = CertificateRecord.model_validate(record)

        template = self.load_template()

        rendered = template.render(
            name=record.name,
            course=record.course,
            date=record.date,
            certificate_id=record.certificate_id,
        )

        if not rendered or not str(rendered).strip():
            raise TemplateError("Rendered certificate output is empty.")

        return rendered


def load_certificate_template() -> Template:
    return TemplateService().load_template()


def render_certificate_template(record: CertificateRecord | dict) -> str:
    return TemplateService().render_certificate(record)
