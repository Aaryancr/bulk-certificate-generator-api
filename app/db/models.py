from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.db.database import engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class GenerationRequest(Base):
    __tablename__ = "generation_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="pending", nullable=False)
    total = Column(Integer, default=0, nullable=False)
    completed = Column(Integer, default=0, nullable=False)
    failed = Column(Integer, default=0, nullable=False)
    output_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
