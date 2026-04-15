"""SQLAlchemy model for the Product (product master) table."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Product(Base):
    """Persistent record of a tracked Amazon product."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asin: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    marketplace: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    main_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("marketplace", "asin", name="uq_marketplace_asin"),
    )

    snapshots = relationship(
        "ProductSnapshot", back_populates="product", cascade="all, delete-orphan"
    )
    changes = relationship(
        "ChangeRecord", back_populates="product", cascade="all, delete-orphan"
    )
