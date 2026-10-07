from fastapi import FastAPI

app = FastAPI(
    title="Bulk Certificate Generator API",
    version="0.1.0",
    description="API for generating personalized certificates in bulk from CSV data and HTML templates.",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
