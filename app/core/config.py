from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Bulk Certificate Generator API"
    app_version: str = "0.1.0"
    debug: bool = False


settings = Settings()
