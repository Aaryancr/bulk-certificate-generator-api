class BulkCertificateError(Exception):
    pass


class ValidationError(BulkCertificateError):
    pass


class TemplateError(BulkCertificateError):
    pass


class CertificateGenerationError(BulkCertificateError):
    pass


class ZipGenerationError(BulkCertificateError):
    pass
