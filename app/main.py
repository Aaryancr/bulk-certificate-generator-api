from fastapi import FastAPI

from app.api.routes import router
from app.db.models import init_db

app = FastAPI(
    title="Bulk Certificate Generator API",
    version="1.0.0",
    description="Generate personalized certificates in bulk from CSV data and HTML templates.",
)

init_db()

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
