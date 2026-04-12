"""SQLAlchemy model for saved simulation records."""

from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class SimulationRecord(Base):
    __tablename__ = "simulation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(10), nullable=False, index=True)
    marketplace = Column(String(5), nullable=False, index=True)
    current_price = Column(Float, nullable=True)
    custom_price = Column(Float, nullable=True)
    custom_start_day = Column(Integer, nullable=True)
    custom_duration = Column(Integer, nullable=True)
    currency = Column(String(5), nullable=True)
    forecast_days = Column(Integer, nullable=True)
    forecast_data = Column(JSON, nullable=True)  # full forecast array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
