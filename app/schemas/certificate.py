from pydantic import BaseModel, Field


class CertificateRecord(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    course: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    certificate_id: str = Field(..., min_length=1)
