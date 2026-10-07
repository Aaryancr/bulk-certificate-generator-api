class BulkCertificateError(Exception):
    """Base exception for bulk certificate generation errors."""


class ValidationError(BulkCertificateError):
    """Raised when input data is invalid."""


class TemplateError(BulkCertificateError):
    """Raised when the certificate template is invalid."""


class CertificateGenerationError(BulkCertificateError):
    """Raised when a certificate cannot be generated."""


class ZipGenerationError(BulkCertificateError):
    """Raised when ZIP creation fails."""
